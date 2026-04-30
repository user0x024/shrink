#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
shk-git-log — compact JSON summary for git log.
Usage: uv run shk-git-log.py [-- git log args]
Output: { branch, total_commits, commits: [{hash, date, author, subject, files_changed}] }

Defaults: last 20 commits, current branch.
"""
import argparse
import json
import subprocess
import sys

SEP = "\x1f"
FMT = SEP.join(["%h", "%aI", "%an", "%s"])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run git log and emit a compact JSON summary.")
    parser.add_argument("-n", "--count", type=int, default=20, help="Number of commits (default: 20)")
    parser.add_argument("git_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    git_args = args.git_args
    if git_args and git_args[0] == "--":
        git_args = git_args[1:]

    # Get current branch
    branch_result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True,
    )
    branch = branch_result.stdout.strip() or "unknown"

    # Get log
    log_result = subprocess.run(
        ["git", "log", f"-{args.count}", f"--pretty=format:{FMT}", "--stat", *git_args],
        capture_output=True, text=True,
    )

    if log_result.returncode != 0:
        print(json.dumps({
            "status": "error",
            "message": log_result.stderr.strip(),
        }), file=sys.__stdout__)
        return log_result.returncode

    commits = []
    # --stat adds blank lines + a summary line after each commit block
    # Split blocks by double-newline
    blocks = log_result.stdout.split("\n\n")
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue
        # First line is our SEP-formatted header
        parts = lines[0].split(SEP)
        if len(parts) < 4:
            continue
        # Last line of stat block: "N files changed, X insertions(+), Y deletions(-)"
        files_changed = 0
        for line in reversed(lines[1:]):
            if "file" in line and "changed" in line:
                try:
                    files_changed = int(line.strip().split()[0])
                except (ValueError, IndexError):
                    pass
                break
        commits.append({
            "hash": parts[0],
            "date": parts[1],
            "author": parts[2],
            "subject": parts[3],
            "files_changed": files_changed,
        })

    payload = {
        "branch": branch,
        "total_shown": len(commits),
        "commits": commits,
    }

    print(json.dumps(payload, ensure_ascii=True), file=sys.__stdout__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))