#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
shk-eslint — compact JSON summary for ESLint output.
Usage: uv run shk-eslint.py [eslint args]
Output: { status, totals: {files, errors, warnings, duration_s}, failures[] }
"""
import argparse
import json
import subprocess
import sys
import time


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run ESLint and emit a compact JSON summary.")
    parser.add_argument("eslint_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    eslint_args = args.eslint_args
    if eslint_args and eslint_args[0] == "--":
        eslint_args = eslint_args[1:]

    start = time.time()
    result = subprocess.run(
        ["eslint", "--format", "json", *eslint_args],
        capture_output=True,
        text=True,
    )
    duration_s = round(time.time() - start, 2)

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError:
        # ESLint can emit non-JSON on fatal errors (missing config, etc.)
        print(json.dumps({
            "status": "error",
            "message": result.stderr.strip() or result.stdout.strip(),
        }), file=sys.__stdout__)
        return result.returncode

    total_errors = sum(f["errorCount"] for f in raw)
    total_warnings = sum(f["warningCount"] for f in raw)
    files_checked = len(raw)

    failures = []
    for file_result in raw:
        for msg in file_result["messages"]:
            if msg["severity"] == 0:
                continue  # skip suggestions
            failures.append({
                "file": file_result["filePath"],
                "line": msg.get("line", 0),
                "col": msg.get("column", 0),
                "severity": "error" if msg["severity"] == 2 else "warning",
                "rule": msg.get("ruleId") or "syntax",
                "message": msg["message"],
            })

    totals = {
        "files": files_checked,
        "errors": total_errors,
        "warnings": total_warnings,
        "duration_s": duration_s,
    }

    if total_errors == 0 and total_warnings == 0:
        payload = {"status": "pass", "totals": totals}
    else:
        payload = {
            "status": "fail" if total_errors > 0 else "warn",
            "totals": totals,
            "failures": failures,
        }

    print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))