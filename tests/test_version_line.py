"""The top-bar version line ("912-ru FW:... SDK:...") shows the translation's language code."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.validator import validate  # noqa: E402

KEY = "{}-{} FW:{}{} SDK:{}"   # DBI fmt template; args: version, "ru", firmware, firmware suffix, SDK


class VersionLineTests(unittest.TestCase):
    def test_hidden_argument_counts_as_placeholder(self) -> None:
        ok, err = validate(KEY, "{}-ua{:.0} FW:{}{} SDK:{}", "ua")
        self.assertTrue(ok, err)
        ok, _ = validate(KEY, "{}-ua FW:{}{} SDK:{}", "ua")
        self.assertFalse(ok)

    def test_every_language_shows_its_code(self) -> None:
        langs = json.loads((ROOT / "data" / "languages.json").read_text(encoding="utf-8"))
        for lc in langs:
            with (ROOT / "translations" / f"{lc}.csv").open(encoding="utf-8", newline="") as f:
                rows = {r[0]: r[1] for r in csv.reader(f) if len(r) >= 2}
            self.assertEqual(rows[KEY], "{}-" + lc + "{:.0} FW:{}{} SDK:{}", lc)


if __name__ == "__main__":
    unittest.main()
