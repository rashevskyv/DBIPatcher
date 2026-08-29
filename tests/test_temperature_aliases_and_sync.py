"""Regression tests for PR #22 and PR #23 temperature aliases, cmd_sync deduplication, and workbook/CSV consistency."""

from __future__ import annotations

import ast
import csv
import json
import sys
import unittest
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.text_utils import tokenize  # noqa: E402


class TemperatureAliasesAndSyncTests(unittest.TestCase):
    """Verify temperature aliases durability, single cmd_sync definition, and CSV consistency."""

    def setUp(self) -> None:
        self.dict_path = ROOT / "data" / "dictionary.xlsx"
        self.lang_path = ROOT / "data" / "languages.json"
        self.main_py_path = ROOT / "src" / "main.py"
        self.translations_dir = ROOT / "translations"

        with open(self.lang_path, "r", encoding="utf-8") as f:
            self.languages = json.load(f)

        self.wb = openpyxl.load_workbook(self.dict_path)
        self.ws = self.wb["Translations"]

        self.headers = [
            self.ws.cell(1, c).value for c in range(1, self.ws.max_column + 1)
        ]
        self.col_map = {h: i + 1 for i, h in enumerate(self.headers) if h}

    def tearDown(self) -> None:
        self.wb.close()

    def test_single_cmd_sync_definition(self) -> None:
        """Ensure exactly one cmd_sync function definition exists in src/main.py."""
        with open(self.main_py_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(self.main_py_path))

        sync_defs = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "cmd_sync"
        ]
        self.assertEqual(
            len(sync_defs),
            1,
            f"Expected exactly 1 definition of cmd_sync, found {len(sync_defs)}",
        )

    def test_workbook_structure_and_version(self) -> None:
        """Verify workbook contains 1,288 unique Original keys, 'tr' column, and version 0.0.86."""
        self.assertIn("tr", self.headers, "Translations sheet missing 'tr' column")

        meta_ws = self.wb["Metadata"]
        version = str(meta_ws["B1"].value or "")
        self.assertEqual(version, "0.0.86", f"Expected version 0.0.86, got {version}")

        original_col = self.col_map["Original"]
        originals = []
        for r in range(2, self.ws.max_row + 1):
            val = self.ws.cell(r, original_col).value
            if val is not None and str(val).strip():
                originals.append(str(val))

        self.assertEqual(
            len(originals),
            1288,
            f"Expected 1,288 original keys, found {len(originals)}",
        )
        self.assertEqual(
            len(set(originals)),
            1288,
            f"Expected 1,288 unique original keys, found {len(set(originals))}",
        )

    def test_all_45_aliases_and_canonical_values(self) -> None:
        """Verify all 45 PR #22 & PR #23 aliases exist once and match canonical translations."""
        can1_key = "Температура        : {}°C"
        can2_key = "Температура батареи             : {}°C"
        can3_key = "Средняя температура: {}°C"

        # 24 PR #22 literal '$°$' aliases
        pr22_aliases = [
            "Температура    : {}$°$C",
            "Температура     : {}$°$C",
            "Температура      : {}$°$C",
            "Температура       : {}$°$C",
            "Температура        : {}$°$C",
            "Температура         : {}$°$C",
            "Температура          : {}$°$C",
            "Температура           : {}$°$C",
            "Температура            : {}$°$C",
            "Температура             : {}$°$C",
            "Температура              : {}$°$C",
            "Срепняя температура: {}$°$C",
            "Средняя температура: {}$°$C",
            "Температура батареи        : {}$°$C",
            "Температура батареи         : {}$°$C",
            "Температура батареи          : {}$°$C",
            "Температура батареи           : {}$°$C",
            "Температура батареи            : {}$°$C",
            "Температура батареи             : {}$°$C",
            "Температура батареи              : {}$°$C",
            "Температура батареи               : {}$°$C",
            "Температура батареи                : {}$°$C",
            "Температура батареи                 : {}$°$C",
            "Температура батареи                  : {}$°$C",
        ]

        # 21 PR #23 clean '°' aliases
        pr23_aliases = [
            "Температура    : {}°C",
            "Температура     : {}°C",
            "Температура      : {}°C",
            "Температура       : {}°C",
            "Температура         : {}°C",
            "Температура          : {}°C",
            "Температура           : {}°C",
            "Температура            : {}°C",
            "Температура             : {}°C",
            "Температура              : {}°C",
            "Температура батареи        : {}°C",
            "Температура батареи         : {}°C",
            "Температура батареи          : {}°C",
            "Температура батареи           : {}°C",
            "Температура батареи            : {}°C",
            "Температура батареи              : {}°C",
            "Температура батареи               : {}°C",
            "Температура батареи                : {}°C",
            "Температура батареи                 : {}°C",
            "Температура батареи                  : {}°C",
            "Срепняя температура: {}°C",
        ]

        all_aliases = pr22_aliases + pr23_aliases
        self.assertEqual(len(all_aliases), 45)
        self.assertEqual(len(set(all_aliases)), 45)

        # Build row map
        original_col = self.col_map["Original"]
        key_to_row = {}
        for r in range(2, self.ws.max_row + 1):
            val = self.ws.cell(r, original_col).value
            if val is not None:
                key_to_row[str(val)] = r

        self.assertIn(can1_key, key_to_row)
        self.assertIn(can2_key, key_to_row)
        self.assertIn(can3_key, key_to_row)

        can1_row = key_to_row[can1_key]
        can2_row = key_to_row[can2_key]
        can3_row = key_to_row[can3_key]

        lang_cols = [lc for lc in self.languages if lc in self.col_map]
        self.assertIn("tr", lang_cols)

        for alias in all_aliases:
            self.assertIn(alias, key_to_row, f"Missing alias in workbook: {repr(alias)}")
            alias_row = key_to_row[alias]

            if alias.startswith("Температура батареи"):
                expected_src_row = can2_row
            elif alias.startswith("Средняя температура") or alias.startswith("Срепняя температура"):
                expected_src_row = can3_row
            elif alias.startswith("Температура"):
                expected_src_row = can1_row
            else:
                self.fail(f"Unrecognized alias prefix: {repr(alias)}")

            for lc in lang_cols:
                col_idx = self.col_map[lc]
                actual_val = self.ws.cell(alias_row, col_idx).value
                expected_val = self.ws.cell(expected_src_row, col_idx).value
                self.assertEqual(
                    actual_val,
                    expected_val,
                    f"Mismatch in alias {repr(alias)} for language '{lc}': got {repr(actual_val)}, expected {repr(expected_val)}",
                )

    def test_exported_csv_keys_match_workbook(self) -> None:
        """Verify every configured language CSV matches the workbook key set exactly."""
        original_col = self.col_map["Original"]
        wb_tokenized_keys = set()
        for r in range(2, self.ws.max_row + 1):
            val = self.ws.cell(r, original_col).value
            if val is not None and str(val).strip():
                wb_tokenized_keys.add(str(val))

        self.assertEqual(len(wb_tokenized_keys), 1288)

        for lc in self.languages:
            if lc == "ru":
                continue
            csv_path = self.translations_dir / f"{lc}.csv"
            self.assertTrue(csv_path.exists(), f"Missing CSV file: {csv_path}")

            csv_keys = set()
            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header = next(reader)
                self.assertEqual(header, ["original", "translation"], f"Bad header in {csv_path}")
                for row in reader:
                    if row:
                        csv_keys.add(tokenize(row[0]))

            self.assertEqual(
                csv_keys,
                wb_tokenized_keys,
                f"Mismatch in source keys for {lc}.csv (diff size: {len(csv_keys ^ wb_tokenized_keys)})",
            )


if __name__ == "__main__":
    unittest.main()