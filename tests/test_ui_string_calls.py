"""Regression tests for DBI 921 activity headers and forwarder settings.

The synthetic NRO runs the real injected ARM64 code in Unicorn. No Switch
binary, NAND, keys or console connection is needed.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

from dbi_translate import PatchError, VERSIONS, patch_nro
from dbi_translate.asm import enc_bl
from dbi_translate.runtime import STATE_MAGIC
from scripts.build_translation_bin import build_table, load_pairs_csv

try:
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn import arm64_const as reg
except ImportError:
    Uc = None

V = VERSIONS["921"]
BASE, HEAP, STACK, STOP = 0x7100000000, 0x7400000000, 0x7300000000, 0x7500000000
CASES = [
    ("Игрок", "Joueur"), ("Сессии", "Sessions"), ("Время", "Temps"),
    ("Настроки создания ярлыков", "Paramètres des raccourcis"),
    ("Использовать 4 ядра CPU", "Utiliser les 4 cœurs CPU"),
    ("Захват видео", "Capture vidéo"), ("Скриншоты", "Captures d'écran"),
]


def synthetic_nro():
    data = bytearray(0xFDA000)
    struct.pack_into("<I", data, 4, 0xF0)
    data[0xF0:0xF4] = b"MOD0"
    struct.pack_into("<I", data, V.bss_end[0], V.bss_end[1])
    struct.pack_into("<III", data, 0x30, len(data), 0, 0x1274000 - len(data))
    for site in (V.reader, V.fmt, V.glog, V.ctor, V.sink):
        struct.pack_into("<I", data, site.addr, site.insn)
    for addr in V.ctors:
        struct.pack_into("<I", data, addr, 0x91004005)
    for call in V.string_calls:
        struct.pack_into("<I", data, call.addr, enc_bl(call.addr, call.target))
    return bytes(data)


class UiStringBuildTests(unittest.TestCase):
    def test_rejects_wrong_ui_call(self):
        data = bytearray(synthetic_nro())
        struct.pack_into("<I", data, V.string_calls[0].addr, 0xD503201F)
        with self.assertRaisesRegex(PatchError, "UI string call"):
            patch_nro(V, data)

    def test_older_versions_have_no_ui_string_calls(self):
        for version in ("905", "912", "920"):
            self.assertEqual(VERSIONS[version].string_calls, ())

    def test_invalid_configuration_and_small_cave(self):
        for version in (replace(V, string_append=0),
                        replace(V, string_calls=(replace(V.string_calls[0], argument=8),)),
                        replace(V, cave=(V.cave[0], V.cave[0] + 100))):
            with self.subTest(version=version):
                with self.assertRaises(PatchError):
                    patch_nro(version, synthetic_nro())


@unittest.skipUnless(Uc, "needs unicorn")
class UiStringEmulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input = synthetic_nro()
        cls.nro, _ = patch_nro(V, cls.input)
        cls.table, _, _ = build_table(load_pairs_csv(ROOT / "translations/fr.csv"))

    def emulate(self, call, text, expected, loaded=True, table=None):
        mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        for address, size in [(BASE, 0x1280000), (HEAP, 0x400000), (STACK, 0x20000), (STOP, 0x1000)]:
            mu.mem_map(address, size)
        mu.mem_write(BASE, self.nro)
        mu.mem_write(HEAP, table or self.table)
        if loaded:
            mu.mem_write(BASE + V.state + 0x10, struct.pack("<QQ", STATE_MAGIC, HEAP))
        obj, buffer = HEAP + 0x200000, HEAP + 0x210000
        source = text.encode()
        mu.mem_write(obj, struct.pack("<QQQ", buffer, len(source), 1024))
        mu.mem_write(buffer, source + b"\0")
        registers = [getattr(reg, f"UC_ARM64_REG_X{i}") for i in range(31)]
        simd = [getattr(reg, f"UC_ARM64_REG_Q{i}") for i in range(32)]
        for i, register in enumerate(registers):
            mu.reg_write(register, 0x123456780000 + i * 0x101)
        for i, register in enumerate(simd):
            mu.reg_write(register, (0xFEDCBA9876543210 << 64) | i)
        mu.reg_write(registers[call.argument], obj)
        mu.reg_write(reg.UC_ARM64_REG_SP, STACK + 0x10000)
        mu.reg_write(reg.UC_ARM64_REG_LR, STOP)
        mu.reg_write(reg.UC_ARM64_REG_NZCV, 0xA0000000)
        mu.reg_write(reg.UC_ARM64_REG_CPACR_EL1, 0x300000)
        checked = registers + simd + [reg.UC_ARM64_REG_SP, reg.UC_ARM64_REG_NZCV]
        before = [mu.reg_read(r) for r in checked]
        seen = []

        def hook(uc, address, size, _):
            if address == BASE + call.target:
                seen.append(address)
                uc.emu_stop()
            elif address == BASE + V.string_append:
                # Model only DBI's append, and deliberately clobber its volatile
                # registers to check the trampoline rather than a lenient stub.
                dest, src, length = [uc.reg_read(r) for r in registers[:3]]
                pointer, old_length = struct.unpack("<QQ", uc.mem_read(dest, 16))
                self.assertEqual(old_length, 0)
                value = bytes(uc.mem_read(src, length))
                uc.mem_write(pointer, value + b"\0")
                uc.mem_write(dest + 8, struct.pack("<Q", length))
                for r in registers[:19] + simd:
                    uc.reg_write(r, 0xBAD)
                uc.reg_write(reg.UC_ARM64_REG_NZCV, 0x50000000)
                uc.reg_write(reg.UC_ARM64_REG_PC, uc.reg_read(reg.UC_ARM64_REG_LR))

        mu.hook_add(UC_HOOK_CODE, hook)
        word = struct.unpack_from("<I", self.nro, call.addr)[0]
        wrapper = call.addr + ((((word & 0x3FFFFFF) ^ 0x2000000) - 0x2000000) << 2)
        mu.emu_start(BASE + wrapper, STOP, count=1000000)
        self.assertEqual(seen, [BASE + call.target])
        self.assertEqual([mu.reg_read(r) for r in checked], before)
        pointer, length = struct.unpack("<QQ", mu.mem_read(obj, 16))
        self.assertEqual(bytes(mu.mem_read(pointer, length)).decode(), expected)
        self.assertEqual(bytes(mu.mem_read(pointer + length, 1)), b"\0")

    def test_all_seven_calls(self):
        for call, (source, target) in zip(V.string_calls, CASES):
            with self.subTest(site=hex(call.addr), source=source):
                self.emulate(call, source, target)

    def test_misses_already_translated_and_empty(self):
        for call in (V.string_calls[0], V.string_calls[3], V.string_calls[4]):
            for text in ("", "Already translated", "Paramètres des raccourcis", "x" * 400):
                with self.subTest(site=hex(call.addr), text=text[:30]):
                    self.emulate(call, text, text)

    def test_missing_table(self):
        self.emulate(V.string_calls[0], "Игрок", "Игрок", loaded=False)

    def test_other_language_uses_the_same_hooks(self):
        table, _, _ = build_table(load_pairs_csv(ROOT / "translations/en.csv"))
        self.emulate(V.string_calls[3], "Настроки создания ярлыков", "Forwarder settings", table=table)

    def test_changes_stay_in_cave_and_configured_sites(self):
        allowed = [s.addr for s in (V.reader, V.fmt, V.glog, V.ctor, V.sink)]
        allowed += [*V.ctors, V.bss_end[0], *(c.addr for c in V.string_calls)]
        for i, (before, after) in enumerate(zip(self.input, self.nro)):
            if before != after:
                self.assertTrue(V.cave[0] <= i < V.cave[1] or (i & ~3) in allowed)


if __name__ == "__main__":
    unittest.main()
