#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
shk-curl — compact JSON summary for curl requests.
Usage: uv run shk-curl.py <url> [curl args]
Output: { status, http_status, duration_s, content_type, body_preview, error? }

body_preview is truncated to 500 chars. If response is JSON, it's included parsed.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import os

PREVIEW_CHARS = 500


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run curl and emit a compact JSON summary.")
    parser.add_argument("curl_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    curl_args = args.curl_args
    if curl_args and curl_args[0] == "--":
        curl_args = curl_args[1:]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".body") as f:
        body_file = f.name

    try:
        result = subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--write-out", "%{http_code}\t%{content_type}\t%{time_total}",
                "--output", body_file,
                *curl_args,
            ],
            capture_output=True,
            text=True,
        )

        # Last line of stdout is our write-out metrics
        metrics_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        parts = metrics_line.split("\t")

        http_status = int(parts[0]) if parts and parts[0].isdigit() else 0
        content_type = parts[1].split(";")[0].strip() if len(parts) > 1 else ""
        duration_s = round(float(parts[2]), 3) if len(parts) > 2 else 0.0

        with open(body_file, "r", errors="replace") as f:
            raw_body = f.read()

    finally:
        os.unlink(body_file)

    if result.returncode != 0:
        print(json.dumps({
            "status": "error",
            "error": result.stderr.strip(),
            "duration_s": duration_s,
        }), file=sys.__stdout__)
        return result.returncode

    # Try to parse as JSON for a cleaner preview
    body_json = None
    if "json" in content_type:
        try:
            body_json = json.loads(raw_body)
        except json.JSONDecodeError:
            pass

    ok = 200 <= http_status < 300

    payload = {
        "status": "pass" if ok else "fail",
        "http_status": http_status,
        "content_type": content_type,
        "duration_s": duration_s,
    }

    if body_json is not None:
        # For JSON responses: include full parsed body (Claude can read it directly)
        payload["body"] = body_json
    else:
        # For non-JSON: truncate
        preview = raw_body[:PREVIEW_CHARS]
        if len(raw_body) > PREVIEW_CHARS:
            preview += f"… [{len(raw_body) - PREVIEW_CHARS} chars truncated]"
        payload["body_preview"] = preview

    print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))