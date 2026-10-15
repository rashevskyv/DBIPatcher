"""tools/porting/find_sites.py must rediscover the hand-made 912 entry from 905 (and back)."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from dbi_translate import VERSIONS  # noqa: E402

NRO = {"905": os.environ.get("DBI_905_NRO"), "912": os.environ.get("DBI_912_NRO")}


@unittest.skipUnless(all(p and Path(p).is_file() for p in NRO.values()),
                     "set DBI_905_NRO and DBI_912_NRO to pristine release NROs")
class FindSitesTests(unittest.TestCase):
    def port(self, src: str, dst: str) -> str:
        return subprocess.run(
            [sys.executable, str(ROOT / "tools" / "porting" / "find_sites.py"), src, NRO[src], NRO[dst], dst],
            check=True, capture_output=True, text=True, encoding="utf-8").stdout

    def check(self, src: str, dst: str) -> None:
        out, v = self.port(src, dst), VERSIONS[dst]
        for label in ("reader", "fmt", "glog", "ctor", "sink"):
            self.assertIn(f"{label}=Site(0x{getattr(v, label).addr:X},", out)
        self.assertIn(f"cave=(0x{v.cave[0]:X},", out)
        self.assertIn(f"bss_end=(0x{v.bss_end[0]:X}, 0x{v.bss_end[1]:X}, 0x{v.bss_end[2]:X})", out)
        self.assertRegex(out, rf"closest by calls: 0x{v.ctors[0]:x} ")
        self.assertNotIn("check by hand", out)

    def test_905_to_912(self) -> None:
        self.check("905", "912")

    def test_912_to_905(self) -> None:
        self.check("912", "905")


if __name__ == "__main__":
    unittest.main()
