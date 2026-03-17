#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
shk-tsc — compact JSON summary for TypeScript compiler output.
Usage: uv run shk-tsc.py [tsc args]
Output: { status, totals: {errors, duration_s}, failures[] }
"""
import argparse
import json
import re
import subprocess
import sys
import time

# TS error line: path/to/file.ts(line,col): error TS1234: message
_TS_RE = re.compile(r"^(.+?)\((\d+),(\d+)\):\s+(error|warning)\s+(TS\d+):\s+(.+)$")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run tsc and emit a compact JSON summary.")
    parser.add_argument("tsc_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    tsc_args = args.tsc_args
    if tsc_args and tsc_args[0] == "--":
        tsc_args = tsc_args[1:]

    start = time.time()
    result = subprocess.run(
        ["tsc", "--noEmit", *tsc_args],
        capture_output=True,
        text=True,
    )
    duration_s = round(time.time() - start, 2)

    failures = []
    for line in (result.stdout + result.stderr).splitlines():
        m = _TS_RE.match(line.strip())
        if m:
            failures.append({
                "file": m.group(1),
                "line": int(m.group(2)),
                "col": int(m.group(3)),
                "severity": m.group(4),
                "code": m.group(5),
                "message": m.group(6),
            })

    error_count = sum(1 for f in failures if f["severity"] == "error")
    totals = {"errors": error_count, "duration_s": duration_s}

    if error_count == 0:
        payload = {"status": "pass", "totals": totals}
    else:
        payload = {"status": "fail", "totals": totals, "failures": failures}

    print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))