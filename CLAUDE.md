# Output Shrinking

Prefer these wrappers over raw tools. All output: `{status, totals, failures[]|errors[]}`.
Run with `uv run <wrapper>` from this directory. Pass extra flags after `--`.

## Wrappers

| Tool              | Wrapper                              | Key output fields                              |
|-------------------|--------------------------------------|------------------------------------------------|
| pytest            | `shk-pytest.py <file>`               | status, totals.tests, failures[]               |
| jest              | `shk-jest.py <args>`                 | status, totals.{tests,failed}, failures[]      |
| eslint            | `shk-eslint.py <files>`              | status, totals.{errors,warnings}, failures[]   |
| tsc               | `shk-tsc.py [args]`                  | status, totals.errors, failures[]              |
| docker build      | `shk-docker.py -- <args>`            | status, image_id, steps.{cached,run}           |
| git log           | `shk-git-log.py [-n 20]`             | branch, commits[{hash,subject,files}]          |
| npm               | `shk-npm.py install|ci`              | status, totals.{added,removed}, warnings[]     |
| curl              | `shk-curl.py <url> [args]`           | status, http_status, body|body_preview         |
| xcodebuild        | `shk-xcodebuild.py -- <args>`        | status, action, totals, failures[], errors[]   |
| swiftlint         | `shk-swiftlint.py [args]`            | status, totals.{errors,warnings}, failures[]   |
| ionic build       | `shk-ionic-build.py -- <args>`       | status, bundle{}, totals, errors[]             |
| ionic cap sync    | `shk-ionic-sync.py [ios|android]`    | status, platforms[], totals.copied_files       |

## Rules

1. **Never run the raw tool** when a shrinker exists for it.
2. Pass extra flags after `--` if needed.
3. On `status: error`, check the `message` field — the tool itself failed to run.
4. `xcodebuild` handles both `build` and `test` actions — action is auto-detected from args.

## Detecting Shrink Opportunities

After running any CLI tool NOT in the table above, count the output lines.
If raw output > 50 lines AND actionable content < 20% of that:
1. Flag it: "This output is a shrink candidate (~N lines, ~X% signal)"
2. Propose a wrapper following the same contract: `{status, totals, failures[]|errors[]}`
3. Write it to this directory as `shk-<tool>.py`
4. Add a row to the table above in this CLAUDE.md
5. Wait for validation before using it in future runs