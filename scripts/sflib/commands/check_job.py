from __future__ import annotations

from .. import SFError, checkjob


def run(args):
    if args.manifest:
        if args.compare:
            try:
                diff, n = checkjob.compare_manifest()
            except FileNotFoundError:
                raise SFError("no manifest; run 'sf.py check-job --manifest' before the test", 2)
            for d in diff:
                print(d)
            print("FAIL manifest changed" if diff else "OK manifest unchanged (%d files)" % n)
            return 1 if diff else 0
        n = checkjob.write_manifest()
        print("manifest written: %d files" % n)
        return 0
    if args.compare:
        raise SFError("--compare needs --manifest", 2)
    if not args.id:
        raise SFError("check-job needs a job ID (or --manifest)", 2)
    results = checkjob.check_job(args.id, args.allow_running)
    lines = checkjob.format_results(results)
    print("\n".join(lines))
    return 0 if lines[-1] == "RESULT: PASS" else 1


def register(subparsers):
    p = subparsers.add_parser("check-job", help="verify a finished job's invariants; --manifest guards team repos")
    p.add_argument("id", nargs="?")
    p.add_argument("--allow-running", action="store_true", help="allow an epic at stage 'children'")
    p.add_argument("--manifest", action="store_true",
                   help="hash every configured repo and team-docs file into <jobs>/.manifest.json")
    p.add_argument("--compare", action="store_true", help="with --manifest: compare against the saved manifest")
    p.set_defaults(func=run)
