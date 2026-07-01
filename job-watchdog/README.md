# job-watchdog

Turn a silently-dead scheduled job into a notification.

## Why

A scheduled job that starts failing usually fails *silently* — it stops doing its work and nobody is
told. (This tool exists because two of my jobs exited 127 every morning for six days before anyone
noticed. The income they were supposed to find simply stopped, quietly.)

A prompt can't watch a scheduler. A job can. This one reads each job's last exit status and pings you
on any non-zero, deduped so a persistent failure doesn't spam.

## Use

```bash
# watch every launchd job under a label prefix; print failures
python3 watchdog.py --prefix com.myapp. --dry

# notify via any command (the message is passed as the final arg) — e.g. a Slack webhook script
python3 watchdog.py --prefix com.myapp. --notify-cmd './slack-notify.sh'
```

Schedule it as its own launchd job (twice a day is plenty). It always exits 0, so it never becomes the
failing job it reports.

## The one non-obvious bit

`launchctl` reports `LastExitStatus` as a raw `wait(2)` status, not the exit code: **exit 3 shows up
as 768**, exit 127 as 32512. `normalize_exit()` decodes it so your alert reads "exit 127", not a
confusing 32512. If you roll your own, this is the part you'll get wrong.

## Porting

macOS/launchd today. `last_exit_status()` is the only platform-specific reader — swap it for a cron
wrapper (log exit codes to a file) or `systemctl show -p ExecMainStatus` and the rest is unchanged.

## Test

```bash
python3 test_watchdog.py     # decoder cases, exit 0 = pass
```
