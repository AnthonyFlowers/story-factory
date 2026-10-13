from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest

import helpers
from test_jobs import JobsTestCase

EPIC = "910-epic-sample"


class EpicTestCase(JobsTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(os.path.join(helpers.FIX, "jobs", EPIC), os.path.join(self.jobs, EPIC))

    def job(self, jid):
        with open(os.path.join(self.jobs, jid, "job.json")) as f:
            return json.load(f)

    def ready(self):
        r = self.sf("job", EPIC, "--stage", "ready", "--decision", "READY", "--approved-by", "agent")
        self.assertEqual(r.returncode, 0, r.stderr)

    def spawn(self):
        self.ready()
        r = self.sf("spawn-children", EPIC)
        self.assertEqual(r.returncode, 0, r.stderr)
        return [line.split("\t") for line in r.stdout.splitlines()]

    def set_story(self, mutate):
        p = os.path.join(self.jobs, EPIC, "story.json")
        with open(p) as f:
            s = json.load(f)
        mutate(s)
        with open(p, "w") as f:
            json.dump(s, f)


class SpawnTests(EpicTestCase):
    def test_spawn_order_and_idempotent(self):
        rows = self.spawn()
        self.assertEqual([r[0] for r in rows], ["C1", "C2", "C3"])
        self.assertEqual([r[1] for r in rows], ["911-filter-statements-date-range", "912-server-side-statement-pdfs",
                                                "913-download-statement-pdf"])
        again = self.sf("spawn-children", EPIC)
        self.assertEqual([l.split("\t") for l in again.stdout.splitlines()], rows)
        self.assertEqual(len([n for n in os.listdir(self.jobs) if not n.startswith(".")]), 4)
        e = self.job(EPIC)
        self.assertEqual(e["stage"], "children")
        self.assertEqual(e["children"]["C3"], "913-download-statement-pdf")

    def test_children_unclaimed_with_parent_and_jira_key(self):
        rows = self.spawn()
        for ref, cid in rows:
            self.assertFalse(os.path.exists(os.path.join(self.jobs, cid, ".claim")), cid)
            j = self.job(cid)
            self.assertIsNone(j["claimed_by"])
            self.assertEqual(j["parent"], EPIC)
            self.assertEqual(j["jira_key"], "DEMO-100")
            self.assertEqual(j["stage"], "intake")
        self.assertEqual([self.job(r[1])["type"] for r in rows], ["story", "spike", "story"])
        self.assertFalse(os.path.exists(os.path.join(self.jobs, EPIC, ".claim")))

    def test_child_brief_and_idea(self):
        rows = self.spawn()
        with open(os.path.join(self.jobs, rows[2][1], "brief.md")) as f:
            brief = f.read()
        self.assertEqual(brief.count("## Parent epic"), 1)
        self.assertIn(os.path.join(self.jobs, EPIC, "story.json"), brief)
        self.assertIn("Customers find and download their own statements", brief)
        self.assertIn("This child: C3", brief)
        self.assertIn("Depends on: C2", brief)
        self.assertIn("- C1: Filter statements by date range", brief)
        self.assertNotIn("- C3:", brief)
        idea = self.job(rows[2][1])["idea"]
        self.assertIn("Child C3 of epic 910-epic-sample: Statement self-service.", idea)
        self.assertIn("Depends on: C2 → Server-side statement PDFs.", idea)
        self.assertIn("Depends on: none.", self.job(rows[0][1])["idea"])
        epic_brief = open(os.path.join(self.jobs, EPIC, "brief.md")).read() if os.path.exists(
            os.path.join(self.jobs, EPIC, "brief.md")) else ""
        self.assertNotIn("## Parent epic", epic_brief)

    def test_not_ready(self):
        r = self.sf("spawn-children", EPIC)
        self.assertEqual(r.returncode, 1)
        self.assertIn("ERROR: epic 910-epic-sample is in stage approve", r.stderr)
        self.assertEqual(len(os.listdir(self.jobs)), 1)

    def test_needs_human_needs_approval(self):
        self.sf("job", EPIC, "--stage", "needs-human")
        self.assertEqual(self.sf("spawn-children", EPIC).returncode, 1)
        self.sf("job", EPIC, "--approved-by", "human")
        self.assertEqual(self.sf("spawn-children", EPIC).returncode, 0)

    def test_not_an_epic(self):
        self.set_story(lambda s: s.update(type="story"))
        self.ready()
        self.assertEqual(self.sf("spawn-children", EPIC).returncode, 1)

    def test_cycle(self):
        def m(s):
            s["epic"]["children"][1]["depends_on"] = ["C3"]
        self.set_story(m)
        self.ready()
        r = self.sf("spawn-children", EPIC)
        self.assertEqual(r.returncode, 1)
        self.assertIn("ERROR: dependency cycle C2 -> C3 -> C2", r.stderr)
        self.assertEqual(len(os.listdir(self.jobs)), 1)

    def test_unknown_ref(self):
        def m(s):
            s["epic"]["children"][0]["depends_on"] = ["C9"]
        self.set_story(m)
        self.ready()
        r = self.sf("spawn-children", EPIC)
        self.assertEqual(r.returncode, 1)
        self.assertIn("unknown ref C9", r.stderr)

    def test_topological_order_beats_order_field(self):
        def m(s):
            s["epic"]["children"][0]["depends_on"] = ["C3"]
        self.set_story(m)
        self.ready()
        r = self.sf("spawn-children", EPIC)
        self.assertEqual([l.split("\t")[0] for l in r.stdout.splitlines()], ["C2", "C3", "C1"])

    def test_no_jira_key_when_epic_has_none(self):
        self.sf("job", EPIC, "--set", "jira_key=null")
        rows = self.spawn()
        self.assertIsNone(self.job(rows[0][1])["jira_key"])


class StatusTests(EpicTestCase):
    def test_running_then_ready(self):
        rows = self.spawn()
        r = self.sf("epic-status", EPIC)
        lines = r.stdout.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(all("intake" in l for l in lines[:3]))
        self.assertEqual(lines[3], "RUNNING")
        for _, cid in rows:
            self.sf("job", cid, "--stage", "ready")
        r = self.sf("epic-status", EPIC, "--apply")
        self.assertIn("ALL-DONE ready=3 needs-human=0", r.stdout)
        e = self.job(EPIC)
        self.assertEqual((e["stage"], e["gate_reasons"]), ("ready", []))

    def test_mixed_is_needs_human(self):
        rows = self.spawn()
        self.sf("job", rows[0][1], "--stage", "ready")
        self.sf("job", rows[1][1], "--stage", "needs-human")
        self.sf("job", rows[2][1], "--stage", "ready")
        r = self.sf("epic-status", EPIC, "--apply")
        self.assertIn("ALL-DONE ready=2 needs-human=1", r.stdout)
        e = self.job(EPIC)
        self.assertEqual(e["stage"], "needs-human")
        self.assertEqual(e["gate_reasons"], ["children-need-human:" + rows[1][1]])

    def test_apply_does_nothing_while_running(self):
        self.spawn()
        self.sf("epic-status", EPIC, "--apply")
        self.assertEqual(self.job(EPIC)["stage"], "children")

    def test_shows_claimed_by(self):
        rows = self.spawn()
        self.sf("claim", rows[0][1], "--who", "sess-a")
        out = self.sf("epic-status", EPIC).stdout
        self.assertIn("claimed_by=sess-a", out.splitlines()[0])
        self.assertNotIn("claimed_by", out.splitlines()[1])

    def test_two_applies_same_state(self):
        rows = self.spawn()
        for _, cid in rows:
            self.sf("job", cid, "--stage", "needs-human")
        procs = [subprocess.Popen([sys.executable, helpers.SF, "epic-status", EPIC, "--apply"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
                 for _ in range(2)]
        for p in procs:
            p.communicate()
            self.assertEqual(p.returncode, 0)
        first = self.job(EPIC)
        self.sf("epic-status", EPIC, "--apply")
        second = self.job(EPIC)
        for k in ("stage", "gate_reasons", "children"):
            self.assertEqual(first[k], second[k])
        self.assertEqual(first["stage"], "needs-human")

    def test_no_children_yet(self):
        self.ready()
        self.assertEqual(self.sf("epic-status", EPIC).returncode, 1)


class NextChildTests(EpicTestCase):
    def test_three_concurrent_distinct_and_fourth_empty(self):
        self.spawn()
        procs = [subprocess.Popen([sys.executable, helpers.SF, "next-child", EPIC, "--who", "s%d" % i],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
                 for i in range(3)]
        ids = []
        for p in procs:
            out, err = p.communicate()
            self.assertEqual(p.returncode, 0, err)
            ids.append(out.strip())
        self.assertEqual(len(set(ids)), 3, ids)
        self.assertTrue(all(ids))
        r = self.sf("next-child", EPIC)
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_prefers_unblocked_then_order(self):
        rows = self.spawn()
        c = dict(rows)
        # C1 and C2 are independent, C3 waits for C2: order is C1, C2, C3
        got = [self.sf("next-child", EPIC).stdout.strip() for _ in range(3)]
        self.assertEqual(got, [c["C1"], c["C2"], c["C3"]])

    def test_blocked_is_still_returned_and_dependency_first(self):
        rows = self.spawn()
        c = dict(rows)
        self.sf("job", c["C1"], "--stage", "ready")
        self.sf("claim", c["C2"], "--who", "other")  # C2 busy elsewhere, unfinished
        self.assertEqual(self.sf("next-child", EPIC).stdout.strip(), c["C3"])  # only blocked one left

    def test_skips_terminal_and_claimed(self):
        rows = self.spawn()
        c = dict(rows)
        self.sf("job", c["C1"], "--stage", "needs-human")
        self.sf("claim", c["C2"], "--who", "other")
        self.assertEqual(self.sf("next-child", EPIC, "--who", "me").stdout.strip(), c["C3"])
        self.assertEqual(self.job(c["C3"])["claimed_by"], "me")
        self.assertEqual(self.sf("next-child", EPIC).stdout, "")

    def test_released_child_comes_back(self):
        rows = self.spawn()
        first = self.sf("next-child", EPIC).stdout.strip()
        self.sf("release", first)
        self.assertEqual(self.sf("next-child", EPIC).stdout.strip(), first)


if __name__ == "__main__":
    unittest.main()
