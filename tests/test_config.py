from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qa_logger.config import load_config, parse_min_yaml


class TestConfig(unittest.TestCase):
    def test_parse_min_yaml_lists_scalars_and_comments(self) -> None:
        raw = """
        transcript_paths:
          - ./transcripts # trailing comment
          - "./other#folder"
        enabled: true
        retries: 3
        """
        parsed = parse_min_yaml(raw)
        self.assertEqual(parsed["transcript_paths"], ["./transcripts", "./other#folder"])
        self.assertTrue(parsed["enabled"])
        self.assertEqual(parsed["retries"], 3)

    def test_parse_min_yaml_list_without_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_min_yaml("- orphan-item")

    def test_load_config_json_requires_object_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)

    def test_load_config_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            path.write_text("", encoding="utf-8")
            self.assertEqual(load_config(path), {})


if __name__ == "__main__":
    unittest.main()
