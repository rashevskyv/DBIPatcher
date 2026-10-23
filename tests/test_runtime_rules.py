"""Run the injected loader and matchers (pfxsfx, ctor_exact) of patched DBI 905/912 builds in Unicorn and
compare them with the Python model of the rules in tools/porting/emu_runtime.py: no second
pass over a translation, word-boundary prefix/suffix hits, prefix-of-translation extension."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "tools" / "porting"))

from dbi_translate import VERSIONS, patch_nro  # noqa: E402

try:
    import emu_runtime  # noqa: E402  (needs unicorn)
except ImportError:
    emu_runtime = None

NRO = {"905": os.environ.get("DBI_905_NRO"), "912": os.environ.get("DBI_912_NRO"),
       "920": os.environ.get("DBI_920_NRO"), "921": os.environ.get("DBI_921_NRO")}


def build_table(td: str, fmt: int) -> bytes:
    out = Path(td) / f"translation_v{fmt}.bin"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_translation_bin.py"),
                    "--format", str(fmt), str(ROOT / "translations" / "ua.csv"), "-o", str(out)],
                   check=True, capture_output=True)
    return out.read_bytes()


@unittest.skipUnless(emu_runtime, "needs unicorn")
class RuntimeRulesTests(unittest.TestCase):
    def check(self, version: str, fmt: int = 3, step: int = 37) -> None:
        path = NRO[version]
        if not (path and Path(path).is_file()):
            self.skipTest(f"set DBI_{version}_NRO to a pristine DBI {version} NRO")
        v = VERSIONS[version]
        nro, report = patch_nro(v, Path(path).read_bytes())
        bases = dict(re.findall(r"(\w+)=(0x[0-9a-f]+)", report[-1]))
        with tempfile.TemporaryDirectory() as td:
            table = build_table(td, fmt)
        loader = int(bases["loader"], 16)
        self.assertTrue(emu_runtime.run_loader(nro, table, v.state, loader, v.reader_fn))
        self.assertFalse(emu_runtime.run_loader(nro, table[:-4], v.state, loader, v.reader_fn))
        _, K, V = emu_runtime.load_table_bytes(table)
        emu = emu_runtime.Emu(nro, table, v.state)
        px, ce = int(bases["pfxsfx"], 16), int(bases["ctor_exact"], 16)
        for c in emu_runtime.corpus(K, V, step=step):
            with self.subTest(pfxsfx=c[:40]):
                self.assertEqual(emu.pfxsfx(px, c), emu_runtime.model_pfxsfx(K, V, c))
        for buf, n in emu_runtime.ctor_corpus(K, V, step=step):
            with self.subTest(ctor=buf[:n][:40]):
                self.assertEqual(emu.ctor(ce, buf, n), emu_runtime.model_ctor(K, V, buf, n))
        # the console bugs this rule set fixes
        self.assertEqual(emu.pfxsfx(px, "Дампити на SD-карту".encode()), "Дампити на SD-карту".encode())
        self.assertEqual(emu.ctor(ce, "Видалити".encode() + b"\0", 14), "Видалити".encode())
        # issue #29: a translation shorter than the Russian length, copied with its NUL and a
        # stale UTF-8 continuation byte, is cut at the NUL
        self.assertEqual(emu.ctor(ce, "Так".encode() + b"\0\x9f\x00", 8), "Так".encode())
        self.assertEqual(emu.ctor(ce, b"ab\0\x9f", 4), b"ab\0\x9f")   # not a translation
        # a panel line ending in a number: "... ({})" key, the number goes into the translation
        line = "Общее время игры      : - (2)".encode()
        self.assertEqual(emu.ctor(ce, line, len(line)), "Загальний час гри : - (2)".encode())

    def test_912(self) -> None:
        self.check("912")

    def test_920(self) -> None:
        self.check("920")

    def test_921(self) -> None:
        self.check("921")

    def test_912_plain_table(self) -> None:
        # version-2 tables (no hash index) still load and match the same way
        self.check("912", fmt=2, step=97)

    def test_905(self) -> None:
        self.check("905")


if __name__ == "__main__":
    unittest.main()
