from __future__ import annotations

import dataclasses
import inspect
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import zstandard

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.patch_dbi import (
    COPIED_GLYPHS,
    DBI_SHA256,
    FONT_SIZE,
    GLYPH_COUNT,
    GLYPH_SIZE,
    MIRRORED_GLYPHS,
    REPAIRED_GLYPH_CODEPOINTS,
    decompress_font_frame,
    find_embedded_font,
    patch_cyrillic_glyphs,
    patch_dbi,
    patch_nro_font,
    reverse_16_bits,
)
from dbi_translate import VERSIONS, patch_nro
from dbi_translate.patch import PatchError

# Pristine release NROs for the integration tests (skipped when unset).
NRO = {"905": os.environ.get("DBI_905_NRO"), "912": os.environ.get("DBI_912_NRO"),
       "920": os.environ.get("DBI_920_NRO"), "921": os.environ.get("DBI_921_NRO")}


def make_synthetic_font() -> bytearray:
    """Create a 2 MiB synthetic font with distinctive non-zero patterns in source glyphs."""
    font = bytearray(FONT_SIZE)
    # 0x042D (Э): distinct 16-bit LE rows
    src_042d_off = 0x042D * GLYPH_SIZE
    for row in range(16):
        val = 0x1200 + (row * 0x0011)
        font[src_042d_off + row * 2 : src_042d_off + row * 2 + 2] = val.to_bytes(2, "little")

    # 0x044D (э): distinct 16-bit LE rows
    src_044d_off = 0x044D * GLYPH_SIZE
    for row in range(16):
        val = 0x3400 + (row * 0x0022)
        font[src_044d_off + row * 2 : src_044d_off + row * 2 + 2] = val.to_bytes(2, "little")

    # 0x0049 (I), 0x0069 (i), 0x00CF (Ï), 0x00EF (ï): distinct 32-byte patterns
    font[0x0049 * GLYPH_SIZE : 0x0049 * GLYPH_SIZE + 32] = b"LATIN_CAP_I_" * 2 + b"12345678"
    font[0x0069 * GLYPH_SIZE : 0x0069 * GLYPH_SIZE + 32] = b"latin_sml_i_" * 2 + b"12345678"
    font[0x00CF * GLYPH_SIZE : 0x00CF * GLYPH_SIZE + 32] = b"LATIN_CAP_YI" * 2 + b"12345678"
    font[0x00EF * GLYPH_SIZE : 0x00EF * GLYPH_SIZE + 32] = b"latin_sml_yi" * 2 + b"12345678"

    # Pre-existing placeholder destination glyphs (replaced during repair)
    for cp in REPAIRED_GLYPH_CODEPOINTS:
        font[cp * GLYPH_SIZE : (cp + 1) * GLYPH_SIZE] = b"ORIGINAL_OLD_DST" * 2

    # Patterned data across unused region so level 1 compression (slot) > level 18 (patched)
    for i in range(1000):
        font[0x2000 * GLYPH_SIZE + i * 100 : 0x2000 * GLYPH_SIZE + i * 100 + 32] = b"SAMPLE_DATA_1234" * 2

    return font


def make_synthetic_nro(
    raw_font: bytes | None = None,
    prefix: bytes = b"MOCK_NRO_PREFIX_HEADER" * 4,
    suffix: bytes = b"MOCK_NRO_SUFFIX_FOOTER" * 4,
) -> bytearray:
    """Create a synthetic NRO containing a compressed font frame with prefix and suffix."""
    if raw_font is None:
        raw_font = make_synthetic_font()
    comp = zstandard.ZstdCompressor(
        level=1, write_checksum=True, write_content_size=True
    ).compress(raw_font)
    return bytearray(prefix + comp + suffix)


class PatchDbiWrapperTests(unittest.TestCase):
    """Offline focused tests for scripts/patch_dbi.py."""

    def test_every_known_release_has_an_engine_version(self) -> None:
        self.assertEqual(set(DBI_SHA256.values()), {"905", "912", "920", "921"})
        self.assertTrue(set(DBI_SHA256.values()) <= set(VERSIONS))

    def test_signature(self) -> None:
        params = list(inspect.signature(patch_dbi).parameters)
        self.assertEqual(params, ["nro_path", "output_path"])

    def test_nonexistent_nro_raises_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dummy_output = Path(td) / "out" / "DBI.nro"
            with self.assertRaises(FileNotFoundError):
                patch_dbi(Path(td) / "missing" / "DBI.912.ru.nro", dummy_output)
            self.assertFalse(dummy_output.exists())

    def test_unknown_sha_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            nro = Path(td) / "DBI.nro"
            nro.write_bytes(b"not a supported DBI release")
            out = Path(td) / "out.nro"
            with self.assertRaises(ValueError) as ctx:
                patch_dbi(nro, out)
            self.assertIn("Unsupported NRO SHA-256", str(ctx.exception))
            self.assertFalse(out.exists())

    def test_runtime_line_gate_is_256_bytes(self) -> None:
        runtime = (ROOT / "vendor" / "dbi_translate" / "runtime.py").read_text(encoding="utf-8")
        self.assertIn('("I", "cmp x20, #0x100"), ("I", "b.hi {miss}"),', runtime)
        self.assertNotIn('("I", "cmp x20, #0x80"), ("I", "b.hi {miss}"),', runtime)

    def _release(self, version: str) -> bytes:
        path = NRO[version]
        if not (path and Path(path).is_file()):
            self.skipTest(f"set DBI_{version}_NRO to a pristine DBI {version} NRO")
        return Path(path).read_bytes()

    def _check_release(self, version: str) -> None:
        data = self._release(version)
        v = VERSIONS[version]
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "DBI.nro"
            self.assertEqual(patch_dbi(Path(NRO[version]), out), version)
            patched = out.read_bytes()
        self.assertEqual(len(patched), len(data))
        font = find_embedded_font(bytearray(data))
        font_slot = range(font.offset, font.offset + font.compressed_size)
        sites = {v.reader.addr, v.fmt.addr, v.glog.addr, v.ctor.addr, v.sink.addr, v.bss_end[0]}
        sites.update(v.ctors)
        sites.update(call.addr for call in v.string_calls)
        cave = range(*v.cave)
        changed = [i for i in range(len(data)) if data[i] != patched[i]]
        self.assertTrue(all(i in cave or i in font_slot or any(s <= i < s + 4 for s in sites)
                            for i in changed))
        mod0 = struct.unpack_from("<I", patched, 4)[0]
        bss_end = mod0 + struct.unpack_from("<i", patched, mod0 + 12)[0]
        data_off, data_size, bss_size = struct.unpack_from("<III", patched, 0x30)
        self.assertEqual(bss_end, data_off + data_size + bss_size)

    def test_patch_905_release(self) -> None:
        self._check_release("905")

    def test_patch_912_release(self) -> None:
        self._check_release("912")

    def test_patch_920_release(self) -> None:
        self._check_release("920")

    def test_patch_921_release(self) -> None:
        self._check_release("921")

    def test_state_inside_bss_is_rejected(self) -> None:
        # The first 912 layout put the patcher state on page 0x1278000: inside
        # __bss_end__ (0x1278988), on top of the main thread's TLS string slots.
        data = self._release("912")
        v = dataclasses.replace(VERSIONS["912"], state=0x1278000, persist=0x1278020,
                                scratch=0x1278080)
        with self.assertRaises(PatchError):
            patch_nro(v, data)

    def test_synthetic_font_glyph_repair_and_frame_round_trip(self) -> None:
        """Consolidated success test: verifies 6 glyph changes, copy/mirror, frame discovery, length, and round-trip."""
        raw_font = make_synthetic_font()
        patched_font = patch_cyrillic_glyphs(bytes(raw_font))

        # 1. Exactly the six destination glyphs change
        changed_codepoints = [
            cp
            for cp in range(GLYPH_COUNT)
            if raw_font[cp * GLYPH_SIZE : (cp + 1) * GLYPH_SIZE]
            != patched_font[cp * GLYPH_SIZE : (cp + 1) * GLYPH_SIZE]
        ]
        self.assertEqual(set(changed_codepoints), REPAIRED_GLYPH_CODEPOINTS)
        self.assertEqual(len(changed_codepoints), 6)

        # 2. Copied glyph bytes match sources
        for src_cp, dst_cp in COPIED_GLYPHS:
            src_bytes = raw_font[src_cp * GLYPH_SIZE : (src_cp + 1) * GLYPH_SIZE]
            dst_bytes = patched_font[dst_cp * GLYPH_SIZE : (dst_cp + 1) * GLYPH_SIZE]
            self.assertEqual(dst_bytes, src_bytes)

        # 3. Mirrored glyph rows match bitwise-reversed source rows
        for src_cp, dst_cp in MIRRORED_GLYPHS:
            src_offset = src_cp * GLYPH_SIZE
            dst_offset = dst_cp * GLYPH_SIZE
            for row in range(16):
                src_val = int.from_bytes(raw_font[src_offset + row * 2 : src_offset + row * 2 + 2], "little")
                dst_val = int.from_bytes(patched_font[dst_offset + row * 2 : dst_offset + row * 2 + 2], "little")
                self.assertEqual(dst_val, reverse_16_bits(src_val))

        # 4. Embedded frame discovery and round-trip recompression in NRO
        synthetic_nro = make_synthetic_nro(raw_font)
        initial_length = len(synthetic_nro)

        discovered = find_embedded_font(synthetic_nro)
        self.assertEqual(discovered.raw, bytes(raw_font))
        self.assertTrue(discovered.has_checksum)

        patched_nro = patch_nro_font(synthetic_nro)
        self.assertEqual(len(patched_nro), initial_length, "NRO length must be strictly preserved")

        # 5. Independent round-trip decompression returns patched font and preserved checksum
        verified = find_embedded_font(patched_nro)
        self.assertEqual(verified.raw, patched_font)
        self.assertTrue(verified.has_checksum)

    def test_find_embedded_font_errors(self) -> None:
        """Verify discovery raises ValueError for missing or ambiguous font frames."""
        no_font = bytearray(b"NO_SUPPORTED_FONT_DATA" * 50)
        with self.assertRaises(ValueError) as ctx_missing:
            find_embedded_font(no_font)
        self.assertIn("No supported embedded bitmap font frame found", str(ctx_missing.exception))

        comp = zstandard.ZstdCompressor(level=1, write_checksum=True, write_content_size=True).compress(
            make_synthetic_font()
        )
        ambiguous = bytearray(b"PREFIX" + comp + b"MIDDLE" + comp + b"SUFFIX")
        with self.assertRaises(ValueError) as ctx_ambig:
            find_embedded_font(ambiguous)
        self.assertIn("Embedded bitmap font is ambiguous", str(ctx_ambig.exception))

    def test_patch_nro_font_recompression_overflow(self) -> None:
        """Verify patch_nro_font raises ValueError when recompressed font exceeds the slot."""
        synthetic_nro = make_synthetic_nro()
        with patch.object(
            zstandard.ZstdCompressor,
            "compress",
            side_effect=lambda *args, **kwargs: b"OVERSIZED_COMPRESSED_DATA" * 10000,
        ):
            with self.assertRaises(ValueError) as ctx:
                patch_nro_font(synthetic_nro)
            self.assertIn("does not fit its compressed frame slot", str(ctx.exception))

    def test_patch_nro_font_verification_failure(self) -> None:
        """Verify patch_nro_font raises RuntimeError when round-trip verification fails."""
        synthetic_nro = make_synthetic_nro()
        call_count = 0
        orig_decompress = decompress_font_frame

        def failing_decompress(data, offset):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return None
            return orig_decompress(data, offset)

        with patch("scripts.patch_dbi.decompress_font_frame", side_effect=failing_decompress):
            with self.assertRaises(RuntimeError) as ctx:
                patch_nro_font(synthetic_nro)
            self.assertIn("failed round-trip verification", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
