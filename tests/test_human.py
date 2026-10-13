from __future__ import annotations

import unittest

import helpers  # noqa: F401
from sflib.commands import human

DECISION = "NEEDS-HUMAN\nFLAGS: pii\n\n## Why\nx\n\n## For the human\n1. Q one?\n2. Q two?\n\n## Notes\nignored\n"


class HumanTests(unittest.TestCase):
    def test_section_extracted(self):
        self.assertEqual(human.human_section(DECISION), "## For the human\n1. Q one?\n2. Q two?\n")

    def test_section_at_end(self):
        self.assertEqual(human.human_section("A\n## For the human\n1. Q\n"), "## For the human\n1. Q\n")

    def test_missing(self):
        self.assertEqual(human.human_section("NEEDS-HUMAN\n## Why\nx\n"), "")

    def test_skill_has_no_command_substitution(self):
        import os
        with open(os.path.join(helpers.REPO, ".claude", "skills", "story", "SKILL.md")) as f:
            self.assertNotIn("$(python3", f.read())


if __name__ == "__main__":
    unittest.main()
