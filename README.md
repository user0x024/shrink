# 🗜️ Shrink

**CLI output is noisy. Your AI agent doesn't need 200 lines to know a test failed.**

Shrink is a collection of lightweight Python wrappers that sit in front of common CLI tools and compress their output into a **compact, structured JSON summary**. Built for AI-assisted development workflows where every token counts.

## 📋 Prerequisites

- **Python 3.12+**
- **[uv](https://github.com/astral-sh/uv)** — handles per-script dependencies automatically, no virtualenv needed

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 🤔 Why?

When you use an AI coding assistant (like Claude Code), it reads tool output to decide what to do next. But most CLI tools were designed for humans scanning terminal screens — not for LLMs parsing context windows.

A typical `pytest` run dumps hundreds of lines. The useful signal? _3 fields._

```
❌ Raw pytest: ~150 lines
✅ Shrink:     {"status": "fail", "totals": {"tests": 42, "failed": 1}, "failures": [{"test": "test_auth", "line": 87, "assertion": "assert 401 == 200"}]}
```

**Less noise → fewer tokens → faster reasoning → lower cost.** 💸

## 🧠 Philosophy

1. **📉 Signal over noise** — Strip everything that isn't actionable. Keep only what matters: status, counts, and failure details.
2. **📦 One contract** — Every wrapper outputs the same shape: `{status, totals, failures[]|errors[]}`. Predictable structure means the consumer never has to guess.
3. **🔌 Drop-in replacement** — Same tool, same args, just prefixed with `shk-`. No workflow changes needed.
4. **🪶 Minimal setup** — Install [uv](https://github.com/astral-sh/uv), then run `uv run shk-<tool>.py`. No config files, no virtualenv to manage — `uv` handles per-script dependencies automatically.
5. **🌱 Grow organically** — See a noisy tool? Wrap it. Add a row to the table. The collection grows with your stack.

## 📦 Available Wrappers

| Tool | Wrapper | Key output fields |
|---|---|---|
| 🧪 pytest | `shk-pytest.py <file>` | status, totals.tests, failures[] |
| 🃏 jest | `shk-jest.py <args>` | status, totals.{tests,failed}, failures[] |
| 🔍 eslint | `shk-eslint.py <files>` | status, totals.{errors,warnings}, failures[] |
| 🏗️ tsc | `shk-tsc.py [args]` | status, totals.errors, failures[] |
| 🐳 docker build | `shk-docker.py -- <args>` | status, image_id, steps.{cached,run} |
| 📜 git log | `shk-git-log.py [-n 20]` | branch, commits[{hash,subject,files}] |
| 📦 npm | `shk-npm.py install\|ci` | status, totals.{added,removed}, warnings[] |
| 🌐 curl | `shk-curl.py <url> [args]` | status, http_status, body\|body_preview |
| 🍎 xcodebuild | `shk-xcodebuild.py -- <args>` | status, action, totals, failures[], errors[] |
| 🧹 swiftlint | `shk-swiftlint.py [args]` | status, totals.{errors,warnings}, failures[] |
| 📱 ionic build | `shk-ionic-build.py -- <args>` | status, bundle{}, totals, errors[] |
| 🔄 ionic cap sync | `shk-ionic-sync.py [ios\|android]` | status, platforms[], totals.copied_files |

## 🚀 Usage

```bash
# Instead of:
pytest tests/ -v          # 😵 200 lines of output

# Run:
uv run shk-pytest.py tests/   # 😎 1 line of JSON
```

Pass extra flags after `--`:

```bash
uv run shk-docker.py -- -t myapp:latest .
uv run shk-xcodebuild.py -- -scheme MyApp -sdk iphonesimulator build
```

## 📄 License

MIT
