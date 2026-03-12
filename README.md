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

Run from this folder.

```bash
python -m qa_logger log-turn \
  --question "purpose of this folder?" \
  --response "to log codex Q&A"
```

```bash
python -m qa_logger wrap \
  --question "What is 2+2?" \
  --command "echo 4"
```

```bash
cp config.example.yaml config.yaml
python -m qa_logger parse-transcript --config config.yaml
```

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
