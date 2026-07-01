#!/usr/bin/env python3
"""Tests for the auto-learn loop (no LLM spend — distillations injected). Run: python3 test_distill.py."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

DISTILL = str(Path(__file__).with_name("distill.py"))
T = Path(tempfile.mkdtemp())
src = T / "sources"; src.mkdir()
out, held, ledger = T / "out", T / "held", T / "ledger.json"

# two source notes; one distills clean, one carries a client path (must scrub then publish)
n1 = src / "n1.md"; n1.write_text("note one, some incident\n")
n2 = src / "n2.md"; n2.write_text("note two, other incident\n")
def h(p): return hashlib.sha1(p.read_text().encode()).hexdigest()[:16]
distilled = {
    h(n1): {"title": "Guard shared mutations", "body": "Route every mutation through one writer."},
    h(n2): {"title": "Snapshot before delete", "body": "Snapshot files at /Users/x/y before a destructive sync."},
}
(T / "distilled.json").write_text(json.dumps(distilled))

def run(extra):
    cmd = ["python3", DISTILL, "--sources", str(src), "--out", str(out), "--held", str(held),
           "--ledger", str(ledger), "--distilled-file", str(T / "distilled.json")] + extra
    return json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)

fails = []
def check(n, c): print(f"  {'PASS' if c else 'FAIL'} {n}"); (fails.append(n) if not c else None)

r1 = run(["--test-verify", "clean"])
check("2 published", len(r1["published"]) == 2)
check("2 files written", len(list(out.glob("*.md"))) == 2)
blob = "".join(p.read_text() for p in out.glob("*.md"))
check("client path scrubbed", "/Users/" not in blob and "[PATH]" in blob)

r2 = run(["--test-verify", "clean"])
check("idempotent (0 published on rerun)", r2["published"] == [])

# semantic HELD path: new note, verify=held -> held, not published
n3 = src / "n3.md"; n3.write_text("note three\n")
d = json.loads((T / "distilled.json").read_text())
d[h(n3)] = {"title": "Third", "body": "generic body."}
(T / "distilled.json").write_text(json.dumps(d))
before = len(list(out.glob("*.md")))
r3 = run(["--test-verify", "held"])
check("held not published", len(list(out.glob("*.md"))) == before)
check("held written to held dir", any(held.glob("held-*.md")))
check("summary reports 1 held", len(r3["held"]) == 1)

print("ALL PASS" if not fails else f"SOME FAILED: {fails}")
sys.exit(1 if fails else 0)
