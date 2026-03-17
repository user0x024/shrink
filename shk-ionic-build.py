#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
shk-ionic-build — compact JSON summary for ionic build output.
Usage: uv run shk-ionic-build.py [-- ionic build args]
Output: { status, totals: {errors, warnings, duration_s}, bundle{}, errors[], warnings[] }
"""
import argparse
import json
import re
import subprocess
import sys
import time

# Webpack/Rollup patterns
_ERROR_RE = re.compile(r"^(?:ERROR|Error)[\s:]+(.+)$")
_WARNING_RE = re.compile(r"^(?:WARNING|Warning)[\s:]+(.+)$")
_NG_ERROR_RE = re.compile(r"✖|×|error TS\d+|Cannot find|Module not found", re.IGNORECASE)
_NG_WARNING_RE = re.compile(r"Warning: .+|DeprecationWarning", re.IGNORECASE)

# Bundle size lines: e.g. "chunk (runtime) main.js (main) 1.23 MB"
_CHUNK_RE = re.compile(r"chunk.+?(\S+\.js).+?([\d.]+)\s*(kB|MB|B)\b", re.IGNORECASE)
# Angular build success
_SUCCESS_RE = re.compile(r"Build at:.+|✔ Browser application bundle generation complete|build finished", re.IGNORECASE)
_FAIL_RE = re.compile(r"Build failed|✖ Failed to compile|ionic build failed", re.IGNORECASE)


def _normalise_size_kb(value: float, unit: str) -> float:
    unit = unit.upper()
    if unit == "MB":
        return round(value * 1024, 1)
    if unit == "B":
        return round(value / 1024, 2)
    return round(value, 1)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run ionic build and emit a compact JSON summary.")
    parser.add_argument("ionic_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    ionic_args = args.ionic_args
    if ionic_args and ionic_args[0] == "--":
        ionic_args = ionic_args[1:]

    start = time.time()
    result = subprocess.run(
        ["ionic", "build", *ionic_args],
        capture_output=True,
        text=True,
    )
    duration_s = round(time.time() - start, 2)

    output = result.stdout + result.stderr
    errors = []
    warnings = []
    chunks = {}
    build_succeeded = False
    build_failed = False

    for line in output.splitlines():
        s = line.strip()
        if not s:
            continue

        if _SUCCESS_RE.search(s):
            build_succeeded = True
        if _FAIL_RE.search(s):
            build_failed = True

        m = _CHUNK_RE.search(s)
        if m:
            chunks[m.group(1)] = {"size_kb": _normalise_size_kb(float(m.group(2)), m.group(3))}
            continue

        m = _ERROR_RE.match(s)
        if m or _NG_ERROR_RE.search(s):
            msg = m.group(1) if m else s
            if msg not in errors:
                errors.append(msg)
            continue

        m = _WARNING_RE.match(s)
        if m or _NG_WARNING_RE.search(s):
            msg = m.group(1) if m else s
            if msg not in warnings:
                warnings.append(msg)

    succeeded = (build_succeeded or result.returncode == 0) and not build_failed and not errors

    totals = {
        "errors": len(errors),
        "warnings": len(warnings),
        "duration_s": duration_s,
    }

    payload = {
        "status": "pass" if succeeded else "fail",
        "totals": totals,
    }

    if chunks:
        payload["bundle"] = chunks

    if errors:
        payload["errors"] = errors
    if warnings:
        payload["warnings"] = warnings[:5]  # cap, Angular can emit many deprecations

    print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))