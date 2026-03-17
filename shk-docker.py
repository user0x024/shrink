#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
shk-docker — compact JSON summary for docker build output.
Usage: uv run shk-docker.py [docker build args]
Output: { status, image_id, steps: {total, cached, run}, duration_s, errors[] }
"""
import argparse
import json
import re
import subprocess
import sys
import time

_STEP_RE = re.compile(r"^Step\s+(\d+)/(\d+)\s+:", re.IGNORECASE)
_CACHED_RE = re.compile(r"---> Using cache", re.IGNORECASE)
_IMAGE_RE = re.compile(r"Successfully built ([a-f0-9]+)")
_TAGGED_RE = re.compile(r"Successfully tagged (.+)")
_ERROR_RE = re.compile(r"^(error|failed to|cannot|could not).+", re.IGNORECASE)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run docker build and emit a compact JSON summary.")
    parser.add_argument("docker_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    docker_args = args.docker_args
    if docker_args and docker_args[0] == "--":
        docker_args = docker_args[1:]

    start = time.time()
    result = subprocess.run(
        ["docker", "build", *docker_args],
        capture_output=True,
        text=True,
    )
    duration_s = round(time.time() - start, 2)

    output = result.stdout + result.stderr

    total_steps = 0
    cached = 0
    run = 0
    image_id = None
    tagged = None
    errors = []
    last_was_step = False

    for line in output.splitlines():
        s = line.strip()
        m = _STEP_RE.match(s)
        if m:
            total_steps = max(total_steps, int(m.group(2)))
            last_was_step = True
            continue
        if last_was_step and _CACHED_RE.search(s):
            cached += 1
            last_was_step = False
            continue
        if last_was_step:
            run += 1
            last_was_step = False

        m = _IMAGE_RE.search(s)
        if m:
            image_id = m.group(1)
        m = _TAGGED_RE.search(s)
        if m:
            tagged = m.group(1)

        if result.returncode != 0 and _ERROR_RE.match(s):
            errors.append(s)

    totals = {
        "steps": {"total": total_steps, "cached": cached, "run": run},
        "duration_s": duration_s,
    }

    if result.returncode == 0:
        payload = {
            "status": "pass",
            "image_id": image_id,
            "tagged": tagged,
            "totals": totals,
        }
    else:
        payload = {
            "status": "fail",
            "totals": totals,
            "errors": errors or [output.splitlines()[-1]] if output else ["unknown error"],
        }

    print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))