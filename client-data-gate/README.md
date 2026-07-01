# client-data-gate

A fail-closed filter that decides whether a piece of text is safe to publish — before an autonomous
system shares it somewhere it can't be taken back.

## Why

If you let an AI system learn from one project and share that learning with another, you have a leak
risk: client A's data ending up in client B's context. For anyone working under confidentiality
(legal, consulting, security, healthcare) that's a non-starter, and the leak can hide in a file path
or a name, not just the obvious body text.

The usual answer is "ask the model to be careful." That's not a control. **This is a control:** a
deterministic gate that publishes only what is provably clean, and holds everything else.

## Guarantee

`is_clean(text)` returns `True` only when the text contains **zero** client-data signals:

- configured **tokens** (client / product / person strings you name),
- a configured **codename** roster (distinctive identifiers matched as whole words),
- always-on structural patterns: **absolute paths, emails, URLs**.

Fail-closed: unknown or unmatched → **held**, never published. Over-holding is a safe false positive;
leaking is not.

## Use

```python
from gate import is_clean, scrub, load_config

cfg = load_config("config.json")          # or pass a dict

if is_clean(candidate, cfg):
    publish(candidate)                     # provably clean
else:
    scrubbed, hits = scrub(candidate, cfg)
    if is_clean(scrubbed, cfg):
        publish(scrubbed)                  # cleaned, then re-gated
    else:
        hold(candidate, hits)              # surface for a human; never leak
```

CLI:

```bash
echo "the AcmeCorp file at /Users/jane/x.py" | python3 gate.py config.json
# -> HELD: token:AcmeCorp, path:/Users/jane/x.py   (exit 1)
```

Pair it with an LLM semantic pass for a second net (the deterministic gate is the hard floor; the LLM
is the soft catch for novel names a regex can't know). See `../auto-learn` for that pattern.

## Config

Copy `config.example.json` → `config.json`. `tokens` are substrings (case-insensitive); `codenames`
are whole-word identifiers. Use `codenames_from_names([...])` to build a roster from a list of project
names while dropping generic words like "accountant".

## Test

```bash
python3 test_gate.py     # 11 cases, exit 0 = pass
```
