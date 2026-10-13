from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import FIX, REPO, SF, TEST_CONFIG

from sflib import config, jira, jobs  # noqa: E402

STUB = os.path.join(REPO, "scripts", "jira_stub.py")
FIXD = os.path.join(FIX, "jira")


def stub(*args):
    p = subprocess.run([sys.executable, STUB] + list(args), capture_output=True, text=True)
    return p.returncode, p.stdout


def read(key, ext="json"):
    with open(os.path.join(FIXD, "%s.%s" % (key, ext))) as f:
        return f.read()


class JiraBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.env = dict(os.environ, STORY_FACTORY_CONFIG=TEST_CONFIG, STORY_FACTORY_JOBS=self.tmp)
        self._old = {k: os.environ.get(k) for k in ("STORY_FACTORY_CONFIG", "STORY_FACTORY_JOBS")}
        os.environ.update(STORY_FACTORY_CONFIG=TEST_CONFIG, STORY_FACTORY_JOBS=self.tmp)
        self.addCleanup(self._restore)

    def _restore(self):
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def new(self, idea, key=None):
        return jobs.new_job("story", idea, mode="refine" if key else "new", jira_key=key)

    def pull(self, job_id, key, ext="json"):
        shutil.copy(os.path.join(FIXD, "%s.%s" % (key, ext)),
                    os.path.join(self.tmp, job_id, "context", "jira", "%s.%s" % (key, ext)))

    def keys(self, job_id, cfg=None):
        c = cfg or config.load()
        return jira.keys_to_pull(jobs.load_job(job_id), jobs.job_dir(job_id), c)


class TestNormalize(unittest.TestCase):
    def test_factory_shape_as_is(self):
        d = jira.normalize(read("DEMO-101"))
        self.assertEqual(d["key"], "DEMO-101")
        self.assertEqual(d["parent_key"], "DEMO-100")
        self.assertEqual(d, json.loads(read("DEMO-101")))

    def test_raw_rest(self):
        d = jira.normalize(read("DEMO-105"))
        self.assertEqual(d["key"], "DEMO-105")
        self.assertEqual(d["issue_type"], "Story")
        self.assertEqual(d["status"], "To Do")
        self.assertEqual(d["components"], ["statements"])
        self.assertEqual(d["labels"], ["ux"])
        self.assertEqual(d["parent_key"], "DEMO-100")
        self.assertEqual(d["links"], [{"relation": "relates to", "key": "DEMO-101"}])

    def test_adf_flattened(self):
        d = jira.normalize(read("DEMO-105"))
        self.assertEqual(d["description"],
                         "Add quick date presets to the statement filter.\n"
                         "Presets: last 30 days, last 90 days, this year.")

    def test_rest_inward_link_and_plain_description(self):
        raw = json.dumps({"key": "DEMO-9", "fields": {
            "summary": "s", "description": "plain",
            "issuelinks": [{"type": {"inward": "is blocked by", "outward": "blocks"},
                            "inwardIssue": {"key": "DEMO-1"}}]}})
        d = jira.normalize(raw)
        self.assertEqual(d["description"], "plain")
        self.assertEqual(d["links"], [{"relation": "is blocked by", "key": "DEMO-1"}])
        self.assertIsNone(d["parent_key"])

    def test_markdown(self):
        d = jira.normalize(read("DEMO-106", "md"))
        self.assertEqual(d["format"], "markdown")
        self.assertEqual(d["key"], "DEMO-106")
        self.assertEqual(d["keys_mentioned"], ["DEMO-106", "DEMO-101", "DEMO-102"])

    def test_empty(self):
        self.assertIsNone(jira.normalize("  \n"))
        self.assertEqual(jira.normalize("no keys here")["key"], None)


class TestStub(unittest.TestCase):
    def test_json(self):
        rc, out = stub("DEMO-101")
        self.assertEqual(rc, 0)
        d = json.loads(out)
        self.assertEqual((d["key"], d["parent_key"]), ("DEMO-101", "DEMO-100"))

    def test_md(self):
        rc, out = stub("DEMO-101", "--format", "md")
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines()[0], "# DEMO-101: Statement filter")
        self.assertIn("**Parent:** DEMO-100", out)
        self.assertIn("## Acceptance criteria", out)

    def test_md_from_raw_rest(self):
        rc, out = stub("DEMO-105", "--format", "md")
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines()[0], "# DEMO-105: Statement date presets")
        self.assertIn("Presets: last 30 days", out)

    def test_raw_rest_json_verbatim(self):
        rc, out = stub("DEMO-105")
        self.assertEqual(out, read("DEMO-105"))

    def test_markdown_fixture_verbatim(self):
        rc, out = stub("DEMO-106", "--format", "json")
        self.assertEqual((rc, out), (0, read("DEMO-106", "md")))

    def test_not_found(self):
        self.assertEqual(stub("DEMO-999"), (2, "ERROR: DEMO-999 not found\n"))

    def test_invalid_key(self):
        self.assertEqual(stub("demo-1"), (64, "ERROR: invalid key demo-1\n"))

    def test_all_fixtures_have_required_fields(self):
        for n in range(100, 105):
            d = json.loads(read("DEMO-%d" % n))
            for k in ("key", "issue_type", "summary", "status", "labels", "components",
                      "fix_versions", "subtasks", "updated"):
                self.assertIn(k, d)


class TestJiraKeys(JiraBase):
    def test_seed_from_jira_key(self):
        self.assertEqual(self.keys(self.new("refine DEMO-101", "DEMO-101")), ["DEMO-101"])

    def test_seeds_from_idea(self):
        j = self.new("combine DEMO-101 and DEMO-102 and DEMO-101")
        self.assertEqual(self.keys(j), ["DEMO-101", "DEMO-102"])

    def test_seeds_from_rework(self):
        j = self.new("idea")
        with open(os.path.join(self.tmp, j, "rework-1.md"), "w") as f:
            f.write("Reviewer: see also DEMO-103.")
        self.assertEqual(self.keys(j), ["DEMO-103"])

    def test_one_hop(self):
        j = self.new("refine", "DEMO-101")
        self.pull(j, "DEMO-101")
        self.assertEqual(self.keys(j), ["DEMO-100", "DEMO-102"])
        self.pull(j, "DEMO-100")
        self.pull(j, "DEMO-102")
        self.assertEqual(self.keys(j), [])

    def test_two_hops(self):
        j = self.new("refine", "DEMO-101")
        for k in ("DEMO-101", "DEMO-100", "DEMO-102"):
            self.pull(j, k)
        cfg = config.load()
        cfg["jira"]["follow_links"] = 2
        self.assertEqual(self.keys(j, cfg), [])  # hop 1 tickets link to nothing new
        self.pull(j, "DEMO-105")
        # DEMO-105 is not reachable from the seed, so it adds nothing
        self.assertEqual(self.keys(j, cfg), [])

    def test_zero_hops(self):
        j = self.new("refine", "DEMO-101")
        self.pull(j, "DEMO-101")
        cfg = config.load()
        cfg["jira"]["follow_links"] = 0
        self.assertEqual(self.keys(j, cfg), [])

    def test_max_tickets(self):
        j = self.new("DEMO-101 DEMO-102 DEMO-103 DEMO-104")
        cfg = config.load()
        cfg["jira"]["max_tickets"] = 2
        self.assertEqual(self.keys(j, cfg), ["DEMO-101", "DEMO-102"])
        self.pull(j, "DEMO-101")
        self.assertEqual(self.keys(j, cfg), ["DEMO-102"])
        self.pull(j, "DEMO-102")
        self.assertEqual(self.keys(j, cfg), [])

    def test_cycle_and_self_link(self):
        j = self.new("refine", "DEMO-104")
        self.pull(j, "DEMO-104")
        self.assertEqual(self.keys(j), ["DEMO-101"])
        self.pull(j, "DEMO-101")
        self.assertEqual(self.keys(j), [])  # 1 hop reached; DEMO-104 never re-listed
        cfg = config.load()
        cfg["jira"]["follow_links"] = 3
        self.assertEqual(self.keys(j, cfg), ["DEMO-100", "DEMO-102"])

    def test_follows_raw_rest(self):
        j = self.new("refine", "DEMO-105")
        self.pull(j, "DEMO-105")
        self.assertEqual(self.keys(j), ["DEMO-100", "DEMO-101"])

    def test_follows_markdown(self):
        j = self.new("refine", "DEMO-106")
        self.pull(j, "DEMO-106", "md")
        self.assertEqual(self.keys(j), ["DEMO-101", "DEMO-102"])

    def test_cli_loop(self):
        p = subprocess.run([sys.executable, SF, "new-job", "--type", "story", "--mode", "refine",
                            "--jira-key", "DEMO-101", "--idea", "x"], capture_output=True, text=True, env=self.env)
        jid = p.stdout.strip()
        out = subprocess.run([sys.executable, SF, "jira-keys", jid], capture_output=True, text=True, env=self.env)
        self.assertEqual((out.returncode, out.stdout), (0, "DEMO-101\n"))


if __name__ == "__main__":
    unittest.main()
