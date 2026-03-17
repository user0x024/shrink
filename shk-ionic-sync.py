#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
shk-ionic-sync — compact JSON summary for ionic cap sync / capacitor sync.
Usage: uv run shk-ionic-sync.py [ios|android] [-- args]
Output: { status, platforms[], totals: {copied, duration_s}, errors[] }
"""
import argparse
import json
import re
import subprocess
import sys
import time

_COPIED_RE = re.compile(r"Copying web assets.+?(\d+) file", re.IGNORECASE)
_PLATFORM_RE = re.compile(r"(?:Syncing|✔ Updating)\s+(iOS|Android|ios|android)", re.IGNORECASE)
_PLUGIN_RE = re.compile(r"(?:✔|✓)\s+(.+?)\s+(?:added|updated|installed)", re.IGNORECASE)
_ERROR_RE = re.compile(r"(?:✖|✗|ERROR|error:)\s+(.+)", re.IGNORECASE)
_SUCCESS_RE = re.compile(r"Sync finished|✔ Sync complete", re.IGNORECASE)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run ionic cap sync and emit a compact JSON summary.")
    parser.add_argument("sync_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    sync_args = args.sync_args
    if sync_args and sync_args[0] == "--":
        sync_args = sync_args[1:]

    start = time.time()
    result = subprocess.run(
        ["ionic", "cap", "sync", *sync_args],
        capture_output=True,
        text=True,
    )
    duration_s = round(time.time() - start, 2)

    output = result.stdout + result.stderr
    platforms = []
    plugins = []
    copied = 0
    errors = []
    succeeded = False

    for line in output.splitlines():
        s = line.strip()
        if not s:
            continue

        if _SUCCESS_RE.search(s):
            succeeded = True

        m = _COPIED_RE.search(s)
        if m:
            copied = max(copied, int(m.group(1)))

        m = _PLATFORM_RE.search(s)
        if m:
            p = m.group(1).lower()
            if p not in platforms:
                platforms.append(p)

        m = _PLUGIN_RE.search(s)
        if m:
            name = m.group(1).strip()
            if name not in plugins:
                plugins.append(name)

        m = _ERROR_RE.search(s)
        if m:
            msg = m.group(1).strip()
            if msg and msg not in errors:
                errors.append(msg)

    succeeded = succeeded or (result.returncode == 0 and not errors)

    totals = {
        "copied_files": copied,
        "plugins_synced": len(plugins),
        "duration_s": duration_s,
    }

    payload = {
        "status": "pass" if succeeded else "fail",
        "platforms": platforms,
        "totals": totals,
    }

    if errors:
        payload["errors"] = errors

    print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))