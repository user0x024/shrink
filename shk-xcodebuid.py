#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
shk-xcodebuild — compact JSON summary for xcodebuild, via xcbeautify JUnit report.
Requires: brew install xcbeautify

Usage:
  uv run shk-xcodebuild.py -- [xcodebuild args]

Examples:
  uv run shk-xcodebuild.py -- -scheme MyApp -destination 'platform=iOS Simulator,name=iPhone 16' build
  uv run shk-xcodebuild.py -- -scheme MyApp -destination 'platform=iOS Simulator,name=iPhone 16' test

Output:
  Build: { status, action, totals: {errors, warnings, duration_s}, errors[], warnings[] }
  Test:  { status, action, totals: {tests, passed, failed, skipped, duration_s}, failures[] }

Notes:
  - JUnit XML is written to a temp dir and cleaned up after parsing.
  - xcbeautify human-readable output is suppressed; only JSON goes to stdout.
  - Exit code mirrors xcodebuild's exit code.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET


# Fallback regex for build action (JUnit only covers test results)
_ERROR_RE = re.compile(r"^(.+?):(\d+)(?::(\d+))?:\s+error:\s+(.+)$")
_WARNING_RE = re.compile(r"^(.+?):(\d+)(?::(\d+))?:\s+warning:\s+(.+)$")
_BUILD_SUCCEEDED_RE = re.compile(r"\*\*\s*BUILD SUCCEEDED\s*\*\*")
_BUILD_FAILED_RE = re.compile(r"\*\*\s*BUILD FAILED\s*\*\*")


def _detect_action(args: list[str]) -> str:
    for i, a in enumerate(args):
        if a == "test":
            return "test"
        if a == "build":
            return "build"
        if a == "-action" and i + 1 < len(args):
            return args[i + 1]
    return "build"


def _parse_junit(report_dir: str) -> dict:
    """Parse xcbeautify's JUnit XML into a clean dict."""
    junit_path = os.path.join(report_dir, "junit.xml")
    if not os.path.exists(junit_path):
        return {"found": False}

    tree = ET.parse(junit_path)
    root = tree.getroot()

    total = failed = skipped = 0
    failures = []

    for suite in root.iter("testsuite"):
        for case in suite.iter("testcase"):
            total += 1
            failure_el = case.find("failure")
            skipped_el = case.find("skipped")
            if skipped_el is not None:
                skipped += 1
            elif failure_el is not None:
                failed += 1
                failures.append({
                    "suite": suite.get("name", ""),
                    "test": case.get("name", ""),
                    "duration_s": float(case.get("time", 0)),
                    "message": failure_el.get("message", ""),
                    "detail": (failure_el.text or "").strip(),
                })

    return {
        "found": True,
        "total": total,
        "failed": failed,
        "skipped": skipped,
        "passed": total - failed - skipped,
        "failures": failures,
    }


def _parse_build_output(output: str) -> dict:
    """Parse raw output for build action — no JUnit available for builds."""
    errors = []
    warnings = []
    succeeded = False
    seen_e: set = set()
    seen_w: set = set()

    for line in output.splitlines():
        s = line.strip()
        if _BUILD_SUCCEEDED_RE.search(s):
            succeeded = True
        if _BUILD_FAILED_RE.search(s):
            succeeded = False

        m = _ERROR_RE.match(s)
        if m:
            key = (m.group(1), m.group(2), m.group(4))
            if key not in seen_e:
                seen_e.add(key)
                errors.append({
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "col": int(m.group(3) or 0),
                    "message": m.group(4),
                })
            continue

        m = _WARNING_RE.match(s)
        if m:
            key = (m.group(1), m.group(2), m.group(4))
            if key not in seen_w:
                seen_w.add(key)
                warnings.append({
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "col": int(m.group(3) or 0),
                    "message": m.group(4),
                })

    return {"succeeded": succeeded, "errors": errors, "warnings": warnings[:10]}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Run xcodebuild via xcbeautify and emit a compact JSON summary."
    )
    parser.add_argument("xcode_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    xcode_args = args.xcode_args
    if xcode_args and xcode_args[0] == "--":
        xcode_args = xcode_args[1:]

    if not shutil.which("xcbeautify"):
        print(json.dumps({
            "status": "error",
            "message": "xcbeautify not found. Install with: brew install xcbeautify",
        }), file=sys.__stdout__)
        return 1

    action = _detect_action(xcode_args)
    report_dir = tempfile.mkdtemp(prefix="shk-xcodebuild-")

    try:
        start = time.time()

        # NSUnbufferedIO=YES: prevents parallel test output being lost in pipe buffer
        # set -o pipefail: ensures xcodebuild exit code is preserved through the pipe
        # Shell-quote args that contain spaces (e.g. -destination values)
        quoted = [f"'{a}'" if " " in a else a for a in xcode_args]
        xcb_cmd = (
            f"NSUnbufferedIO=YES xcodebuild {' '.join(quoted)} 2>&1 "
            f"| xcbeautify --disable-colored-output --report junit --report-path {report_dir}"
        )

        result = subprocess.run(
            ["bash", "-o", "pipefail", "-c", xcb_cmd],
            capture_output=True,
            text=True,
        )
        duration_s = round(time.time() - start, 2)
        raw_output = result.stdout + result.stderr

        if action == "test":
            junit = _parse_junit(report_dir)
            if not junit["found"]:
                # Build failed before any tests ran
                build = _parse_build_output(raw_output)
                payload = {
                    "status": "fail",
                    "action": "test",
                    "totals": {"errors": len(build["errors"]), "duration_s": duration_s},
                    "errors": build["errors"] or [{"message": "Build failed before tests ran"}],
                }
            else:
                payload = {
                    "status": "pass" if junit["failed"] == 0 and result.returncode == 0 else "fail",
                    "action": "test",
                    "totals": {
                        "tests": junit["total"],
                        "passed": junit["passed"],
                        "failed": junit["failed"],
                        "skipped": junit["skipped"],
                        "duration_s": duration_s,
                    },
                }
                if junit["failures"]:
                    payload["failures"] = junit["failures"]
        else:
            build = _parse_build_output(raw_output)
            succeeded = build["succeeded"] or (result.returncode == 0 and not build["errors"])
            payload = {
                "status": "pass" if succeeded else "fail",
                "action": "build",
                "totals": {
                    "errors": len(build["errors"]),
                    "warnings": len(build["warnings"]),
                    "duration_s": duration_s,
                },
            }
            if build["errors"]:
                payload["errors"] = build["errors"]
            if build["warnings"]:
                payload["warnings"] = build["warnings"]

    finally:
        shutil.rmtree(report_dir, ignore_errors=True)

    print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))