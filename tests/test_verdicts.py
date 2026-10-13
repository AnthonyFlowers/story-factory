from __future__ import annotations

import os
import subprocess
import sys
import unittest

import helpers
from sflib import verdicts

REV = os.path.join(helpers.FIX, "reviews")
DEC = os.path.join(helpers.FIX, "decisions")


class VerdictTests(unittest.TestCase):
    def test_parse_fixtures(self):
        self.assertEqual(verdicts.parse_file(os.path.join(REV, "pass.md")), ("PASS", []))
        self.assertEqual(verdicts.parse_file(os.path.join(REV, "changes-flags.md")), ("CHANGES", ["pii", "auth"]))
        self.assertEqual(verdicts.parse_file(os.path.join(DEC, "ready.md")), ("READY", []))
        self.assertEqual(verdicts.parse_file(os.path.join(DEC, "needs-human.md")), ("NEEDS-HUMAN", ["pii"]))

    def test_invalid(self):
        for name, reason in (("invalid-first-line.md", "first line"), ("invalid-flags.md", "unknown flag nonsense")):
            with self.assertRaises(verdicts.Invalid) as cm:
                verdicts.parse_file(os.path.join(REV, name))
            self.assertEqual(str(cm.exception), reason)
        for text, reason in (("", "empty file"), ("  \n", "empty file"), ("VERDICT: PASS\n", "flags line"),
                             ("VERDICT: PASS\nFLAGS:\n", "flags line"), ("VERDICT: MAYBE\nFLAGS: none\n", "first line"),
                             ("**VERDICT: PASS**\nFLAGS: none\n", "first line"), ("READY\nflags: none\n", "flags line")):
            with self.assertRaises(verdicts.Invalid) as cm:
                verdicts.parse_text(text)
            self.assertEqual(str(cm.exception), reason, text)

    def test_kind(self):
        with self.assertRaises(verdicts.Invalid):
            verdicts.parse_text("READY\nFLAGS: none\n", "review")
        with self.assertRaises(verdicts.Invalid):
            verdicts.parse_text("VERDICT: PASS\nFLAGS: none\n", "decision")

    def test_cli(self):
        def run(*a):
            return subprocess.run([sys.executable, helpers.SF, "verdict"] + list(a), capture_output=True, text=True)
        r = run(os.path.join(REV, "changes-flags.md"))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "CHANGES flags=pii,auth"))
        r = run(os.path.join(REV, "pass.md"))
        self.assertEqual(r.stdout.strip(), "PASS flags=none")
        r = run(os.path.join(REV, "invalid-first-line.md"))
        self.assertEqual((r.returncode, r.stdout.strip()), (1, "INVALID first line"))
        r = run(os.path.join(DEC, "needs-human.md"))
        self.assertEqual(r.stdout.strip(), "NEEDS-HUMAN flags=pii")


if __name__ == "__main__":
    unittest.main()
