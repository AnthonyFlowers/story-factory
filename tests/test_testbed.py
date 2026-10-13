from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import helpers


class TestbedTests(unittest.TestCase):
    def test_creates_standalone_repo_and_snippet(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        dest = os.path.join(tmp, "team")
        r = subprocess.run([sys.executable, os.path.join(helpers.REPO, "scripts", "sf.py"), "testbed", dest],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(dest, "openapi.json")))
        log = subprocess.run(["git", "log", "--oneline"], cwd=dest, capture_output=True, text=True).stdout
        self.assertEqual(len(log.splitlines()), 1)
        snippet = json.loads(r.stdout[r.stdout.index("{"):])
        self.assertEqual(snippet["repos"][0]["path"], dest)
        again = subprocess.run([sys.executable, os.path.join(helpers.REPO, "scripts", "sf.py"), "testbed", dest],
                               capture_output=True, text=True)
        self.assertNotEqual(again.returncode, 0)

    def test_testbed_has_no_nested_git_and_is_not_in_example_config(self):
        self.assertFalse(os.path.exists(os.path.join(helpers.REPO, "testbed", "team-repo", ".git")))
        with open(os.path.join(helpers.REPO, "factory.config.example.json")) as f:
            self.assertNotIn("testbed", f.read())
        with open(os.path.join(helpers.REPO, "tests", "fixtures", "factory.config.test.json")) as f:
            self.assertNotIn("testbed", f.read())
