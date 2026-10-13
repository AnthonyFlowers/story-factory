from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

import helpers
import test_gate
from test_jobs import JobsTestCase


class ClaimTests(JobsTestCase):
    def job(self, jid):
        with open(os.path.join(self.jobs, jid, "job.json")) as f:
            return json.load(f)

    def test_new_job_auto_claims(self):
        jid = self.new("claim me")
        self.assertTrue(os.path.isfile(os.path.join(self.jobs, jid, ".claim")))
        self.assertTrue(self.job(jid)["claimed_by"])
        r = self.sf("claim", jid, "--who", "other")
        self.assertEqual(r.returncode, 3)
        self.assertTrue(r.stdout.startswith("BUSY %s " % jid))

    def test_release_then_claim(self):
        jid = self.new("claim me")
        self.assertEqual(self.sf("release", jid).returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.jobs, jid, ".claim")))
        self.assertIsNone(self.job(jid)["claimed_by"])
        r = self.sf("claim", jid, "--who", "sess-a")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "CLAIMED " + jid))
        self.assertEqual(self.job(jid)["claimed_by"], "sess-a")

    def test_force(self):
        jid = self.new("claim me")
        self.assertEqual(self.sf("claim", jid, "--who", "b").returncode, 3)
        r = self.sf("claim", jid, "--who", "b", "--force")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.job(jid)["claimed_by"], "b")

    def test_dead_holder_is_taken_over(self):
        import socket
        jid = self.new("stale")
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        self.sf("claim", jid, "--who", "%s:%d" % (socket.gethostname(), dead.pid), "--force")
        r = self.sf("claim", jid, "--who", "sess-b")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("took over a stale claim", r.stdout)
        self.assertEqual(self.job(jid)["claimed_by"], "sess-b")

    def test_live_or_custom_holder_stays_busy(self):
        import socket
        jid = self.new("live")
        self.sf("claim", jid, "--who", "%s:%d" % (socket.gethostname(), os.getpid()), "--force")
        self.assertEqual(self.sf("claim", jid, "--who", "x").returncode, 3)
        self.sf("claim", jid, "--who", "custom-label", "--force")
        self.assertEqual(self.sf("claim", jid, "--who", "x").returncode, 3)
        self.sf("claim", jid, "--who", "otherhost:99999999", "--force")
        self.assertEqual(self.sf("claim", jid, "--who", "x").returncode, 3)

    def test_concurrent_claims_one_winner(self):
        jid = self.new("race")
        self.sf("release", jid)
        rcs = []

        def go(i):
            rcs.append(self.sf("claim", jid, "--who", "s%d" % i).returncode)

        ts = [threading.Thread(target=go, args=(i,)) for i in range(4)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sorted(rcs), [0, 3, 3, 3])

    def test_escalate_releases(self):
        jid = self.new("esc")
        r = self.sf("escalate", jid, "--why", "test")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.jobs, jid, ".claim")))
        self.assertIsNone(self.job(jid)["claimed_by"])


class GateReleaseTests(test_gate.GateTests):
    def test_gate_apply_releases_claim(self):
        self.assertEqual(self.sf("claim", "900-sample", "--who", "me").returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(self.job, ".claim")))
        r = self.sf("gate", "900-sample", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.job, ".claim")))
        with open(os.path.join(self.job, "job.json")) as f:
            self.assertIsNone(json.load(f)["claimed_by"])


# Do not re-run GateTests' own cases under this module.
for _n in [n for n in dir(GateReleaseTests) if n.startswith("test_") and n != "test_gate_apply_releases_claim"]:
    setattr(GateReleaseTests, _n, None)

if __name__ == "__main__":
    unittest.main()
