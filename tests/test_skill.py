from __future__ import annotations

import os
import re
import unittest

import helpers

SKILL = os.path.join(helpers.REPO, ".claude", "skills", "story", "SKILL.md")


class SkillTests(unittest.TestCase):
    def setUp(self):
        with open(SKILL) as f:
            self.text = f.read()
        m = re.match(r"^---\n(.*?)\n---\n", self.text, re.S)
        self.assertIsNotNone(m, "no frontmatter")
        self.front = {}
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            self.front[k.strip()] = v.strip()

    def test_frontmatter_keys(self):
        self.assertEqual(sorted(self.front),
                         sorted(["name", "description", "argument-hint", "disable-model-invocation", "allowed-tools"]))
        self.assertEqual(self.front["name"], "story")
        self.assertEqual(self.front["disable-model-invocation"], "true")
        self.assertIn("Bash(python3 scripts/sf.py *)", self.front["allowed-tools"])
        self.assertIn("Bash(python3 scripts/jira_stub.py *)", self.front["allowed-tools"])

    def test_subcommands(self):
        hint = self.front["argument-hint"]
        for name in ("bug", "spike", "epic", "refine", "next", "approve", "rework", "resume", "render", "children"):
            self.assertIn(name, hint)
            self.assertIn(name, self.text)

    def test_required_phrases(self):
        for phrase in ("in ONE message", "WAIT FOR ALL", "SendMessage", "sf.py gate", "--apply", "never write to Jira",
                       "sf.py claim", "BUSY", "--force"):
            self.assertIn(phrase, self.text)

    def test_agents(self):
        for a in ("story-writer", "reviewer-invest", "reviewer-ac", "reviewer-tech", "reviewer-security",
                  "story-approver"):
            self.assertIn(a, self.text)
            self.assertTrue(os.path.isfile(os.path.join(helpers.REPO, ".claude", "agents", a + ".md")))

    def test_section_order_and_size(self):
        heads = re.findall(r"^## \d+\. (.+)$", self.text, re.M)
        want = ["Role", "The loop", "Parse arguments", "Prompts", "New job", "Draft", "Review round N", "Approve",
                "Report"]
        self.assertEqual(heads[:len(want)], want)
        self.assertLessEqual(len(self.text.splitlines()), 250)

    def test_sf_commands_exist(self):
        import subprocess, sys
        cmds = set(re.findall(r"sf\.py ([a-z-]+)", self.text))
        out = subprocess.run([sys.executable, helpers.SF, "-h"], capture_output=True, text=True).stdout
        for c in cmds:
            self.assertIn(c, out, "SKILL.md uses unknown sf.py command %s" % c)


if __name__ == "__main__":
    unittest.main()
