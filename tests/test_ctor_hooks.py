"""Run hooked std::string(const char*, size_t) copies of a patched DBI 912 in Unicorn with a
real translation table and check what they construct (game info panel labels)."""

from __future__ import annotations

import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from dbi_translate import VERSIONS, patch_nro  # noqa: E402
from dbi_translate.runtime import STATE_MAGIC  # noqa: E402

try:
    from unicorn import UC_ARCH_ARM64, UC_HOOK_CODE, UC_MODE_ARM, Uc
    from unicorn.arm64_const import (UC_ARM64_REG_CPACR_EL1, UC_ARM64_REG_LR, UC_ARM64_REG_PC,
                                     UC_ARM64_REG_SP, UC_ARM64_REG_X0, UC_ARM64_REG_X1,
                                     UC_ARM64_REG_X2)
except ImportError:  # optional test dependency
    Uc = None

NRO912 = os.environ.get("DBI_912_NRO")
BASE = 0x7100000000
M_CREATE = 0x7403A4      # std::string::_M_create (heap allocation) in DBI 912
HEAP, STACK, STOP = 0x7400000000, 0x7300000000, 0x7500000000

CASES = [
    ("Тикеты", "Тікети"),
    ("Контент", "Контент"),
    ("Язык    : ", "Мова    : "),
    ("Версия  : ", "Версія  : "),     # translation > 15 bytes: heap path
    ("hello", "hello"),                 # ASCII: gate skips the lookup
    ("Привет мир", "Привет мир"),       # Cyrillic miss
    ("C:/Сохранения/x", "C:/Сохранения/x"),   # exact match only: paths stay intact
]


@unittest.skipUnless(Uc and NRO912 and Path(NRO912).is_file(),
                     "needs unicorn and DBI_912_NRO (pristine DBI 912 NRO)")
class CtorHookEmulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        v = VERSIONS["912"]
        nro, _ = patch_nro(v, Path(NRO912).read_bytes())
        with tempfile.TemporaryDirectory() as td:
            table = Path(td) / "translation.bin"
            subprocess.run([sys.executable, str(ROOT / "scripts" / "build_translation_bin.py"),
                            str(ROOT / "translations" / "ua.csv"), "-o", str(table)],
                           check=True, capture_output=True)
            table_bytes = table.read_bytes()
        mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        mu.mem_map(BASE, 0x1280000)
        mu.mem_write(BASE, nro[:0xFDA000])
        mu.reg_write(UC_ARM64_REG_CPACR_EL1, 0x300000)          # enable FP/NEON
        mu.mem_map(HEAP, 0x200000)
        mu.mem_write(HEAP, table_bytes)
        mu.mem_write(BASE + v.state + 0x10, struct.pack("<QQ", STATE_MAGIC, HEAP))
        mu.mem_map(STACK, 0x10000)
        mu.mem_map(STOP, 0x1000)
        cls.heap_top = HEAP + 0x190000

        def m_create(uc, addr, size, _):
            cap = struct.unpack("<Q", uc.mem_read(uc.reg_read(UC_ARM64_REG_X1), 8))[0]
            uc.reg_write(UC_ARM64_REG_X0, cls.heap_top)
            cls.heap_top += (cap + 16) & ~15
            uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))

        mu.hook_add(UC_HOOK_CODE, m_create, begin=BASE + M_CREATE, end=BASE + M_CREATE)
        cls.mu, cls.v = mu, v

    def construct(self, ctor: int, text: str) -> str:
        mu, data = self.mu, text.encode()
        dest, src = HEAP + 0x180000, HEAP + 0x181000
        mu.mem_write(dest, b"\xee" * 0x20)
        mu.mem_write(src, data + b"\0")
        for reg, val in ((UC_ARM64_REG_X0, dest), (UC_ARM64_REG_X1, src),
                         (UC_ARM64_REG_X2, len(data)), (UC_ARM64_REG_SP, STACK + 0x8000),
                         (UC_ARM64_REG_LR, STOP)):
            mu.reg_write(reg, val)
        mu.emu_start(BASE + ctor, STOP, count=200000)
        ptr, length = struct.unpack("<QQ", mu.mem_read(dest, 16))
        return bytes(mu.mem_read(ptr, length)).decode()

    def test_first_and_last_ctor_copy(self) -> None:
        for ctor in (self.v.ctors[0], self.v.ctors[-1]):
            for src, want in CASES:
                with self.subTest(ctor=hex(ctor), src=src):
                    self.assertEqual(self.construct(ctor, src), want)


if __name__ == "__main__":
    unittest.main()
