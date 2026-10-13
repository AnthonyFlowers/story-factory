from __future__ import annotations

import functools
import http.server
import os

from . import SFError, config

HOST = "127.0.0.1"


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass


def make_server(directory: str, port: int = 8765) -> http.server.ThreadingHTTPServer:
    handler = functools.partial(Handler, directory=directory)
    return http.server.ThreadingHTTPServer((HOST, port), handler)


def serve(port: int = 8765, jobs_dir: str = None) -> int:
    directory = jobs_dir or os.path.join(config.root(), "factory")
    if not os.path.isfile(os.path.join(directory, "dashboard.html")):
        raise SFError("dashboard.html not found in %s" % directory)
    try:
        httpd = make_server(directory, port)
    except OSError as e:
        raise SFError("cannot bind %s:%s: %s" % (HOST, port, e))
    print("Dashboard: http://%s:%d/dashboard.html" % (HOST, httpd.server_address[1]), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
