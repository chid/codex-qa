# Codex Q&A Logger

This folder stores your Codex questions and responses in an append-only JSONL log.

## What it does

- Logs one Q&A per user turn into `logs/qa.jsonl`
- Supports three capture modes:
  - `log-turn`: manual append
  - `wrap`: run a command template and auto-log output
  - `parse-transcript`: import Q&A pairs from transcript files
- Optional regex redaction with `--redact`
- Dedupe on `_dedupe_key = timestamp + normalized_question_hash + source_ref`

## Entry schema

Each line in `logs/qa.jsonl` is a JSON object:

- `timestamp`
- `cwd`
- `agent`
- `question`
- `response`
- `tags` (array)
- `source_mode` (`manual`, `wrapper`, `transcript`)
- `source_ref`
- `_dedupe_key`

## Usage

## Installation

Install in editable mode from this folder:

```bash
python3 -m pip install -e .
```

If your environment is offline or has older `pip` tooling, use:

```bash
python3 -m pip install -e . --no-use-pep517
```

Using `uv`:

```bash
./scripts/install_with_uv.sh
```

`pipx`-style install with `uv` (installs CLI onto your user tool path):

```bash
uv tool install .
uv tool update-shell
```

After restarting your shell, `qa-logger --help` should work without activating `.venv`.

## Usage

```bash
qa-logger log-turn \
  --question "purpose of this folder?" \
  --response "to log codex Q&A"
```

```bash
qa-logger wrap \
  --question "What is 2+2?" \
  --command "echo 4"
```

```bash
cp config.example.yaml config.yaml
qa-logger parse-transcript --config config.yaml
```

You can still use `python3 -m qa_logger ...` if preferred.

## Config file

`config.yaml` uses a small YAML subset (top-level keys and lists):

```yaml
transcript_paths:
  - ./transcripts
agent: codex
cwd: /Users/charley/codex/questions
session_output_dir: logs/sessions
redaction_patterns:
  - "(?i)api[_-]?key\\s*[:=]\\s*[^\\s]+"
```

`parse-transcript` writes per-source snapshot artifacts into `logs/sessions/`.

## Notes

- `wrap` runs commands with shell expansion. Treat command templates as trusted input.
- If transcript messages are missing timestamps, parser uses source file mtime for stable dedupe.
