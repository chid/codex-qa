from __future__ import annotations

import re
from typing import Iterable


def apply_redaction(text: str, patterns: Iterable[str], replacement: str = "[REDACTED]") -> str:
    """Apply regex redaction patterns to text."""
    redacted = text
    for pattern in patterns:
        redacted = re.sub(pattern, replacement, redacted)
    return redacted
