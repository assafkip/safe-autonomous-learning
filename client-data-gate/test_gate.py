#!/usr/bin/env python3
"""Fail-closed tests for the client-data gate. Run: python3 test_gate.py (exit 0 = pass)."""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("gate", Path(__file__).with_name("gate.py"))
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

cfg = {"tokens": ["AcmeCorp"], "codenames": ["Falcon_2026"]}
fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'} {name}")
    if not cond: fails.append(name)

# every client-data class must fail is_clean (fail-closed)
check("configured token held",  not g.is_clean("The AcmeCorp incident taught us X", cfg))
check("codename held",          not g.is_clean("Falcon_2026 hit the wall", cfg))
check("absolute path held",     not g.is_clean("edit /Users/jane/proj/x.py", cfg))
check("generic path held",      not g.is_clean("the file /etc/app/config.json broke", cfg))
check("email held",             not g.is_clean("ping a.b@client.com about it", cfg))
check("url held",               not g.is_clean("see https://acme.com/secret", cfg))

# a real HOW-only lesson passes
clean = ("Route every mutation of a shared resource through one writer and add a test that greps "
         "the tree to prove no caller bypasses it.")
check("clean generic lesson passes", g.is_clean(clean, cfg))

# scrub then re-gate: scrubbing makes it clean
scrubbed, hits = g.scrub("contact a.b@client.com now", cfg)
check("scrub replaces + result clean", g.is_clean(scrubbed, cfg) and len(hits) == 1)

# codename helper keeps distinctive names, drops generic words
names = g.codenames_from_names(["accountant", "negotiator", "Falcon_2026", "CLIENT_A"])
check("helper keeps codenames", "Falcon_2026" in names and "CLIENT_A" in names)
check("helper drops generic",   "accountant" not in names and "negotiator" not in names)

# default config (no tokens) still catches structural signals
check("default config catches path", not g.is_clean("/var/secret/x", None))

print("ALL PASS" if not fails else f"SOME FAILED: {fails}")
sys.exit(1 if fails else 0)
