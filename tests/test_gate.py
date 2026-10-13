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


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.jobs = os.path.join(self.tmp, "jobs")
        os.makedirs(self.jobs)
        self.job = os.path.join(self.jobs, "900-sample")
        shutil.copytree(SAMPLE, self.job)
        self.cfg = helpers.NOREPOS_CONFIG
        self.sf("checks", "900-sample", "--round", "1")
        for lens in ("invest", "ac", "tech", "security"):
            shutil.copy(os.path.join(REV, "pass.md"), os.path.join(self.job, "round-1", "review-%s.md" % lens))
        shutil.copy(os.path.join(DEC, "ready.md"), os.path.join(self.job, "decision.md"))

    def sf(self, *args):
        env = dict(os.environ, STORY_FACTORY_CONFIG=self.cfg, STORY_FACTORY_JOBS=self.jobs)
        return subprocess.run([sys.executable, helpers.SF] + list(args), capture_output=True, text=True, env=env)

    def story(self, **changes):
        p = os.path.join(self.job, "story.json")
        with open(p) as f:
            s = json.load(f)
        s.update(changes)
        with open(p, "w") as f:
            json.dump(s, f)

    def job_json(self):
        with open(os.path.join(self.job, "job.json")) as f:
            return json.load(f)

    def gate(self, *extra):
        return self.sf("gate", "900-sample", *extra)

    def test_ok(self):
        r = self.gate()
        self.assertEqual(r.stdout.strip(), "OK", r.stderr)

    def test_apply_ready(self):
        r = self.gate("--apply")
        self.assertEqual(r.stdout.split(), ["OK", "ready"])
        j = self.job_json()
        self.assertEqual((j["stage"], j["decision"], j["approved_by"], j["gate_reasons"]), ("ready", "READY", "agent", []))
        self.assertTrue(os.path.isfile(os.path.join(self.job, "story.md")))

    def test_non_blocking_flag_is_ready(self):
        for flag in ("audit", "third-party"):
            self.story(risk_flags=[flag])
            with open(os.path.join(self.job, "decision.md"), "w") as f:
                f.write("READY\nFLAGS: %s\n\n## Why\nok\n" % flag)
            r = self.gate("--apply")
            self.assertEqual(r.stdout.split(), ["OK", "ready"], flag)
            j = self.job_json()
            self.assertEqual(j["stage"], "ready")
            self.assertIn(flag, j["flags"])

    def sec(self, name):
        shutil.copy(os.path.join(REV, name), os.path.join(self.job, "round-1", "review-security.md"))

    def test_security_flag_is_human(self):
        self.sec("pass-pii.md")
        r = self.gate("--apply")
        self.assertEqual(r.stdout.splitlines()[0], "HUMAN: flag:pii")
        j = self.job_json()
        self.assertEqual((j["stage"], j["gate_reasons"], j["flags"]), ("needs-human", ["flag:pii"], ["pii"]))

    def test_writer_flag_cleared_by_security_is_ready(self):
        self.story(risk_flags=["pii", "auth", "payments", "regulatory"])
        r = self.gate("--apply")  # security review says FLAGS: none
        self.assertEqual(r.stdout.split(), ["OK", "ready"])
        j = self.job_json()
        self.assertEqual((j["stage"], j["gate_reasons"]), ("ready", []))
        self.assertIn("pii", j["flags"])  # recorded as a hint

    def test_other_reviewer_and_decision_flags_do_not_block(self):
        shutil.copy(os.path.join(REV, "pass-pii.md"), os.path.join(self.job, "round-1", "review-tech.md"))
        with open(os.path.join(self.job, "decision.md"), "w") as f:
            f.write("READY\nFLAGS: pii\n\n## Why\nok\n")
        self.assertEqual(self.gate().stdout.strip(), "OK")

    def test_missing_flags_line_is_human(self):
        self.sec("missing-flags.md")
        self.assertEqual(self.gate().stdout.strip(), "HUMAN: review-invalid:security")

    def test_changes_remaining_is_human(self):
        shutil.copy(os.path.join(REV, "changes-flags.md"), os.path.join(self.job, "round-1", "review-ac.md"))
        self.assertEqual(self.gate().stdout.strip(), "HUMAN: changes-left:ac")

    def test_review_flags_and_changes(self):
        shutil.copy(os.path.join(REV, "changes-flags.md"), os.path.join(self.job, "round-1", "review-security.md"))
        r = self.gate("--apply")
        self.assertEqual(r.stdout.splitlines()[0], "HUMAN: flag:pii; flag:auth; changes-left:security")
        j = self.job_json()
        self.assertEqual(j["stage"], "needs-human")
        self.assertEqual(j["decision"], "NEEDS-HUMAN")
        self.assertEqual(j["gate_reasons"], ["flag:pii", "flag:auth", "changes-left:security"])
        self.assertEqual(j["flags"], ["pii", "auth"])

    def test_decision_flags_count(self):
        shutil.copy(os.path.join(DEC, "needs-human.md"), os.path.join(self.job, "decision.md"))
        r = self.gate()
        self.assertEqual(r.stdout.strip(), "HUMAN: decision-needs-human")

    def test_open_questions_and_assumptions_do_not_block(self):
        self.story(open_questions=["Which dates?"], assumptions=[{"text": "Dates are UTC", "kind": "product"}])
        r = self.gate("--apply")
        self.assertEqual(r.stdout.split(), ["OK", "ready"])
        with open(os.path.join(self.job, "story.md")) as f:
            md = f.read()
        self.assertIn("## Open questions for the team\n\n- Which dates?", md)
        self.assertIn("## Assumptions", md)
        self.assertIn("- Dates are UTC (product)", md)

    def test_technical_assumption_ok(self):
        r = self.gate()  # the sample has a technical assumption
        self.assertEqual(r.stdout.strip(), "OK")

    def test_missing_source(self):
        s = os.path.join(self.job, "story.json")
        with open(s) as f:
            st = json.load(f)
        st["sources"].append({"kind": "jira", "ref": "DEMO-999"})
        with open(s, "w") as f:
            json.dump(st, f)
        self.assertEqual(self.gate().stdout.strip(), "HUMAN: missing-sources")

    def test_schema_errors(self):
        s = os.path.join(self.job, "story.json")
        with open(s) as f:
            st = json.load(f)
        del st["title"]
        with open(s, "w") as f:
            json.dump(st, f)
        r = self.gate("--apply")
        self.assertEqual(r.stdout.splitlines()[0], "HUMAN: schema-errors")
        self.assertEqual(self.job_json()["stage"], "needs-human")

    def test_extra_terms_and_default_always_human(self):
        with open(helpers.NOREPOS_CONFIG) as f:
            cfg = json.load(f)
        cfg["escalation"]["extra_terms"] = ["Wire Transfer"]
        self.cfg = os.path.join(self.tmp, "c.json")
        with open(self.cfg, "w") as f:
            json.dump(cfg, f)
        self.story(context="A wire transfer limit is checked by `StatementController`.")
        self.assertEqual(self.gate().stdout.strip(), "HUMAN: term:Wire Transfer")
        # a config without the key falls back to the default blocking list
        del cfg["escalation"]["always_human"]
        with open(self.cfg, "w") as f:
            json.dump(cfg, f)
        self.story(context="ok", risk_flags=["audit", "regulatory"])
        self.assertEqual(self.gate().stdout.strip(), "OK")  # writer flags are hints
        shutil.copy(os.path.join(REV, "pass-pii.md"), os.path.join(self.job, "round-1", "review-security.md"))
        self.assertEqual(self.gate().stdout.strip(), "HUMAN: flag:pii")

    def test_no_decision(self):
        os.unlink(os.path.join(self.job, "decision.md"))
        self.assertEqual(self.gate().stdout.strip(), "HUMAN: no-decision")
        with open(os.path.join(self.job, "decision.md"), "w") as f:
            f.write("MAYBE\n")
        self.assertEqual(self.gate().stdout.strip(), "HUMAN: no-decision")

    def test_uses_latest_round(self):
        shutil.copy(os.path.join(REV, "changes-flags.md"), os.path.join(self.job, "round-1", "review-ac.md"))
        shutil.copytree(os.path.join(self.job, "round-1"), os.path.join(self.job, "round-2"))
        for lens in ("invest", "ac", "tech", "security"):
            shutil.copy(os.path.join(REV, "pass.md"), os.path.join(self.job, "round-2", "review-%s.md" % lens))
        self.assertEqual(self.gate().stdout.strip(), "OK")

    def test_missing_review(self):
        os.unlink(os.path.join(self.job, "round-1", "review-tech.md"))
        self.assertEqual(self.gate().stdout.strip(), "HUMAN: review-invalid:tech")


class EscalateTests(GateTests):
    def test_escalate(self):
        r = self.sf("escalate", "900-sample", "--why", "Jira pull failed")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.job, "decision.md")) as f:
            self.assertEqual(f.read(), "NEEDS-HUMAN\nFLAGS: none\n\n## Why\nJira pull failed\n\n## For the human\n1. Jira pull failed\n")
        j = self.job_json()
        self.assertEqual((j["stage"], j["decision"]), ("needs-human", "NEEDS-HUMAN"))
        self.assertEqual(self.sf("verdict", os.path.join(self.job, "decision.md")).stdout.strip(), "NEEDS-HUMAN flags=none")


if __name__ == "__main__":
    unittest.main()
