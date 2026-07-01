#!/usr/bin/env python3
"""job-watchdog: turn a silently-dead scheduled job into a notification.

A scheduled job (launchd on macOS) that starts failing usually fails SILENTLY — it just stops doing
its work and nobody is told. This watchdog reads each job's last exit status and notifies (deduped)
on any non-zero, so a silent death becomes a ping within hours instead of days.

It always exits 0 so the watchdog never becomes the failing job it reports.

Configure the label prefix (which jobs to watch), a notify command (Slack webhook, `notify-send`,
anything — the message is passed as the last arg), and a dedup TTL. macOS/launchd today; the
`last_exit_status` reader is the only platform-specific piece (swap it for a cron/systemd reader).

Usage:
  watchdog.py                         # check + notify on new/again failures
  watchdog.py --dry                   # print findings, no notify, no state write
  watchdog.py --prefix com.myapp.     # which jobs
  watchdog.py --notify-cmd './slack.sh'   # command to run with the message as final arg
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SELF_HINT = "job-watchdog"  # never report a job whose label contains this


def normalize_exit(raw):
    """launchd reports LastExitStatus as a raw wait(2) status. Decode to the human exit code:
    exit 3 arrives as 3<<8 = 768; a signal kill as 128+signal. A small value (<256) is already
    a clean code, so pass it through. This is the bit everyone gets wrong."""
    if raw == 0 or 0 < raw < 256:
        return raw
    exit_code = (raw >> 8) & 0xFF
    if exit_code:
        return exit_code
    signal_num = raw & 0x7F
    return 128 + signal_num if signal_num else raw


def launchd_labels(prefix):
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return []
    labels = []
    for line in out.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 3 and parts[2].startswith(prefix):
            labels.append(parts[2].strip())
    return labels


def last_exit_status(label):
    try:
        out = subprocess.run(["launchctl", "list", label], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return 0
    m = re.search(r'"LastExitStatus"\s*=\s*(-?\d+)', out)
    return normalize_exit(int(m.group(1))) if m else 0


def discover_failing(prefix):
    return [(lbl, last_exit_status(lbl)) for lbl in launchd_labels(prefix)
            if SELF_HINT not in lbl and last_exit_status(lbl) != 0]


def load_state(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}


def notify(notify_cmd, message):
    if not notify_cmd:
        print(message)
        return
    try:
        subprocess.run(notify_cmd.split() + [message], timeout=20)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="com.example.")
    ap.add_argument("--notify-cmd", default="")
    ap.add_argument("--state", default=str(Path.home() / ".job-watchdog-state.json"))
    ap.add_argument("--ttl", type=int, default=6 * 3600, help="re-notify a still-failing job at most this often")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    failing = discover_failing(args.prefix)
    if not failing:
        if args.dry:
            print(f"all jobs matching {args.prefix} healthy (exit 0)")
        sys.exit(0)

    for label, code in failing:
        print(f"FAILING: {label} exit {code}")

    state = load_state(args.state)
    now = int(time.time())
    due = [(l, c) for l, c in failing if now - state.get(l, {}).get("at", 0) >= args.ttl]

    if args.dry:
        print(f"[dry] would notify {len(due)} job(s)")
        sys.exit(0)

    if due:
        summary = ", ".join(f"{l} (exit {c})" for l, c in due)
        notify(args.notify_cmd, f"job-watchdog: {len(due)} job(s) failing — {summary}")
        for l, c in due:
            state[l] = {"at": now, "exit": c}
    failing_labels = {l for l, _ in failing}
    for l in [k for k in state if k not in failing_labels]:
        state.pop(l)
    Path(args.state).write_text(json.dumps(state, indent=2))
    sys.exit(0)  # a watchdog must never report itself as failing


if __name__ == "__main__":
    main()
