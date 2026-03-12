from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qa_logger.transcript_parser import discover_transcript_files, entries_from_transcript, pair_turns


class TestTranscriptParser(unittest.TestCase):
    def test_pair_turns(self) -> None:
        events = [
            {"role": "user", "text": "Q1", "timestamp": "2026-03-12T01:00:00Z"},
            {"role": "assistant", "text": "A1", "timestamp": "2026-03-12T01:00:01Z"},
            {"role": "user", "text": "Q2", "timestamp": "2026-03-12T01:01:00Z"},
            {"role": "assistant", "text": "A2", "timestamp": "2026-03-12T01:01:01Z"},
        ]
        pairs = pair_turns(events)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0]["question"], "Q1")
        self.assertEqual(pairs[1]["response"], "A2")

    def test_entries_from_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            rows = [
                {"role": "user", "content": "How are you?", "timestamp": "2026-03-12T02:00:00Z"},
                {"role": "assistant", "content": "Great.", "timestamp": "2026-03-12T02:00:01Z"},
            ]
            path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

            entries = entries_from_transcript(path, cwd="/tmp", agent="codex")
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["question"], "How are you?")
            self.assertEqual(entries[0]["source_mode"], "transcript")
            self.assertTrue(str(path) in entries[0]["source_ref"])

    def test_discover_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "a.jsonl").write_text("", encoding="utf-8")
            (d / "b.txt").write_text("", encoding="utf-8")
            files = discover_transcript_files([str(d)])
            names = [f.name for f in files]
            self.assertEqual(names, ["a.jsonl", "b.txt"])


if __name__ == "__main__":
    unittest.main()
