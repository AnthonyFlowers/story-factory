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
REV = os.path.join(helpers.FIX, "reviews")
DEC = os.path.join(helpers.FIX, "decisions")
LENSES = ("invest", "ac", "tech", "security")


class Base(unittest.TestCase):
    cfg = helpers.NOREPOS_CONFIG

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.jobs = os.path.join(self.tmp, "jobs")
        os.makedirs(self.jobs)

    def sf(self, *args):
        env = dict(os.environ, STORY_FACTORY_CONFIG=self.cfg, STORY_FACTORY_JOBS=self.jobs)
        return subprocess.run([sys.executable, helpers.SF] + list(args), capture_output=True, text=True, env=env)

    def path(self, job, *parts):
        return os.path.join(self.jobs, job, *parts)

    def edit_job(self, job, **changes):
        p = self.path(job, "job.json")
        with open(p) as f:
            j = json.load(f)
        j.update(changes)
        with open(p, "w") as f:
            json.dump(j, f)

    def finish(self, job, story=None, decision="ready.md"):
        """Turn a copied sample into a finished READY job: checks, 4 PASS reviews, decision, gate."""
        if story:
            shutil.copy(story, self.path(job, "story.json"))
        r = self.sf("checks", job, "--round", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        for lens in LENSES:
            shutil.copy(os.path.join(REV, "pass.md"), self.path(job, "round-1", "review-%s.md" % lens))
        shutil.copy(os.path.join(DEC, decision), self.path(job, "decision.md"))
        r = self.sf("gate", job, "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)

    def check(self, job, *extra):
        r = self.sf("check-job", job, *extra)
        return r.returncode, r.stdout


class CheckJobTests(Base):
    def setUp(self):
        super().setUp()
        self.job = "900-sample"
        shutil.copytree(SAMPLE, self.path(self.job))
        self.finish(self.job)

    def assertFails(self, name, *extra):
        rc, out = self.check(self.job, *extra)
        self.assertEqual(rc, 1, out)
        self.assertIn("FAIL %s" % name, out)
        self.assertTrue(out.rstrip().endswith("RESULT: FAIL"), out)

    def test_pass(self):
        rc, out = self.check(self.job)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("FAIL", out)
        self.assertEqual(out.splitlines()[-1], "RESULT: PASS")

    def test_job_schema(self):
        self.edit_job(self.job, stage="bogus")
        self.assertFails("job-schema")

    def test_running_stage(self):
        self.edit_job(self.job, stage="review")
        self.assertFails("stage")

    def test_children_stage_needs_allow_running_and_epic(self):
        self.edit_job(self.job, stage="children")
        self.assertFails("stage")
        self.assertFails("stage", "--allow-running")  # not an epic

    def test_story_missing(self):
        os.unlink(self.path(self.job, "story.json"))
        self.assertFails("story-schema")

    def test_missing_review(self):
        os.unlink(self.path(self.job, "round-1", "review-tech.md"))
        self.assertFails("rounds")
        self.assertIn("review-tech.md missing", self.check(self.job)[1])

    def test_invalid_verdict(self):
        shutil.copy(os.path.join(REV, "invalid-first-line.md"), self.path(self.job, "round-1", "review-ac.md"))
        self.assertFails("rounds")
        self.assertIn("review-ac.md invalid", self.check(self.job)[1])

    def test_missing_checks_md(self):
        os.unlink(self.path(self.job, "round-1", "checks.md"))
        self.assertFails("rounds")

    def test_round_three_without_rework(self):
        self.edit_job(self.job, round=3)
        self.assertFails("round-limit")

    def test_round_three_with_rework_file_passes_limit(self):
        self.edit_job(self.job, round=3)
        with open(self.path(self.job, "rework-1.md"), "w") as f:
            f.write("note\n")
        self.assertNotIn("FAIL round-limit", self.check(self.job)[1])

    def test_missing_decision(self):
        os.unlink(self.path(self.job, "decision.md"))
        self.assertFails("decision-file")

    def test_ready_with_needs_human_decision(self):
        self.edit_job(self.job, decision="NEEDS-HUMAN")
        shutil.copy(os.path.join(DEC, "needs-human.md"), self.path(self.job, "decision.md"))
        self.assertFails("ready")

    def test_ready_blocking_flag_fails_gate(self):
        with open(self.path(self.job, "round-1", "review-security.md"), "w") as f:
            f.write("VERDICT: PASS\nFLAGS: pii\n")
        self.assertFails("ready")
        self.assertIn("flag:pii", self.check(self.job)[1])

    def test_ready_blocking_flag_ok_when_human_approved(self):
        with open(self.path(self.job, "round-1", "review-security.md"), "w") as f:
            f.write("VERDICT: PASS\nFLAGS: pii\n")
        self.edit_job(self.job, approved_by="human")
        rc, out = self.check(self.job)
        self.assertEqual(rc, 0, out)

    def test_ready_with_nonblocking_flag_passes(self):
        with open(self.path(self.job, "round-1", "review-security.md"), "w") as f:
            f.write("VERDICT: PASS\nFLAGS: audit\n")
        rc, out = self.check(self.job)
        self.assertEqual(rc, 0, out)

    def test_table_in_story_md(self):
        with open(self.path(self.job, "story.md"), "a") as f:
            f.write("\n| a | b |\n|---|---|\n")
        self.assertFails("story-md")

    def test_checkbox_and_nested_list_in_story_md(self):
        with open(self.path(self.job, "story.md"), "a") as f:
            f.write("\n- [ ] todo\n- item\n  - nested\n")
        rc, out = self.check(self.job)
        self.assertIn("checkbox", out)
        self.assertIn("nested list", out)

    def test_story_md_missing(self):
        os.unlink(self.path(self.job, "story.md"))
        self.assertFails("story-md")

    def test_big_file(self):
        with open(self.path(self.job, "context", "big.txt"), "wb") as f:
            f.write(b"x" * (1024 * 1024 + 1))
        self.assertFails("file-size")

    def test_stale_claim_file(self):
        with open(self.path(self.job, ".claim"), "w") as f:
            f.write('{"who": "laptop:1"}\n')
        self.assertFails("claim")

    def test_stale_claimed_by(self):
        self.edit_job(self.job, claimed_by="laptop:1")
        self.assertFails("claim")

    def test_running_job_with_claim_is_not_checked_for_claim(self):
        self.edit_job(self.job, stage="review", claimed_by="laptop:1")
        rc, out = self.check(self.job)
        self.assertNotIn("claim", out)

    def test_needs_human_with_reasons_passes(self):
        self.edit_job(self.job, stage="needs-human", decision="NEEDS-HUMAN", gate_reasons=["flag:pii"])
        shutil.copy(os.path.join(DEC, "needs-human.md"), self.path(self.job, "decision.md"))
        rc, out = self.check(self.job)
        self.assertEqual(rc, 0, out)

    def test_needs_human_without_questions_or_reasons(self):
        self.edit_job(self.job, stage="needs-human", decision="NEEDS-HUMAN", gate_reasons=[])
        shutil.copy(os.path.join(DEC, "ready.md"), self.path(self.job, "decision.md"))
        self.assertFails("needs-human")

    def test_needs_human_with_numbered_question_and_no_reasons(self):
        self.edit_job(self.job, stage="needs-human", decision="NEEDS-HUMAN", gate_reasons=[])
        shutil.copy(os.path.join(DEC, "needs-human.md"), self.path(self.job, "decision.md"))
        rc, out = self.check(self.job)
        self.assertEqual(rc, 0, out)


class EpicTests(Base):
    def setUp(self):
        super().setUp()
        self.epic = "901-epic"
        shutil.copytree(SAMPLE, self.path(self.epic))
        self.edit_job(self.epic, id=self.epic, type="epic", jira_key="DEMO-100")
        with open(os.path.join(helpers.STORIES, "epic.json")) as f:
            story = json.load(f)
        story["risk_flags"] = []  # the fixture's pii flag would send the epic to a human
        sp = os.path.join(self.tmp, "epic-story.json")
        with open(sp, "w") as f:
            json.dump(story, f)
        os.makedirs(self.path(self.epic, "context", "jira"), exist_ok=True)
        with open(self.path(self.epic, "context", "jira", "DEMO-100.json"), "w") as f:
            f.write("{}\n")  # the epic story cites DEMO-100 as a source
        self.finish(self.epic, story=sp)

    def test_ready_epic_without_children_fails(self):
        rc, out = self.check(self.epic)
        self.assertEqual(rc, 1, out)
        self.assertIn("FAIL epic-children: children map is empty", out)

    def spawn(self):
        r = self.sf("spawn-children", self.epic)
        self.assertEqual(r.returncode, 0, r.stderr)
        return [line.split("\t")[1] for line in r.stdout.strip().splitlines()]

    def test_running_epic(self):
        self.spawn()
        rc, out = self.check(self.epic)
        self.assertIn("FAIL stage", out)
        rc, out = self.check(self.epic, "--allow-running")
        self.assertEqual(rc, 0, out)  # children may still be running

    def test_finished_epic_passes(self):
        for cid in self.spawn():
            self.sf("job", cid, "--stage", "ready")
        r = self.sf("epic-status", self.epic, "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        rc, out = self.check(self.epic)
        self.assertEqual(rc, 0, out)

    def test_child_with_wrong_parent(self):
        ids = self.spawn()
        for cid in ids:
            self.sf("job", cid, "--stage", "ready")
        self.sf("epic-status", self.epic, "--apply")
        self.sf("job", ids[0], "--set", 'parent="999-other"')
        rc, out = self.check(self.epic)
        self.assertEqual(rc, 1, out)
        self.assertIn("parent is 999-other", out)

    def test_needs_human_epic_not_approved_needs_no_children(self):
        self.edit_job(self.epic, stage="needs-human", decision="NEEDS-HUMAN", gate_reasons=["flag:pii"])
        rc, out = self.check(self.epic)
        self.assertNotIn("epic-children", out)

    def test_human_approved_epic_needs_children(self):
        self.edit_job(self.epic, stage="needs-human", decision="READY", approved_by="human",
                      gate_reasons=["flag:pii"])
        rc, out = self.check(self.epic)
        self.assertIn("FAIL epic-children", out)


class ManifestTests(Base):
    def setUp(self):
        super().setUp()
        self.repo = os.path.join(self.tmp, "repo")
        self.docs = os.path.join(self.tmp, "docs")
        for d in (self.repo, self.docs):
            os.makedirs(os.path.join(d, "src"))
            with open(os.path.join(d, "src", "a.txt"), "w") as f:
                f.write("one\n")
        os.makedirs(os.path.join(self.repo, ".git"))
        with open(os.path.join(self.repo, ".git", "index"), "w") as f:
            f.write("ignored\n")
        self.cfg = os.path.join(self.tmp, "config.json")
        with open(self.cfg, "w") as f:
            json.dump({"jira": {"skill": "x", "project_key": "DEMO"},
                       "repos": [{"name": "r", "path": self.repo, "openapi": [], "docs": []}],
                       "team_docs": [{"name": "d", "path": self.docs}]}, f)

    def test_unchanged(self):
        r = self.sf("check-job", "--manifest")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.jobs, ".manifest.json")))
        r = self.sf("check-job", "--manifest", "--compare")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("OK manifest unchanged", r.stdout)

    def test_git_dir_is_ignored(self):
        self.sf("check-job", "--manifest")
        with open(os.path.join(self.repo, ".git", "index"), "w") as f:
            f.write("changed\n")
        self.assertEqual(self.sf("check-job", "--manifest", "--compare").returncode, 0)

    def test_changed_added_removed(self):
        self.sf("check-job", "--manifest")
        with open(os.path.join(self.repo, "src", "a.txt"), "w") as f:
            f.write("two\n")
        with open(os.path.join(self.docs, "new.md"), "w") as f:
            f.write("x\n")
        os.unlink(os.path.join(self.docs, "src", "a.txt"))
        r = self.sf("check-job", "--manifest", "--compare")
        self.assertEqual(r.returncode, 1)
        self.assertIn("CHANGED " + os.path.join(self.repo, "src", "a.txt"), r.stdout)
        self.assertIn("ADDED " + os.path.join(self.docs, "new.md"), r.stdout)
        self.assertIn("REMOVED " + os.path.join(self.docs, "src", "a.txt"), r.stdout)

    def test_compare_without_manifest(self):
        r = self.sf("check-job", "--manifest", "--compare")
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
