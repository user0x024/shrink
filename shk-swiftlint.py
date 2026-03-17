#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
shk-swiftlint — compact JSON summary for SwiftLint output.
Usage: uv run shk-swiftlint.py [-- swiftlint args]
Output: { status, totals: {errors, warnings, files, duration_s}, failures[] }
"""
import argparse
import json
import subprocess
import sys
import time


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run SwiftLint and emit a compact JSON summary.")
    parser.add_argument("swiftlint_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    swiftlint_args = args.swiftlint_args
    if swiftlint_args and swiftlint_args[0] == "--":
        swiftlint_args = swiftlint_args[1:]

    start = time.time()
    result = subprocess.run(
        ["swiftlint", "--reporter", "json", *swiftlint_args],
        capture_output=True,
        text=True,
    )
    duration_s = round(time.time() - start, 2)

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(json.dumps({
            "status": "error",
            "message": result.stderr.strip() or result.stdout.strip(),
        }), file=sys.__stdout__)
        return result.returncode

    errors = [v for v in raw if v.get("severity") == "Error"]
    warnings = [v for v in raw if v.get("severity") == "Warning"]
    files = len({v["file"] for v in raw if "file" in v})

    failures = [
        {
            "file": v.get("file", ""),
            "line": v.get("line", 0),
            "col": v.get("character", 0),
            "severity": v.get("severity", "").lower(),
            "rule": v.get("rule_id", ""),
            "message": v.get("reason", ""),
        }
        for v in raw
        if v.get("severity") == "Error"  # only errors in failures; warnings in totals only
    ]

    totals = {
        "errors": len(errors),
        "warnings": len(warnings),
        "files": files,
        "duration_s": duration_s,
    }

    if len(errors) == 0 and len(warnings) == 0:
        payload = {"status": "pass", "totals": totals}
    elif len(errors) == 0:
        payload = {"status": "warn", "totals": totals}
    else:
        payload = {"status": "fail", "totals": totals, "failures": failures}

    print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))