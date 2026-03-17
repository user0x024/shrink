#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
shk-jest — compact JSON summary for Jest output.
Usage: uv run shk-jest.py [jest args]
Output: { status, totals: {suites, tests, failed, duration_s}, failures[] }
"""
import argparse
import json
import subprocess
import sys
import tempfile
import os
import time


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run Jest and emit a compact JSON summary.")
    parser.add_argument("jest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    jest_args = args.jest_args
    if jest_args and jest_args[0] == "--":
        jest_args = jest_args[1:]

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        json_out = f.name

    start = time.time()
    result = subprocess.run(
        ["jest", "--json", f"--outputFile={json_out}", "--silent", *jest_args],
        capture_output=True,
        text=True,
    )
    duration_s = round(time.time() - start, 2)

    try:
        with open(json_out) as f:
            raw = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(json.dumps({
            "status": "error",
            "message": result.stderr.strip() or "jest produced no output",
        }), file=sys.__stdout__)
        return result.returncode
    finally:
        os.unlink(json_out)

    failures = []
    for suite in raw.get("testResults", []):
        for test in suite.get("testResults", []):
            if test["status"] != "failed":
                continue
            failures.append({
                "suite": suite["testFilePath"],
                "test": test["fullName"],
                "message": "\n".join(test.get("failureMessages", [])),
            })

    totals = {
        "suites": raw.get("numTotalTestSuites", 0),
        "tests": raw.get("numTotalTests", 0),
        "failed": raw.get("numFailedTests", 0),
        "duration_s": duration_s,
    }

    if raw.get("success"):
        payload = {"status": "pass", "totals": totals}
    else:
        payload = {"status": "fail", "totals": totals, "failures": failures}

    print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))