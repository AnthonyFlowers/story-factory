from __future__ import annotations

import os
import re
import unittest

import helpers

AGENTS = os.path.join(helpers.REPO, ".claude", "agents")
SPEC = {
    "story-writer": ("opus", "story.json"),
    "reviewer-invest": ("sonnet", "round-<N>/review-invest.md"),
    "reviewer-ac": ("sonnet", "round-<N>/review-ac.md"),
    "reviewer-tech": ("sonnet", "round-<N>/review-tech.md"),
    "reviewer-security": ("opus", "round-<N>/review-security.md"),
    "story-approver": ("opus", "decision.md"),
}
FORBIDDEN = {"Bash", "Edit", "WebFetch", "WebSearch", "Agent"}


def parse(name):
    with open(os.path.join(AGENTS, name + ".md")) as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert m, "no frontmatter in %s" % name
    fm = {}
    for line in m.group(1).splitlines():
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip().strip('"')
    return fm, m.group(2)


class AgentTests(unittest.TestCase):
    def test_agents(self):
        for name, (model, out) in SPEC.items():
            with self.subTest(agent=name):
                fm, body = parse(name)
                self.assertEqual(sorted(fm), ["description", "model", "name", "tools"])
                self.assertEqual(fm["name"], name)
                self.assertEqual(fm["model"], model)
                tools = {t.strip() for t in fm["tools"].split(",")}
                self.assertEqual(tools, {"Read", "Grep", "Glob", "Write"})
                self.assertFalse(tools & FORBIDDEN)
                self.assertIn(out, body)
                self.assertIn("exactly one file", body)
                self.assertIn("Job folder: <abs job dir>. Repo root: <abs factory root>.", body)
                self.assertIn("No estimates", body)
                if name.startswith("reviewer-"):
                    self.assertIn("VERDICT: PASS", body)
                    self.assertIn("FLAGS:", body)
                if name == "story-approver":
                    self.assertIn("NEEDS-HUMAN", body)
                    self.assertIn("## Escalation", body)

    def test_no_stray_agent_files(self):
        self.assertEqual(sorted(f[:-3] for f in os.listdir(AGENTS) if f.endswith(".md")), sorted(SPEC))


class ReviewerWriteRuleTests(unittest.TestCase):
    def test_reviewers_must_write_the_file(self):
        for name in ("reviewer-invest", "reviewer-ac", "reviewer-tech", "reviewer-security"):
            with self.subTest(agent=name):
                self.assertIn("Never return the review as your reply", parse(name)[1])


if __name__ == "__main__":
    unittest.main()
