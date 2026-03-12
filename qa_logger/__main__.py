from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qa_logger.config import load_config
from qa_logger.logger import DEFAULT_LOG_PATH, append_entries, build_entry
from qa_logger.redaction import apply_redaction
from qa_logger.transcript_parser import discover_transcript_files, entries_from_transcript


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def _apply_optional_redaction(
    entry: dict[str, Any], enabled: bool, patterns: list[str]
) -> dict[str, Any]:
    if not enabled:
        return entry
    redacted = dict(entry)
    redacted["question"] = apply_redaction(str(redacted.get("question", "")), patterns)
    redacted["response"] = apply_redaction(str(redacted.get("response", "")), patterns)
    return redacted


def _write_session_artifact(output_dir: Path, source: Path, entries: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = source.stem.replace(" ", "_")
    target = output_dir / f"{stem}.{ts}.json"
    payload = {
        "source": str(source),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "entry_count": len(entries),
        "entries": entries,
    }
    target.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def cmd_log_turn(args: argparse.Namespace) -> int:
    entry = build_entry(
        args.question,
        args.response,
        cwd=args.cwd,
        agent=args.agent,
        tags=_parse_tags(args.tags),
        source_mode="manual",
        source_ref=args.source_ref,
    )
    entry = _apply_optional_redaction(entry, args.redact, args.redact_pattern)
    written, skipped = append_entries([entry], path=Path(args.log_path))
    print(f"written={written} skipped={skipped} log={args.log_path}")
    return 0


def cmd_wrap(args: argparse.Namespace) -> int:
    question = args.question
    if not question:
        question = input("Question: ").strip()
    if not question:
        raise ValueError("question is required")

    command = args.command.format(question=question)
    proc = subprocess.run(command, shell=True, capture_output=True, text=True)
    response = proc.stdout.strip() or proc.stderr.strip() or f"(no output, exit={proc.returncode})"

    entry = build_entry(
        question,
        response,
        cwd=args.cwd,
        agent=args.agent,
        tags=_parse_tags(args.tags),
        source_mode="wrapper",
        source_ref=args.command,
    )
    entry = _apply_optional_redaction(entry, args.redact, args.redact_pattern)

    written, skipped = append_entries([entry], path=Path(args.log_path))
    print(
        f"command_exit={proc.returncode} written={written} skipped={skipped} log={args.log_path}"
    )
    return proc.returncode


def cmd_parse_transcript(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    transcript_paths = config.get("transcript_paths", [])
    if not isinstance(transcript_paths, list):
        raise ValueError("config.transcript_paths must be a list")

    agent = str(config.get("agent", args.agent))
    cwd = str(config.get("cwd", os.getcwd()))
    session_output_dir = Path(str(config.get("session_output_dir", "logs/sessions")))

    config_patterns = config.get("redaction_patterns", [])
    if not isinstance(config_patterns, list):
        raise ValueError("config.redaction_patterns must be a list")
    patterns = [str(x) for x in config_patterns] + list(args.redact_pattern)

    files = discover_transcript_files([str(p) for p in transcript_paths])
    all_entries: list[dict[str, Any]] = []

    for src in files:
        entries = entries_from_transcript(src, cwd=cwd, agent=agent)
        if args.redact:
            entries = [_apply_optional_redaction(e, True, patterns) for e in entries]
        _write_session_artifact(session_output_dir, src, entries)
        all_entries.extend(entries)

    written, skipped = append_entries(all_entries, path=Path(args.log_path))
    print(
        f"files={len(files)} parsed_entries={len(all_entries)} written={written} "
        f"skipped={skipped} log={args.log_path}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Q&A logger for Codex sessions")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--log-path", default=str(DEFAULT_LOG_PATH))
    common.add_argument("--agent", default="codex")
    common.add_argument("--cwd", default=os.getcwd())
    common.add_argument("--tags", default="")
    common.add_argument("--redact", action="store_true")
    common.add_argument("--redact-pattern", action="append", default=[])

    p_log = sub.add_parser("log-turn", parents=[common], help="Append one Q&A entry")
    p_log.add_argument("--question", required=True)
    p_log.add_argument("--response", required=True)
    p_log.add_argument("--source-ref", default="")
    p_log.set_defaults(func=cmd_log_turn)

    p_wrap = sub.add_parser("wrap", parents=[common], help="Run command template and log output")
    p_wrap.add_argument("--question", default="")
    p_wrap.add_argument(
        "--command",
        required=True,
        help="Command template. Use {question} placeholder. Example: 'echo {question}'",
    )
    p_wrap.set_defaults(func=cmd_wrap)

    p_parse = sub.add_parser(
        "parse-transcript", parents=[common], help="Parse transcript files into Q&A entries"
    )
    p_parse.add_argument("--config", default="config.yaml")
    p_parse.set_defaults(func=cmd_parse_transcript)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
