from __future__ import annotations

from .. import server


def run(args):
    return server.serve(port=args.port, jobs_dir=args.jobs_dir)


def register(subparsers):
    p = subparsers.add_parser("dashboard", help="serve the local HTML dashboard (127.0.0.1 only)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--jobs-dir", help="serve DIR (containing dashboard.html and jobs/) instead of factory/")
    p.set_defaults(func=run)
