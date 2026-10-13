from __future__ import annotations

import os
import re
import unittest

import helpers

PROMPT = os.path.join(helpers.REPO, ".github", "prompts", "story-lite.prompt.md")


class PromptFileTests(unittest.TestCase):
    def setUp(self):
        with open(PROMPT) as f:
            self.text = f.read()
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", self.text, re.S)
        self.assertIsNotNone(m, "no frontmatter")
        self.body = m.group(2)
        self.front = {}
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            self.front[k.strip()] = v.strip()

    def test_frontmatter(self):
        self.assertEqual(sorted(self.front), ["agent", "argument-hint", "description", "name", "tools"])
        self.assertEqual(self.front["name"], "story-lite")
        self.assertEqual(self.front["agent"], "agent")
        tools = re.findall(r"'([^']+)'", self.front["tools"])
        self.assertEqual(tools, ["read", "search", "edit", "execute"])
        for word in ("bug", "spike", "epic", "refine", "children", "resume", "approve", "rework", "render"):
            self.assertIn(word, self.front["argument-hint"])

    def test_agent_files_exist(self):
        names = set(re.findall(r"\.claude/agents/([A-Za-z0-9<>_-]+)\.md", self.body))
        self.assertIn("story-writer", names)
        self.assertIn("story-approver", names)
        for n in names:
            if "<" in n:
                continue
            self.assertTrue(os.path.exists(os.path.join(helpers.REPO, ".claude", "agents", n + ".md")), n)
        for lens in ("invest", "ac", "tech", "security"):
            self.assertTrue(os.path.exists(os.path.join(helpers.REPO, ".claude", "agents", "reviewer-%s.md" % lens)))

    def test_required_phrases(self):
        for phrase in ("--harness copilot-lite", "security, tech, ac, invest", "gate ID --apply", "Never",
                       "resume", "sf.py claim", "BUSY", "next-child", "spawn-children", "epic-status",
                       "Reviewed in one context (Copilot lite)."):
            self.assertIn(phrase, self.body)

    def test_no_urls(self):
        self.assertNotIn("http", self.text)

    def test_sf_commands_exist(self):
        import subprocess, sys
        out = subprocess.run([sys.executable, os.path.join(helpers.REPO, "scripts", "sf.py"), "-h"],
                             capture_output=True, text=True).stdout
        for name in set(re.findall(r"sf\.py (?:-\S+ )*([a-z][a-z-]+)", self.body)):
            if name in ("claim", "release", "job", "new-job", "brief", "validate", "render", "checks",
                        "verdict", "gate", "escalate", "jira-keys"):
                self.assertIn(name, out, name)


if __name__ == "__main__":
    unittest.main()
