from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import helpers

SAMPLE = os.path.join(helpers.FIX, "jobs", "900-sample")


class ChecksTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg_path = helpers.NOREPOS_CONFIG
        self.configure()
        self.jobs = os.path.join(self.tmp, "jobs")
        os.makedirs(self.jobs)
        shutil.copytree(SAMPLE, os.path.join(self.jobs, "900-sample"))
        self.job = os.path.join(self.jobs, "900-sample")
        self.env = dict(os.environ, STORY_FACTORY_CONFIG=self.cfg_path,
                        STORY_FACTORY_JOBS=self.jobs)

    def configure(self):
        pass

    def write_config(self, extra):
        with open(helpers.TEST_CONFIG) as f:
            cfg = json.load(f)
        cfg.update(extra)
        self.cfg_path = os.path.join(self.tmp, "config.json")
        with open(self.cfg_path, "w") as f:
            json.dump(cfg, f)

    def sf(self, *args):
        return subprocess.run([sys.executable, helpers.SF] + list(args), capture_output=True,
                              text=True, env=self.env)

    def story(self):
        with open(os.path.join(self.job, "story.json")) as f:
            return json.load(f)

    def save_story(self, s):
        with open(os.path.join(self.job, "story.json"), "w") as f:
            json.dump(s, f)

    def checks_md(self, n=1):
        with open(os.path.join(self.job, "round-%d" % n, "checks.md")) as f:
            return f.read()


class ChecksNoReposTests(ChecksTestCase):
    def test_snapshot_and_report(self):
        r = self.sf("checks", "900-sample", "--round", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "checks: schema=OK dor_fail=0 missing=0")
        self.assertTrue(os.path.isfile(os.path.join(self.job, "round-1", "story.json")))
        md = self.checks_md()
        for needle in ("# Checks: round 1", "Schema: OK", "## Definition of ready (auto)", "- PASS DOR1 ",
                       "- PASS DOR2 ", "## Sources", "- SKIPPED DEMO-101 (jira: present in context/jira)",
                       "no repos or team docs configured", "## API operations", "## Flags", "risk_flags: none"):
            self.assertIn(needle, md)
        self.assertNotIn("DOR6", md)  # review items are not auto

    def test_schema_errors_and_dor(self):
        s = self.story()
        del s["title"]
        s["open_questions"] = ["Which dates?", "Which format?"]
        s["acceptance_criteria"] = s["acceptance_criteria"][:1]
        self.save_story(s)
        r = self.sf("checks", "900-sample", "--round", "2")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "checks: schema=ERRORS dor_fail=2 missing=0")
        md = self.checks_md(2)
        self.assertIn("Schema: ERRORS", md)
        self.assertIn("- ERROR /title: required", md)
        self.assertIn("- FAIL DOR5 No open questions: 2 open questions", md)
        self.assertIn("- FAIL DOR2 ", md)

    def test_jira_missing(self):
        s = self.story()
        s["sources"].append({"kind": "jira", "ref": "DEMO-999"})
        s["risk_flags"] = ["pii", "auth"]
        self.save_story(s)
        self.sf("checks", "900-sample", "--round", "1")
        md = self.checks_md()
        self.assertIn("- MISSING DEMO-999 (jira: not pulled)", md)
        self.assertIn("risk_flags: pii, auth", md)

    def test_no_story(self):
        os.unlink(os.path.join(self.job, "story.json"))
        r = self.sf("checks", "900-sample", "--round", "1")
        self.assertEqual(r.returncode, 1)

    def test_invalid_json(self):
        with open(os.path.join(self.job, "story.json"), "w") as f:
            f.write("{nope")
        r = self.sf("checks", "900-sample", "--round", "1")
        self.assertEqual(r.returncode, 0)
        self.assertIn("schema=ERRORS", r.stdout)


class ChecksWithReposTests(ChecksTestCase):
    def configure(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, True)
        os.makedirs(os.path.join(self.repo, "src", "controllers"))
        with open(os.path.join(self.repo, "src", "controllers", "statement.controller.ts"), "w") as f:
            f.write("line1\nline2\nline3\n")
        spec = {"paths": {"/accounts/{accountId}/statements": {"get": {}}, "/health": {"get": {}}}}
        with open(os.path.join(self.repo, "openapi.json"), "w") as f:
            json.dump(spec, f)
        self.write_config({"repos": [{"name": "accounts-api", "path": self.repo}]})

    def test_resolution(self):
        s = self.story()
        s["sources"] += [
            {"kind": "code", "ref": "accounts-api:src/controllers/statement.controller.ts:3"},
            {"kind": "code", "ref": "accounts-api:src/controllers/statement.controller.ts:99"},
            {"kind": "code", "ref": "accounts-api:src/services/nope.ts"},
            {"kind": "code", "ref": "accounts-api:../outside.ts"},
            {"kind": "code", "ref": "other-repo:a.ts"},
            {"kind": "idea", "ref": "brief.md"}]
        s["api_impact"] += [
            {"contract": "accounts-api:openapi.json", "operation": "POST /accounts/{accountId}/exports", "change": "add", "breaking": "no"},
            {"contract": "accounts-api:openapi.json", "operation": "DELETE /x", "change": "modify", "breaking": "no"},
            {"contract": "accounts-api:openapi.json", "operation": "GET /health", "change": "add", "breaking": "no"},
            {"contract": "accounts-api:openapi.yaml", "operation": "GET /y", "change": "modify", "breaking": "no"}]
        self.save_story(s)
        r = self.sf("checks", "900-sample", "--round", "1")
        md = self.checks_md()
        self.assertIn("- OK accounts-api:src/controllers/statement.controller.ts\n", md)
        self.assertIn("- OK accounts-api:src/controllers/statement.controller.ts:3\n", md)
        self.assertIn("- MISSING accounts-api:src/controllers/statement.controller.ts:99 (line 99 beyond end", md)
        self.assertIn("- MISSING accounts-api:src/services/nope.ts (file not found)", md)
        self.assertIn("- MISSING accounts-api:../outside.ts", md)
        self.assertIn("- MISSING other-repo:a.ts", md)
        self.assertIn("- SKIPPED brief.md (idea)", md)
        self.assertIn("- OK GET /accounts/{accountId}/statements in accounts-api:openapi.json (modify", md)
        self.assertIn("- NEW POST /accounts/{accountId}/exports in accounts-api:openapi.json (add; not in contract, as expected)", md)
        self.assertIn("- MISSING DELETE /x in accounts-api:openapi.json (modify; operation not found)", md)
        self.assertIn("- CONFLICT GET /health in accounts-api:openapi.json (add; already exists)", md)
        self.assertIn("- SKIPPED accounts-api:openapi.yaml (yaml)", md)
        self.assertIn("- FAIL DOR4 Every source reference exists: 4 missing sources", md)
        self.assertIn("missing=5", r.stdout)


if __name__ == "__main__":
    unittest.main()
