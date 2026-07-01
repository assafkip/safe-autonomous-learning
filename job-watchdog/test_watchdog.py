#!/usr/bin/env python3
"""Tests for the watchdog's pure logic (the wait-status decoder). Run: python3 test_watchdog.py."""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("wd", Path(__file__).with_name("watchdog.py"))
wd = importlib.util.module_from_spec(spec); spec.loader.exec_module(wd)

fails = []
def check(raw, want):
    got = wd.normalize_exit(raw)
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'} normalize_exit({raw}) = {got} (want {want})")
    if not ok: fails.append(raw)

check(0, 0)          # clean
check(768, 3)        # exit 3 wait-encoded (3<<8)
check(32512, 127)    # exit 127 wait-encoded (command not found — the classic)
check(256, 1)        # exit 1
check(3, 3)          # small value passthrough
check(127, 127)      # small value passthrough
check(15, 15)        # signal-range passthrough (<256)

print("ALL PASS" if not fails else f"SOME FAILED: {fails}")
sys.exit(1 if fails else 0)
