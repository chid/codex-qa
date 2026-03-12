from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qa_logger.logger import append_entries, build_entry
from qa_logger.redaction import apply_redaction


class TestLogger(unittest.TestCase):
    def test_append_dedupes_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "qa.jsonl"
            entry = build_entry(
                "What is 2+2?",
                "4",
                timestamp="2026-03-12T00:00:00Z",
                source_ref="manual-1",
            )

            w1, s1 = append_entries([entry], path=log_path)
            w2, s2 = append_entries([entry], path=log_path)

            self.assertEqual((w1, s1), (1, 0))
            self.assertEqual((w2, s2), (0, 1))

    def test_entry_round_trip_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "qa.jsonl"
            entry = build_entry("Q", "A", timestamp="2026-03-12T00:00:00Z")
            append_entries([entry], path=log_path)

            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            row = json.loads(lines[0])
            self.assertEqual(row["question"], "Q")
            self.assertEqual(row["response"], "A")
            self.assertIn("_dedupe_key", row)

    def test_redaction(self) -> None:
        text = "token=secret123"
        redacted = apply_redaction(text, [r"secret\d+"])
        self.assertEqual(redacted, "token=[REDACTED]")


if __name__ == "__main__":
    unittest.main()
