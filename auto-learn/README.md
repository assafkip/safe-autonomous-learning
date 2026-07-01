# auto-learn

The loop that makes a knowledge base compound instead of sit still — made safe for confidential work.

## Why

Most "second brain" setups capture notes but never distill them, so the pile grows and the insight
doesn't. The fix is a loop: read new notes → distill each into a reusable, generic lesson → write it
back into the shared store → the next distillation builds on it.

The catch when you do this **across projects**: a distilled lesson can carry client data. So here the
write-back is **fail-closed** — a lesson publishes only if it passes the [client-data-gate](../client-data-gate).
Clean lessons flow; anything tainted is held for a human, never shared.

## Use

```bash
python3 distill.py \
  --sources ./notes \          # dir of .md notes to distill from
  --out ./lessons \            # where clean lessons are published
  --held ./held \              # where gated (possible client data) drafts land for review
  --ledger ./.processed.json \ # so each note is processed once
  --config ../client-data-gate/config.json \
  --llm-cmd 'claude -p'        # any CLI that takes a prompt as its last arg

# preview without writing / without spend
python3 distill.py ... --dry
```

Schedule it daily (with [job-watchdog](../job-watchdog) covering it) and you have an autonomous learning
loop that never leaks.

## How the gate works here

1. Distill note → `{title, body}` via the LLM (prompted for HOW-only, no specifics).
2. **Deterministic gate:** scrub known signals (tokens, codenames, paths, emails, URLs); the scrubbed
   text must be `is_clean`.
3. **LLM semantic pass:** a second check for a novel real entity the regex can't know.
4. Both must pass → publish. Otherwise → **held**, surfaced, never published.

## Test

```bash
python3 test_distill.py     # clean publishes, client path scrubbed, held held, idempotent — exit 0
```
