from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _strip_comment(line: str) -> str:
    in_quote = False
    quote_char = ""
    for idx, ch in enumerate(line):
        if ch in ('"', "'"):
            if not in_quote:
                in_quote = True
                quote_char = ch
            elif quote_char == ch:
                in_quote = False
                quote_char = ""
        if ch == "#" and not in_quote:
            return line[:idx]
    return line


def _coerce_scalar(value: str) -> Any:
    v = value.strip()
    if not v:
        return ""
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1]
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    lower = v.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    if lower in {"null", "none"}:
        return None
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


def parse_min_yaml(text: str) -> dict[str, Any]:
    """Parse a minimal YAML subset supporting top-level keys + list values."""
    result: dict[str, Any] = {}
    current_list_key: str | None = None

    for raw_line in text.splitlines():
        line = _strip_comment(raw_line).rstrip()
        if not line.strip():
            continue

        if line.lstrip().startswith("- "):
            if current_list_key is None:
                raise ValueError("Invalid YAML: list item without key")
            result.setdefault(current_list_key, [])
            item = _coerce_scalar(line.split("-", 1)[1].strip())
            result[current_list_key].append(item)
            continue

        current_list_key = None
        if ":" not in line:
            raise ValueError(f"Invalid YAML line: {raw_line}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()

        if value == "":
            result[key] = []
            current_list_key = key
        else:
            result[key] = _coerce_scalar(value)

    return result


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}

    if raw[0] in "[{":
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError("Config root must be an object")
        return obj

    return parse_min_yaml(raw)
