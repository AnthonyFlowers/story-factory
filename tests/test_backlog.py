from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

import helpers

EXAMPLE = os.path.join(helpers.REPO, "factory", "backlog.example.md")


class BacklogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = os.path.join(self.tmp, "backlog.md")
        shutil.copyfile(EXAMPLE, self.path)
        self.env = dict(os.environ, STORY_FACTORY_BACKLOG=self.path, STORY_FACTORY_CONFIG=helpers.TEST_CONFIG)

    def sf(self, *args):
        return subprocess.run([sys.executable, helpers.SF, "backlog"] + list(args), capture_output=True,
                              text=True, env=self.env)

    def lines(self):
        with open(self.path) as f:
            return f.read().split("\n")

    def test_claim_order_and_prefixes(self):
        r = self.sf("claim")
        parts = r.stdout.rstrip("\n").split("\t")
        self.assertEqual(parts[1:], ["story", "Add the service version to the GET /health response"])
        n = int(parts[0])
        self.assertTrue(self.lines()[n - 1].startswith("- [x] Add the service") and
                        self.lines()[n - 1].endswith("→ claimed"))
        self.assertEqual(self.sf("claim").stdout.rstrip("\n").split("\t")[1:], ["refine", "DEMO-101"])
        third = self.sf("claim").stdout.rstrip("\n").split("\t")
        self.assertEqual(third[1], "bug")
        self.assertTrue(third[2].startswith("GET /accounts/"))

    def test_done(self):
        n = self.sf("claim").stdout.split("\t")[0]
        r = self.sf("done", n, "001-add-service-version")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.lines()[int(n) - 1].endswith("→ 001-add-service-version"))
        self.assertNotEqual(self.sf("done", n, "x").returncode, 0)  # no longer claimed

    def test_empty_backlog(self):
        for _ in range(3):
            self.sf("claim")
        r = self.sf("claim")
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_missing_backlog_copied_from_example(self):
        os.unlink(self.path)
        r = self.sf("claim")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("backlog.example.md", r.stderr)
        self.assertTrue(r.stdout.startswith("5\t") or r.stdout.split("\t")[0].isdigit())

    def test_concurrent_claims_differ(self):
        out = []

        def go():
            out.append(self.sf("claim").stdout.split("\t")[0])

        ts = [threading.Thread(target=go) for _ in range(3)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(set(out)), 3, out)
        self.assertNotIn("", out)


if __name__ == "__main__":
    unittest.main()
