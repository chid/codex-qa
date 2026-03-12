from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qa_logger.logger import build_entry


def _stable_file_timestamp(path: Path) -> str:
    dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        chunks: list[str] = []
        for item in value:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                if "text" in item and isinstance(item["text"], str):
                    chunks.append(item["text"])
                elif "content" in item:
                    chunks.append(_extract_text(item["content"]))
        return "\n".join(c for c in chunks if c).strip()
    if isinstance(value, dict):
        for key in ("text", "content", "value", "message"):
            if key in value:
                return _extract_text(value[key])
    return ""


def _extract_role(obj: dict[str, Any]) -> str | None:
    for key in ("role", "speaker", "type"):
        role = obj.get(key)
        if isinstance(role, str):
            r = role.lower()
            if "user" in r:
                return "user"
            if "assistant" in r or "model" in r:
                return "assistant"
    return None


def _extract_timestamp(obj: dict[str, Any]) -> str | None:
    for key in ("timestamp", "time", "created_at"):
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _events_from_jsonl(path: Path) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        role = _extract_role(obj)
        if role is None:
            continue
        text = _extract_text(obj.get("content") if "content" in obj else obj.get("text"))
        if not text:
            continue
        events.append({
            "role": role,
            "text": text,
            "timestamp": _extract_timestamp(obj) or "",
        })
    return events


def _events_from_json(path: Path) -> list[dict[str, str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items: list[Any]
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("messages"), list):
            items = raw["messages"]
        elif isinstance(raw.get("events"), list):
            items = raw["events"]
        else:
            items = [raw]
    else:
        items = []

    events: list[dict[str, str]] = []
    for obj in items:
        if not isinstance(obj, dict):
            continue
        role = _extract_role(obj)
        if role is None:
            continue
        text = _extract_text(obj.get("content") if "content" in obj else obj.get("text"))
        if not text:
            continue
        events.append({
            "role": role,
            "text": text,
            "timestamp": _extract_timestamp(obj) or "",
        })
    return events


def _events_from_text(path: Path) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    current_role: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_role, current_lines
        if current_role and current_lines:
            events.append({"role": current_role, "text": "\n".join(current_lines).strip(), "timestamp": ""})
        current_role = None
        current_lines = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        lower = line.lower()
        if lower.startswith("user:"):
            flush()
            current_role = "user"
            current_lines.append(line.split(":", 1)[1].strip())
        elif lower.startswith("assistant:"):
            flush()
            current_role = "assistant"
            current_lines.append(line.split(":", 1)[1].strip())
        elif current_role:
            current_lines.append(raw)
    flush()
    return events


def parse_transcript_file(path: Path) -> list[dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return _events_from_jsonl(path)
    if suffix == ".json":
        return _events_from_json(path)
    return _events_from_text(path)


def pair_turns(events: list[dict[str, str]]) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    pending_question: dict[str, str] | None = None

    for event in events:
        role = event.get("role")
        if role == "user":
            pending_question = event
            continue
        if role == "assistant" and pending_question:
            pairs.append(
                {
                    "question": pending_question.get("text", ""),
                    "response": event.get("text", ""),
                    "timestamp": pending_question.get("timestamp", ""),
                }
            )
            pending_question = None
    return pairs


def discover_transcript_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_file():
            files.append(path)
            continue
        if path.is_dir():
            for pattern in ("*.jsonl", "*.json", "*.txt", "**/*.jsonl", "**/*.json", "**/*.txt"):
                files.extend(path.glob(pattern))
    # Stable ordering and dedupe by resolved path
    unique: dict[str, Path] = {}
    for f in files:
        unique[str(f.resolve())] = f
    return [unique[k] for k in sorted(unique.keys())]


def entries_from_transcript(path: Path, *, cwd: str | None = None, agent: str = "codex") -> list[dict[str, Any]]:
    events = parse_transcript_file(path)
    turns = pair_turns(events)
    fallback_ts = _stable_file_timestamp(path)
    entries: list[dict[str, Any]] = []

    for idx, turn in enumerate(turns):
        ts = turn["timestamp"] or fallback_ts
        entries.append(
            build_entry(
                turn["question"],
                turn["response"],
                timestamp=ts,
                cwd=cwd,
                agent=agent,
                source_mode="transcript",
                source_ref=f"{path}:{idx}",
            )
        )
    return entries
