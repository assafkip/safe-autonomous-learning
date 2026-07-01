#!/usr/bin/env python3
"""client-data-gate: a fail-closed filter that decides whether text is safe to publish.

The problem: an autonomous system that shares what it learns across projects can leak client data
from project A into project B. That leak is irreversible. So the decision to publish must be a hard,
deterministic check — not model judgment.

`is_clean(text)` returns True ONLY when the text contains zero client-data signals: configured
tokens (client/product/person names), the configured codename roster, and always-on structural
patterns (absolute paths, emails, URLs). Anything else -> not clean -> HOLD. Over-holding a clean
item is a safe false positive; leaking one is not. This gate holds.

`scrub(text)` best-effort replaces signals with placeholders; the caller must still gate on
`is_clean(scrubbed)` — scrub is a helper, not the guarantee.

stdlib only. Configure via a JSON file (see config.example.json) or pass a dict to load_config.
"""
import json
import re
from pathlib import Path

# Always-on structural signals (these identify real entities regardless of project).
PATH_RE = re.compile(r"/(?:Users|home|var|etc|opt|srv)/[^\s]*|(?:/[A-Za-z0-9_.\-]+){2,}")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
URL_RE = re.compile(r"https?://[^\s)]+")

DEFAULT_CONFIG = {
    "tokens": [],       # exact client/product/person strings, matched case-insensitive as substrings
    "codenames": [],    # distinctive identifiers matched as whole words (e.g. "Project_Falcon")
    "check_paths": True,
    "check_emails": True,
    "check_urls": True,
}


def load_config(source=None):
    """Accept a path, a dict, or None. Returns a config dict with defaults filled in."""
    cfg = dict(DEFAULT_CONFIG)
    if isinstance(source, dict):
        cfg.update(source)
    elif source:
        cfg.update(json.loads(Path(source).read_text()))
    return cfg


def find_client_data(text, config=None):
    """Return list of (category, matched_string) for every client-data signal. Empty list = clean."""
    cfg = load_config(config)
    hits = []
    for tok in cfg["tokens"]:
        if tok and re.search(re.escape(tok), text, re.IGNORECASE):
            hits.append(("token", tok))
    if cfg["check_urls"]:
        hits += [("url", m.group(0)) for m in URL_RE.finditer(text)]
    if cfg["check_emails"]:
        hits += [("email", m.group(0)) for m in EMAIL_RE.finditer(text)]
    if cfg["check_paths"]:
        hits += [("path", m.group(0)) for m in PATH_RE.finditer(text)]
    for name in cfg["codenames"]:
        if name and re.search(r"\b" + re.escape(name) + r"\b", text, re.IGNORECASE):
            hits.append(("codename", name))
    return hits


def is_clean(text, config=None):
    """Fail-closed: clean ONLY when no client-data signal is found."""
    return len(find_client_data(text, config)) == 0


_PLACEHOLDER = {"token": "[REDACTED]", "url": "[URL]", "email": "[EMAIL]",
                "path": "[PATH]", "codename": "[REDACTED]"}


def scrub(text, config=None):
    """Best-effort replace signals with placeholders. Returns (scrubbed_text, hits).
    Always re-gate with is_clean(scrubbed) — scrub is a helper, not the guarantee."""
    cfg = load_config(config)
    out = text
    if cfg["check_urls"]:
        out = URL_RE.sub(_PLACEHOLDER["url"], out)
    if cfg["check_emails"]:
        out = EMAIL_RE.sub(_PLACEHOLDER["email"], out)
    if cfg["check_paths"]:
        out = PATH_RE.sub(_PLACEHOLDER["path"], out)
    for tok in cfg["tokens"]:
        if tok:
            out = re.sub(re.escape(tok), _PLACEHOLDER["token"], out, flags=re.IGNORECASE)
    for name in cfg["codenames"]:
        if name:
            out = re.sub(r"\b" + re.escape(name) + r"\b", _PLACEHOLDER["codename"], out, flags=re.IGNORECASE)
    return out, find_client_data(text, cfg)


def codenames_from_names(names):
    """Helper: keep only distinctive identifiers (uppercase / digit / underscore) from a list of
    names, dropping generic lowercase words that would over-hold plain English."""
    return [n for n in names if re.search(r"[A-Z]|\d|_", n or "")]


if __name__ == "__main__":
    import sys
    cfg = load_config(sys.argv[1] if len(sys.argv) > 1 else None)
    hits = find_client_data(sys.stdin.read(), cfg)
    print("CLEAN" if not hits else "HELD: " + ", ".join(f"{c}:{v}" for c, v in hits))
    sys.exit(0 if not hits else 1)
