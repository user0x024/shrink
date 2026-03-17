#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///
import argparse
import io
import json
import re
import sys
import time
from contextlib import redirect_stderr, redirect_stdout

import pytest


def _extract_assertion(longreprtext: str) -> str:
    if not longreprtext:
        return ""
    for line in longreprtext.splitlines():
        m = re.search(r"assert .+", line)
        if m:
            return m.group(0).strip()
    return ""


def _extract_expected_actual(longreprtext: str, assertion: str) -> tuple[str, str]:
    expected = ""
    actual = ""

    if longreprtext:
        for line in longreprtext.splitlines():
            s = line.strip()
            if s.startswith("- "):
                expected = s[2:].strip()
            elif s.startswith("+ "):
                actual = s[2:].strip()

    if (not expected or not actual) and assertion:
        m = re.search(r"assert\s+(.+?)\s*==\s*(.+)$", assertion)
        if m:
            actual = actual or m.group(1).strip()
            expected = expected or m.group(2).strip()

    return actual, expected


class JsonSummaryPlugin:
    def __init__(self) -> None:
        self.start_time = None
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures = []
        self._skipped_ids = set()
        self._total_ids = set()

    def pytest_sessionstart(self, session):
        self.start_time = time.time()

    def pytest_runtest_logreport(self, report):
        nodeid = report.nodeid

        if report.when == "call":
            self._total_ids.add(nodeid)
            if report.outcome == "passed":
                self.passed += 1
            elif report.outcome == "failed":
                self.failed += 1
                self.failures.append(self._failure_from_report(report))
            elif report.outcome == "skipped":
                if nodeid not in self._skipped_ids:
                    self._skipped_ids.add(nodeid)
                    self.skipped += 1
        elif report.outcome == "skipped":
            # Skips can occur in setup; count once per test.
            if nodeid not in self._skipped_ids:
                self._skipped_ids.add(nodeid)
                self.skipped += 1
                self._total_ids.add(nodeid)

    def pytest_sessionfinish(self, session, exitstatus):
        duration_s = 0.0
        if self.start_time is not None:
            duration_s = time.time() - self.start_time

        if self.failed == 0:
            totals = {
                "tests": len(self._total_ids),
                "duration_s": round(duration_s, 2),
            }
            payload = {
                "status": "pass",
                "totals": totals,
            }
        else:
            totals = {
                "tests": len(self._total_ids),
                "failed": self.failed,
                "duration_s": round(duration_s, 2),
            }

            if self.skipped > 0:
                totals["skipped"] = self.skipped

            payload = {
                "status": "fail",
                "totals": totals,
                "failures": self.failures,
            }

        # Use the original stdout so we still emit JSON even when pytest output is silenced.
        print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)

    def _failure_from_report(self, report):
        longreprtext = getattr(report, "longreprtext", "") or ""
        assertion = _extract_assertion(longreprtext)

        if not assertion and hasattr(report.longrepr, "reprcrash"):
            msg = getattr(report.longrepr.reprcrash, "message", "")
            assertion = msg or ""

        actual, expected = _extract_expected_actual(longreprtext, assertion)

        file_path, line_no, _ = report.location
        # pytest location line numbers are 0-based internally.
        line_no = int(line_no) + 1

        return {
            "test": report.nodeid,
            "file": file_path,
            "line": line_no,
            "assertion": assertion,
            "actual": actual,
            "expected": expected,
        }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run pytest and emit a compact JSON summary.")
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed through to pytest. Use -- to separate.",
    )
    args = parser.parse_args(argv)

    pytest_args = args.pytest_args
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]

    plugin = JsonSummaryPlugin()

    # Suppress pytest's own terminal output; we only emit JSON.
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        exit_code = pytest.main(["-q", "--disable-warnings", *pytest_args], plugins=[plugin])

    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
