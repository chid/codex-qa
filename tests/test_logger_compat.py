from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qa_logger.logger import append_entries, build_entry


class TestLoggerCompat(unittest.TestCase):
    def test_dedupe_works_with_legacy_rows_without_dedupe_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "qa.jsonl"
            legacy = {
                "timestamp": "2026-03-12T10:00:00Z",
                "question": "Legacy question",
                "response": "Legacy answer",
                "source_ref": "legacy-1",
            }
            log_path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

            new_entry = build_entry(
                "Legacy question",
                "New answer should be skipped",
                timestamp="2026-03-12T10:00:00Z",
                source_ref="legacy-1",
            )
            written, skipped = append_entries([new_entry], path=log_path)

            self.assertEqual((written, skipped), (0, 1))
            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)

    def test_dedupe_normalizes_question_whitespace_and_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "qa.jsonl"

            first = build_entry(
                "What  Is  This?",
                "A",
                timestamp="2026-03-12T10:10:00Z",
                source_ref="s1",
            )
            second = build_entry(
                " what is this? ",
                "B",
                timestamp="2026-03-12T10:10:00Z",
                source_ref="s1",
            )
            w1, s1 = append_entries([first], path=log_path)
            w2, s2 = append_entries([second], path=log_path)

            self.assertEqual((w1, s1), (1, 0))
            self.assertEqual((w2, s2), (0, 1))


if __name__ == "__main__":
    unittest.main()
