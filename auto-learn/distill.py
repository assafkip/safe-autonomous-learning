#!/usr/bin/env python3
"""auto-learn: distill notes into shareable lessons, behind the client-data gate.

The loop (the thing that makes a knowledge base compound instead of sit still):
  read new source notes -> DISTILL each into a generic HOW-only lesson via an LLM ->
  GATE it (deterministic client-data-gate + an optional LLM semantic pass) ->
  PUBLISH the clean ones; HOLD anything the gate can't clear (surfaced, never leaked) ->
  LEDGER each source so it is processed once (idempotent).

This is the capture -> synthesize -> write-back loop, made safe for confidential work: publishing is
fail-closed. A clean lesson flows; a client-tainted one is held for a human, not shared.

LLM is pluggable (`--llm-cmd`, default `claude -p`); the message is appended as the final arg.
Test hooks: `--distilled-file` (inject distillations, skip the LLM), `--test-verify {real,clean,held}`.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_gate_path = Path(__file__).resolve().parents[1] / "client-data-gate" / "gate.py"
_spec = importlib.util.spec_from_file_location("gate", _gate_path)
gate = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(gate)


def new_sources(sources_dir, ledger):
    for p in sorted(Path(sources_dir).glob("*.md")):
        text = p.read_text(errors="ignore")
        h = hashlib.sha1(text.encode()).hexdigest()[:16]
        if h not in ledger:
            yield p, h, text


def run_llm(llm_cmd, prompt):
    try:
        r = subprocess.run(llm_cmd.split() + [prompt], capture_output=True, text=True, timeout=120)
        return r.stdout
    except Exception:
        return ""


def distill(llm_cmd, text):
    prompt = (
        "Turn the note below into a REUSABLE, HOW-ONLY lesson for people on unrelated projects. "
        "Output STRICT JSON {\"title\":..,\"body\":..}. RULES: net-new general restatement; NO "
        "client/product/person/company names, NO file paths, NO specifics that identify the source.\n\n"
        + text[:2000]
    )
    out = run_llm(llm_cmd, prompt)
    m = re.search(r"\{.*\}", out, re.S)
    try:
        obj = json.loads(m.group(0)) if m else None
    except Exception:
        obj = None
    return {"title": str(obj["title"]).strip(), "body": str(obj["body"]).strip()} if obj else None


def semantic_clean(llm_cmd, text, mode):
    if mode == "clean":
        return True
    if mode == "held":
        return False
    out = run_llm(llm_cmd, "Does the text contain ANY specific real client, product, person, company, "
                           "or identifying number/codename? Reply exactly CLEAN or HELD.\n\n" + text[:2000])
    return out.strip().upper().startswith("CLEAN")


def gate_lesson(title, body, cfg, llm_cmd, verify_mode):
    """Return (clean_text_or_None, held_reason_or_None). Fail-closed."""
    combined = f"{title}\n{body}"
    scrubbed, _ = gate.scrub(combined, cfg)
    if not gate.is_clean(scrubbed, cfg):
        return None, "deterministic gate could not clear all client-data signals"
    if not semantic_clean(llm_cmd, scrubbed, verify_mode):
        return None, "LLM semantic check flagged a residual real entity"
    return scrubbed, None


def slugify(t):
    return (re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60]) or "lesson"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--held", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--config", default=None)
    ap.add_argument("--llm-cmd", default="claude -p")
    ap.add_argument("--distilled-file", default=None)
    ap.add_argument("--test-verify", default="real", choices=["real", "clean", "held"])
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    cfg = gate.load_config(args.config)
    out_dir, held_dir, ledger_path = Path(args.out), Path(args.held), Path(args.ledger)
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    injected = json.loads(Path(args.distilled_file).read_text()) if args.distilled_file else None
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    used, published, held = set(), [], []

    for path, h, text in new_sources(args.sources, ledger):
        d = injected.get(h) if injected is not None else distill(args.llm_cmd, text)
        if not d:
            continue
        clean_text, reason = gate_lesson(d["title"], d["body"], cfg, args.llm_cmd, args.test_verify)
        if args.dry:
            (published if clean_text else held).append(d["title"]); continue
        if clean_text:
            out_dir.mkdir(parents=True, exist_ok=True)
            title = clean_text.split("\n", 1)[0].strip()
            body = clean_text.split("\n", 1)[1].strip() if "\n" in clean_text else ""
            lid = slugify(title); n = 2
            while lid in used or (out_dir / f"{lid}.md").exists():
                lid = f"{slugify(title)}-{n}"; n += 1
            used.add(lid)
            (out_dir / f"{lid}.md").write_text(f"# {title}\n\n_{stamp}_\n\n{body}\n")
            published.append(title)
        else:
            held_dir.mkdir(parents=True, exist_ok=True)
            (held_dir / f"held-{h}.md").write_text(
                f"# HELD (not published)\n\nreason: {reason}\nsource: {path}\n\n"
                f"title: {d['title']}\n\n{d['body']}\n")
            held.append(d["title"])
        ledger[h] = {"status": "published" if clean_text else "held", "date": stamp}

    if not args.dry:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(json.dumps(ledger, indent=2))
    print(json.dumps({"published": published, "held": held}, indent=2))


if __name__ == "__main__":
    main()
