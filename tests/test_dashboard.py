from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
import urllib.request

import helpers
import make_demo_jobs
from sflib import server

HTML = os.path.join(helpers.REPO, "factory", "dashboard.html")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class DashboardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        make_demo_jobs.main(cls.dir)
        cls.httpd = server.make_server(cls.dir, free_port())
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        shutil.rmtree(cls.dir, True)

    def get(self, path):
        return urllib.request.urlopen("http://127.0.0.1:%d/%s" % (self.port, path))

    def test_binds_loopback_only(self):
        self.assertEqual(self.httpd.server_address[0], "127.0.0.1")

    def test_serves_files_with_no_store(self):
        r = self.get("dashboard.html")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.headers["Cache-Control"], "no-store")
        listing = self.get("jobs/").read().decode()
        self.assertIn("004-refine-demo-101/", listing)
        job = json.loads(self.get("jobs/004-refine-demo-101/job.json").read())
        self.assertEqual(job["stage"], "review")

    def test_eight_demo_jobs(self):
        self.assertEqual(len(os.listdir(os.path.join(self.dir, "jobs"))), 8)

    def test_html_static_properties(self):
        html = open(HTML).read()
        self.assertNotRegex(html, r"https?://")
        self.assertEqual(html.count("Content-Security-Policy"), 1)
        self.assertIn("esc(", html.split("function cardHtml")[1].split("function render")[0])
        script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
        for key in ["intake", "draft", "review", "approve", "children", "ready", "needs-human",
                    "invest", "ac", "tech", "security"]:
            self.assertIn("'%s'" % key, script)

    def test_script_syntax(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        script = re.search(r"<script>(.*?)</script>", open(HTML).read(), re.S).group(1)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(script)
        self.addCleanup(os.unlink, f.name)
        r = subprocess.run([node, "--check", f.name], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
