from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = Path("logs/qa.jsonl")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def question_hash(question: str) -> str:
    digest = hashlib.sha256(normalize_text(question).encode("utf-8")).hexdigest()
    return digest[:16]


def build_dedupe_key(timestamp: str, question: str, source_ref: str | None) -> str:
    return f"{timestamp}|{question_hash(question)}|{source_ref or '-'}"


def build_entry(
    question: str,
    response: str,
    *,
    timestamp: str | None = None,
    cwd: str | None = None,
    agent: str = "codex",
    tags: list[str] | None = None,
    source_mode: str = "manual",
    source_ref: str | None = None,
) -> dict[str, Any]:
    ts = timestamp or now_iso()
    entry = {
        "timestamp": ts,
        "cwd": cwd,
        "agent": agent,
        "question": question,
        "response": response,
        "tags": tags or [],
        "source_mode": source_mode,
        "source_ref": source_ref,
    }
    entry["_dedupe_key"] = build_dedupe_key(ts, question, source_ref)
    return entry


def _load_existing_dedupe_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    if not path.exists():
        return keys

    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            dedupe = obj.get("_dedupe_key")
            if isinstance(dedupe, str):
                keys.add(dedupe)
                continue
            ts = str(obj.get("timestamp", ""))
            q = str(obj.get("question", ""))
            src = obj.get("source_ref")
            if ts and q:
                keys.add(build_dedupe_key(ts, q, src if isinstance(src, str) else None))
    return keys


def append_entries(entries: list[dict[str, Any]], path: Path = DEFAULT_LOG_PATH) -> tuple[int, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_existing_dedupe_keys(path)

    written = 0
    skipped = 0
    with path.open("a", encoding="utf-8") as fh:
        for entry in entries:
            key = entry.get("_dedupe_key")
            if not isinstance(key, str):
                ts = str(entry.get("timestamp", ""))
                q = str(entry.get("question", ""))
                src = entry.get("source_ref")
                key = build_dedupe_key(ts, q, src if isinstance(src, str) else None)
                entry["_dedupe_key"] = key

            if key in existing:
                skipped += 1
                continue

            fh.write(json.dumps(entry, ensure_ascii=True) + "\n")
            existing.add(key)
            written += 1

    return written, skipped
