# safe-autonomous-learning

Let your AI systems heal themselves and teach each other, without leaking client data.

Three small, independent tools for anyone running scheduled AI automation across more than one project,
especially under confidentiality (security, legal, consulting, healthcare). No framework, no lock-in.
Point them at what you already run.

## Where this came from

I run a fleet of AI agents, one per project. One day I asked mine a simple question: are they actually
self-healing and learning from each other? The honest answer was no. Two of my scheduled jobs had been
dying silently for six days after a sync deleted their scripts, and the "shared brain" my agents were
supposed to learn from held exactly one lesson.

Fixing that surfaced three reusable pieces. The interesting one is the last: I wanted every project's
learning to reach every other project, but a few of my projects are client-confidential. Sharing a
lesson that carries client data from one into another is not an oops, it is a breach. So the gate that
decides what gets shared had to be hard code, not a model being asked to be careful.

## The tools

### 1. [`client-data-gate`](./client-data-gate) — the one that matters
A fail-closed filter: text publishes only if it is provably free of client-data signals (names you
configure, plus paths, emails, URLs caught structurally). Unknown or unmatched is held, never shared.
Over-holding is a safe mistake; leaking is not. This is the piece that makes cross-project AI learning
safe for confidential work.

### 2. [`job-watchdog`](./job-watchdog)
A silently-dead scheduled job becomes a notification. Reads each job's last exit status and pings you
on any non-zero (deduped). Includes the wait-status decoder everyone gets wrong (exit 127 shows up as
32512). Always exits 0 so it never becomes the failing job it reports.

### 3. [`auto-learn`](./auto-learn)
The capture → distill → write-back loop that makes a knowledge base compound, with the gate wired in.
Reads new notes, distills each into a generic HOW-only lesson via any LLM CLI, and publishes only the
clean ones. Client-tainted drafts are held for a human.

## Install

Nothing to install. Python 3, standard library only (the LLM step shells out to a CLI you already
have). Clone it, run the tests, wire the tools at what you run.

```bash
git clone https://github.com/assafkip/safe-autonomous-learning.git
cd safe-autonomous-learning
python3 client-data-gate/test_gate.py
python3 job-watchdog/test_watchdog.py
python3 auto-learn/test_distill.py
```

## Design stance

- **Prevention beats detection beats rollback.** A leak can't be rolled back, so the publish decision
  is deterministic, not model judgment.
- **Fail-closed.** When unsure, hold and surface. Never guess in the leaking direction.
- **Composable, not a framework.** Three files you can read in ten minutes and adopt one at a time.
- **Tested, reproducer-first.** Every guarantee has a test that shows the failure, then shows it fixed.

## License

MIT. Use it however you want. Make it your own.
