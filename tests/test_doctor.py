from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest

import helpers
from sflib import doctor


def git(cwd, *args):
    subprocess.run(["git"] + list(args), cwd=cwd, check=True, capture_output=True)


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        git(self.tmp, "init", "-q")
        shutil.copy(os.path.join(helpers.REPO, ".gitignore"), self.tmp)

    def test_clean(self):
        self.assertEqual(doctor.check(self.tmp), [])

    def test_allowed_gitkeeps(self):
        for p in ("factory/jobs/.gitkeep", "templates/local/.gitkeep"):
            os.makedirs(os.path.join(self.tmp, os.path.dirname(p)), exist_ok=True)
            open(os.path.join(self.tmp, p), "w").close()
            git(self.tmp, "add", "-f", p)
        self.assertEqual(doctor.check(self.tmp), [])

    def test_missing_ignore_line(self):
        gi = os.path.join(self.tmp, ".gitignore")
        text = open(gi).read().replace("factory.config.json\n", "")
        open(gi, "w").write(text)
        self.assertTrue(any("factory.config.json" in p for p in doctor.check(self.tmp)))

    def test_tracked_local_file(self):
        open(os.path.join(self.tmp, "factory.config.json"), "w").write("{}")
        git(self.tmp, "add", "-f", "factory.config.json")
        self.assertTrue(any("factory.config.json" in p for p in doctor.check(self.tmp)))

    def test_pre_commit_hook_blocks(self):
        hook = os.path.join(helpers.REPO, "scripts", "hooks", "pre-commit")
        os.makedirs(os.path.join(self.tmp, "factory", "jobs", "001-x"))
        open(os.path.join(self.tmp, "factory", "jobs", "001-x", "job.json"), "w").write("{}")
        open(os.path.join(self.tmp, "factory", "jobs", ".gitkeep"), "w").close()
        git(self.tmp, "add", "-f", "factory")
        r = subprocess.run(["sh", hook], cwd=self.tmp, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("factory/jobs/001-x/job.json", r.stderr)
        self.assertNotIn(".gitkeep", r.stderr)
        git(self.tmp, "reset", "-q")
        git(self.tmp, "add", "-f", "factory/jobs/.gitkeep")
        self.assertEqual(subprocess.run(["sh", hook], cwd=self.tmp).returncode, 0)


if __name__ == "__main__":
    unittest.main()


class DoctorTrustWarningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cj = os.path.join(self.tmp, "claude.json")

    def write(self, data):
        with open(self.cj, "w") as f:
            json.dump(data, f)

    def test_untrusted_warns(self):
        self.write({"projects": {}})
        w = doctor.warnings(self.tmp, self.cj)
        self.assertEqual(len(w), 1)
        self.assertIn("trust dialog", w[0])

    def test_trusted_is_quiet(self):
        self.write({"projects": {os.path.realpath(self.tmp): {"hasTrustDialogAccepted": True}}})
        self.assertEqual(doctor.warnings(self.tmp, self.cj), [])

    def test_missing_state_file_is_quiet(self):
        self.assertEqual(doctor.warnings(self.tmp, self.cj), [])
