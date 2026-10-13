# 0051. claim takes over a claim whose holder process is dead

- Date: 2026-10-13
- Status: accepted
- By: coordinator (smoke test bug 3)

## Decision

`sf.py claim` takes over an existing claim without `--force` when its `who` is the default `<this hostname>:<pid>` label and `kill(pid, 0)` says that process is gone. The default label's pid is the parent of `sf.py`, which in Claude Code is the long-lived session process, so it is a real liveness signal. Custom `--who` labels, other hosts and live pids stay BUSY. The check and the takeover run under an exclusive `flock` on the job directory. Output is `CLAIMED ID (took over a stale claim from WHO, its process is gone)`.

## Why

After a crashed headless run, `/story resume` printed BUSY for a dead pid and the session could not check liveness (`ps` is not allowed), so the user had to run `claim --force` by hand. Decision 0036 left liveness to the human.

## How to undo

Remove `holder_is_dead` and the takeover branch in `claims.claim`; `--force` still works.
