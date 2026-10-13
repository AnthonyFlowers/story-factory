from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import helpers
from sflib import config, settings


class JobsTestCase(unittest.TestCase):
    def setUp(self):
        self.jobs = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.jobs, True)
        self.env = dict(os.environ, STORY_FACTORY_CONFIG=helpers.TEST_CONFIG, STORY_FACTORY_JOBS=self.jobs)

    def sf(self, *args, env=None):
        return subprocess.run([sys.executable, helpers.SF] + list(args), capture_output=True,
                              text=True, env=env or self.env)

    def new(self, idea, typ="story"):
        r = self.sf("new-job", "--type", typ, "--idea", idea)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()


class JobTests(JobsTestCase):
    def test_new_job_and_numbering(self):
        a = self.new("Add the service version to the health endpoint")
        self.assertEqual(a, "001-add-service-version-health")
        self.assertEqual(self.new("x y z"), "002-x-y-z")
        d = os.path.join(self.jobs, a)
        self.assertTrue(os.path.isdir(os.path.join(d, "context", "jira")))
        with open(os.path.join(d, "job.json")) as f:
            job = json.load(f)
        self.assertEqual(job["stage"], "intake")
        self.assertEqual(job["reviews"], {"invest": "pending", "ac": "pending", "tech": "pending", "security": "pending"})
        brief = open(os.path.join(d, "brief.md")).read()
        for needle in ("# Brief: " + a, "## Idea", "> Add the service", "## Where to look", "team docs `team-docs`",
                       "## Jira context", "none yet", "## Template", "## Escalation",
                       "These flags force NEEDS-HUMAN", "## Rules", "No estimates."):
            self.assertIn(needle, brief)
        self.assertLess(brief.index("## Template"), brief.index("## Escalation"))
        self.assertLess(brief.index("## Escalation"), brief.index("## Rules"))

    def test_refine_slug(self):
        r = self.sf("new-job", "--type", "story", "--mode", "refine", "--jira-key", "DEMO-101", "--idea", "tidy")
        self.assertEqual(r.stdout.strip(), "001-refine-demo-101")

    def test_concurrent_new_job(self):
        procs = [subprocess.Popen([sys.executable, helpers.SF, "new-job", "--type", "story", "--idea",
                                   "same idea %d" % (i % 2)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, env=self.env) for i in range(5)]
        ids = []
        for p in procs:
            out, err = p.communicate()
            self.assertEqual(p.returncode, 0, err)
            ids.append(out.strip())
        self.assertEqual(len(set(ids)), 5, ids)
        self.assertEqual(len({i.split("-")[0] for i in ids}), 5, ids)

    def test_job_update(self):
        jid = self.new("some idea here")
        r = self.sf("job", jid, "--stage", "review", "--round", "1", "--review", "ac=PASS",
                    "--flags", "pii,auth", "--set", 'title="T title"')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"ac": "PASS"', r.stdout)
        job = json.loads(r.stdout)
        self.assertEqual(job["flags"], ["pii", "auth"])
        self.assertEqual(job["title"], "T title")
        r = self.sf("job", jid, "--reset-reviews")
        self.assertEqual(json.loads(r.stdout)["reviews"]["ac"], "pending")

    def test_invalid_update_leaves_file_unchanged(self):
        jid = self.new("some idea here")
        p = os.path.join(self.jobs, jid, "job.json")
        before = open(p).read()
        r = self.sf("job", jid, "--stage", "nonsense")
        self.assertEqual(r.returncode, 1)
        self.assertIn("ERROR", r.stderr)
        self.assertIn("stage", r.stderr)
        self.assertEqual(open(p).read(), before)
        r = self.sf("job", jid, "--revisions-used", "2")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(open(p).read(), before)

    def test_list(self):
        a = self.new("Add the service version to the health endpoint")
        self.new("x y z")
        self.sf("job", a, "--stage", "review", "--round", "1")
        lines = self.sf("list").stdout.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("001-add-service-version-health  story  review  r1  "), lines[0])

    def test_missing_config_exit_2(self):
        env = dict(self.env, STORY_FACTORY_CONFIG=os.path.join(self.jobs, "nope.json"))
        r = self.sf("config", env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("ERROR: no config; copy factory.config.example.json to factory.config.json", r.stderr)

    def test_validate_cli_exit_codes(self):
        ok = self.sf("validate", os.path.join(helpers.STORIES, "story.json"))
        self.assertEqual((ok.returncode, ok.stdout.strip()), (0, "OK"))
        bad = self.sf("validate", os.path.join(helpers.STORIES, "invalid-estimate.json"))
        self.assertEqual(bad.returncode, 1)
        self.assertIn("ERROR /story_points: additional property not allowed", bad.stdout)

    def test_render_job(self):
        jid = self.new("some idea here")
        shutil_copy = os.path.join(self.jobs, jid, "story.json")
        shutil.copy(os.path.join(helpers.STORIES, "story.json"), shutil_copy)
        r = self.sf("render", jid)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.jobs, jid, "story.md")))
        job = json.load(open(os.path.join(self.jobs, jid, "job.json")))
        self.assertEqual(job["title"], "Filter account statements by date range")


class SettingsTests(unittest.TestCase):
    def test_settings_build(self):
        cfg = {"repos": [{"name": "accounts-api", "path": "/Users/me/work/accounts-api"}],
               "team_docs": [], "deny_read": ["/Users/me/secret"]}
        out = settings.build(cfg)["permissions"]
        self.assertEqual(out["additionalDirectories"], ["/Users/me/work/accounts-api"])
        self.assertIn("Edit(//Users/me/work/accounts-api/**)", out["deny"])
        self.assertIn("Read(//Users/me/secret/**)", out["deny"])

    def test_settings_allow_rules_and_jira_skill(self):
        out = settings.build({"jira": {"skill": "pull-jira-ticket"}})["permissions"]
        self.assertIn("Bash(python3 scripts/sf.py *)", out["allow"])
        self.assertIn("Skill(pull-jira-ticket)", out["allow"])
        self.assertEqual(settings.build({})["permissions"]["allow"][:2],
                         ["Bash(python3 scripts/sf.py *)", "Bash(python3 scripts/jira_stub.py *)"])

    def test_config_resolves_relative_paths(self):
        old = os.environ.get("STORY_FACTORY_CONFIG")
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        p = os.path.join(tmp, "c.json")
        with open(p, "w") as f:
            json.dump({"repos": [{"name": "accounts-api", "path": "rel/repo"}]}, f)
        os.environ["STORY_FACTORY_CONFIG"] = p
        try:
            cfg = config.load()
        finally:
            if old is None:
                del os.environ["STORY_FACTORY_CONFIG"]
            else:
                os.environ["STORY_FACTORY_CONFIG"] = old
        self.assertEqual(cfg["repos"][0]["path"], os.path.join(config.root(), "rel", "repo"))
        self.assertEqual(cfg["escalation"]["always_human"], ["pii", "auth", "payments", "regulatory"])
        self.assertTrue(settings.build(cfg)["permissions"]["deny"][0].startswith("Edit(//"))


if __name__ == "__main__":
    unittest.main()
