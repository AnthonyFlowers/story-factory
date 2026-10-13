from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest

import helpers
from sflib import renderers
from sflib.renderers import markdown
from sflib import template


def load(name):
    with open(os.path.join(helpers.STORIES, name)) as f:
        return json.load(f)


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tpl = template.load_template("default")

    def test_golden(self):
        with open(os.path.join(helpers.STORIES, "story.expected.md")) as f:
            expected = f.read()
        self.assertEqual(markdown.render(load("story.json"), self.tpl), expected)

    def test_paste_safe(self):
        for name in ("story", "bug", "spike", "epic"):
            text = markdown.render(load(name + ".json"), self.tpl)
            self.assertTrue(text.startswith("# "), name)
            for line in text.split("\n"):
                self.assertIsNone(re.match(r"^\s+[-*0-9]", line), (name, line))
                self.assertFalse(line.startswith("|"), (name, line))
                self.assertIsNone(re.search(r"\[[ x]\]", line), (name, line))
                self.assertIsNone(re.search(r"<[a-z]", line), (name, line))

    def test_epic_children_sorted_and_deps(self):
        text = markdown.render(load("epic.json"), self.tpl)
        self.assertLess(text.index("- C1 "), text.index("- C3 "))
        self.assertIn("Depends on: C2.", text)

    def test_open_questions_rendered(self):
        s = load("story.json")
        s["open_questions"] = ["Is the range inclusive?"]
        text = markdown.render(s, self.tpl)
        self.assertIn("## Open questions for the team\n\n- Is the range inclusive?", text)
        self.assertLess(text.index("## Out of scope"), text.index("## Open questions for the team"))

    def test_custom_section(self):
        tpl = dict(self.tpl, custom_sections=[
            {"id": "nfr", "heading": "Non-functional requirements", "style": "bullets",
             "types": ["story"], "required": True}])
        s = load("story.json")
        self.assertIn("_Missing: Non-functional requirements_", markdown.render(s, tpl))
        s["extra"] = {"nfr": ["p95 under 300 ms"]}
        self.assertIn("## Non-functional requirements\n\n- p95 under 300 ms", markdown.render(s, tpl))

    def test_registry(self):
        self.assertIs(renderers.get("md"), markdown)

    def test_cli_render_stdout(self):
        env = dict(os.environ)
        env.pop("STORY_FACTORY_CONFIG", None)
        out = subprocess.run([sys.executable, helpers.SF, "render", os.path.join(helpers.STORIES, "story.json")],
                             capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 0, out.stderr)
        with open(os.path.join(helpers.STORIES, "story.expected.md")) as f:
            self.assertEqual(out.stdout, f.read())


if __name__ == "__main__":
    unittest.main()
