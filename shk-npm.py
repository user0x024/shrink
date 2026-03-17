#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
shk-npm — compact JSON summary for npm install/ci.
Usage: uv run shk-npm.py [install|ci|...] [npm args]
Output: { status, totals: {added, removed, changed, audited, duration_s}, warnings[], errors[] }
"""
import argparse
import json
import re
import subprocess
import sys
import time

_ADDED_RE = re.compile(r"added (\d+)")
_REMOVED_RE = re.compile(r"removed (\d+)")
_CHANGED_RE = re.compile(r"changed (\d+)")
_AUDITED_RE = re.compile(r"audited (\d+)")
_WARN_RE = re.compile(r"^npm warn (.+)", re.IGNORECASE)
_ERR_RE = re.compile(r"^npm error (.+)", re.IGNORECASE)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run npm and emit a compact JSON summary.")
    parser.add_argument("npm_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    npm_args = args.npm_args
    if npm_args and npm_args[0] == "--":
        npm_args = npm_args[1:]

    start = time.time()
    result = subprocess.run(
        ["npm", *npm_args],
        capture_output=True,
        text=True,
    )
    duration_s = round(time.time() - start, 2)

    output = result.stdout + result.stderr

    added = removed = changed = audited = 0
    warnings = []
    errors = []

    for line in output.splitlines():
        s = line.strip()
        m = _ADDED_RE.search(s)
        if m:
            added = int(m.group(1))
        m = _REMOVED_RE.search(s)
        if m:
            removed = int(m.group(1))
        m = _CHANGED_RE.search(s)
        if m:
            changed = int(m.group(1))
        m = _AUDITED_RE.search(s)
        if m:
            audited = int(m.group(1))
        m = _WARN_RE.match(s)
        if m:
            msg = m.group(1).strip()
            if msg and msg not in warnings:
                warnings.append(msg)
        m = _ERR_RE.match(s)
        if m:
            msg = m.group(1).strip()
            if msg and msg not in errors:
                errors.append(msg)

    totals = {
        "added": added,
        "removed": removed,
        "changed": changed,
        "audited": audited,
        "duration_s": duration_s,
    }

    if result.returncode == 0:
        payload = {"status": "pass", "totals": totals}
        if warnings:
            payload["warnings"] = warnings
    else:
        payload = {
            "status": "fail",
            "totals": totals,
            "errors": errors or ["unknown error"],
        }
        if warnings:
            payload["warnings"] = warnings

    print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))