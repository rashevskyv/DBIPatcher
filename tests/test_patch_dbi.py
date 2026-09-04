from __future__ import annotations

import inspect
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import zstandard

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.patch_dbi import (
    COPIED_GLYPHS,
    EXPECTED_DBI_SHA256,
    FONT_SIZE,
    GLYPH_COUNT,
    GLYPH_SIZE,
    MIRRORED_GLYPHS,
    PINNED_COMMIT_SHA,
    REPAIRED_GLYPH_CODEPOINTS,
    TARGET_DBI_VERSION,
    UPSTREAM_REPO_URL,
    compute_sha256,
    decompress_font_frame,
    find_embedded_font,
    patch_cyrillic_glyphs,
    patch_dbi,
    patch_nro_font,
    reverse_16_bits,
)


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

    def test_pinned_constants(self) -> None:
        """Verify upstream repository URL, pinned commit SHA, expected SHA-256, and DBI version."""
        self.assertEqual(
            UPSTREAM_REPO_URL,
            "https://github.com/0xroast/dbi-translate.git",
        )
        self.assertEqual(
            PINNED_COMMIT_SHA,
            "1320e138fd017db70c1436b537aef7be030f0668",
        )
        self.assertEqual(
            EXPECTED_DBI_SHA256,
            "f4360db14ea7ed1043a5a0c7d076d4861cc3383f3b254b9b38d2eec6d175686f",
        )
        self.assertEqual(
            TARGET_DBI_VERSION,
            "905",
        )

    def test_signature_has_no_version_parameter(self) -> None:
        """Verify patch_dbi only accepts nro_path and output_path (no public version override)."""
        sig = inspect.signature(patch_dbi)
        params = list(sig.parameters.keys())
        self.assertEqual(params, ["nro_path", "output_path"])

    def test_nonexistent_nro_raises_file_not_found(self) -> None:
        """Verify FileNotFoundError is raised when input NRO does not exist."""
        with tempfile.TemporaryDirectory() as td:
            nonexistent = Path(td) / "nonexistent" / "DBI.905.ru.nro"
            dummy_output = Path(td) / "out" / "DBI.905.ru_patched.nro"
            with self.assertRaises(FileNotFoundError):
                patch_dbi(nonexistent, dummy_output)
            self.assertFalse(dummy_output.exists())

    @patch("scripts.patch_dbi.subprocess.run")
    def test_sha256_mismatch_rejects_before_clone(
        self,
        mock_subproc_run: MagicMock,
    ) -> None:
        """Verify digest mismatch raises ValueError and aborts before any clone operation."""
        with tempfile.TemporaryDirectory() as td:
            dummy_nro = Path(td) / "DBI.905.ru.nro"
            dummy_nro.write_bytes(b"tampered or non-905 NRO binary data")
            dummy_output = Path(td) / "out" / "DBI.905.ru_patched.nro"

            with self.assertRaises(ValueError) as ctx:
                patch_dbi(dummy_nro, dummy_output)

            err_msg = str(ctx.exception)
            self.assertIn("Invalid NRO SHA-256", err_msg)
            self.assertIn(EXPECTED_DBI_SHA256, err_msg)
            actual_digest = compute_sha256(dummy_nro)
            self.assertIn(actual_digest, err_msg)

            mock_subproc_run.assert_not_called()
            self.assertFalse(dummy_output.exists())

    @patch("scripts.patch_dbi.compute_sha256")
    @patch("scripts.patch_dbi.subprocess.run")
    @patch("pathlib.Path.is_file")
    def test_same_input_and_output_path_raises_value_error_before_clone(
        self,
        mock_is_file: MagicMock,
        mock_subproc_run: MagicMock,
        mock_compute_sha256: MagicMock,
    ) -> None:
        """Verify identical input and output paths raise ValueError before cloning or patching."""
        mock_is_file.return_value = True
        mock_compute_sha256.return_value = EXPECTED_DBI_SHA256

        with tempfile.TemporaryDirectory() as td:
            dummy_nro = Path(td) / "DBI.905.ru.nro"
            dummy_output = Path(td) / "DBI.905.ru.nro"

            with self.assertRaises(ValueError) as ctx:
                patch_dbi(dummy_nro, dummy_output)

            self.assertIn("Output path cannot be identical to input NRO path", str(ctx.exception))
            mock_subproc_run.assert_not_called()

    @patch("scripts.patch_dbi.compute_sha256")
    @patch("scripts.patch_dbi.subprocess.run")
    @patch("scripts.patch_dbi.tempfile.TemporaryDirectory")
    @patch("pathlib.Path.is_file")
    def test_sha_mismatch_raises_runtime_error(
        self,
        mock_is_file: MagicMock,
        mock_tempdir: MagicMock,
        mock_subproc_run: MagicMock,
        mock_compute_sha256: MagicMock,
    ) -> None:
        """Verify RuntimeError is raised when checked out commit differs from pinned SHA."""
        mock_tempdir.return_value.__enter__.return_value = "/tmp/mock_temp_dir"
        mock_is_file.return_value = True
        mock_compute_sha256.return_value = EXPECTED_DBI_SHA256

        rev_parse_result = MagicMock()
        rev_parse_result.stdout = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n"
        mock_subproc_run.side_effect = [
            MagicMock(returncode=0),  # git clone --no-checkout
            MagicMock(returncode=0),  # git fetch pinned SHA
            MagicMock(returncode=0),  # git checkout
            rev_parse_result,         # git rev-parse HEAD
        ]

        with tempfile.TemporaryDirectory() as td:
            dummy_nro = Path(td) / "DBI.905.ru.nro"
            dummy_output = Path(td) / "out" / "DBI.905.ru_patched.nro"

            with self.assertRaises(RuntimeError) as ctx:
                patch_dbi(dummy_nro, dummy_output)
            self.assertIn("Checkout verification failed", str(ctx.exception))
            self.assertFalse(dummy_output.exists())

    @patch("scripts.patch_dbi.compute_sha256")
    @patch("scripts.patch_dbi.subprocess.run")
    @patch("scripts.patch_dbi.tempfile.TemporaryDirectory")
    @patch("pathlib.Path.is_file")
    def test_subprocess_failure_propagates(
        self,
        mock_is_file: MagicMock,
        mock_tempdir: MagicMock,
        mock_subproc_run: MagicMock,
        mock_compute_sha256: MagicMock,
    ) -> None:
        """Verify subprocess.CalledProcessError propagates on failure."""
        mock_tempdir.return_value.__enter__.return_value = "/tmp/mock_temp_dir"
        mock_is_file.return_value = True
        mock_compute_sha256.return_value = EXPECTED_DBI_SHA256

        mock_subproc_run.side_effect = subprocess.CalledProcessError(
            returncode=128, cmd=["git", "clone"]
        )

        with tempfile.TemporaryDirectory() as td:
            dummy_nro = Path(td) / "DBI.905.ru.nro"
            dummy_output = Path(td) / "out" / "DBI.905.ru_patched.nro"

            with self.assertRaises(subprocess.CalledProcessError):
                patch_dbi(dummy_nro, dummy_output)
            self.assertFalse(dummy_output.exists())

    @patch("scripts.patch_dbi.compute_sha256")
    @patch("scripts.patch_dbi.subprocess.run")
    @patch("scripts.patch_dbi.tempfile.TemporaryDirectory")
    @patch("pathlib.Path.is_file")
    def test_patch_dbi_invokes_upstream_intermediate_then_writes_patched_output(
        self,
        mock_is_file: MagicMock,
        mock_tempdir: MagicMock,
        mock_subproc_run: MagicMock,
        mock_compute_sha256: MagicMock,
    ) -> None:
        """Verify wrapper calls upstream CLI with intermediate path, then font patches before writing output."""
        with tempfile.TemporaryDirectory() as td:
            mock_temp_path = Path(td) / "work"
            mock_temp_path.mkdir(parents=True, exist_ok=True)
            mock_tempdir.return_value.__enter__.return_value = str(mock_temp_path)
            mock_is_file.return_value = True
            mock_compute_sha256.return_value = EXPECTED_DBI_SHA256

            rev_parse_result = MagicMock()
            rev_parse_result.stdout = f"{PINNED_COMMIT_SHA}\n"

            intermediate_file = mock_temp_path / "intermediate.nro"
            synthetic_nro = make_synthetic_nro()

            def fake_subprocess_run(cmd, *args, **kwargs):
                if isinstance(cmd, list) and "-m" in cmd and "dbi_translate.cli" in cmd:
                    intermediate_file.write_bytes(synthetic_nro)
                    return MagicMock(returncode=0)
                if isinstance(cmd, list) and "rev-parse" in cmd:
                    return rev_parse_result
                return MagicMock(returncode=0)

            mock_subproc_run.side_effect = fake_subprocess_run

            dummy_nro = Path(td) / "DBI.905.ru.nro"
            dummy_output = Path(td) / "out" / "DBI.905.ru_patched.nro"

            patch_dbi(dummy_nro, dummy_output)

            # Subprocess calls: clone, fetch, checkout, rev-parse, CLI patch
            self.assertEqual(mock_subproc_run.call_count, 5)

            # Call 5 passed intermediate_file as --output, not dummy_output
            c5_args = mock_subproc_run.call_args_list[4][0][0]
            self.assertEqual(
                c5_args,
                [
                    sys.executable,
                    "-m",
                    "dbi_translate.cli",
                    "patch",
                    "--nro",
                    str(dummy_nro.resolve()),
                    "--output",
                    str(intermediate_file),
                    "--version",
                    "905",
                ],
            )

            # Final output was written with patched font
            self.assertTrue(dummy_output.is_file())
            patched_frame = find_embedded_font(dummy_output.read_bytes())
            self.assertEqual(
                patched_frame.raw[0x0406 * GLYPH_SIZE : 0x0406 * GLYPH_SIZE + 32],
                patched_frame.raw[0x0049 * GLYPH_SIZE : 0x0049 * GLYPH_SIZE + 32],
            )

    @patch("scripts.patch_dbi.compute_sha256")
    @patch("scripts.patch_dbi.subprocess.run")
    @patch("scripts.patch_dbi.tempfile.TemporaryDirectory")
    @patch("pathlib.Path.is_file")
    @patch("scripts.patch_dbi.patch_nro_font")
    def test_patch_dbi_aborts_without_writing_output_when_font_stage_fails(
        self,
        mock_patch_nro_font: MagicMock,
        mock_is_file: MagicMock,
        mock_tempdir: MagicMock,
        mock_subproc_run: MagicMock,
        mock_compute_sha256: MagicMock,
    ) -> None:
        """Verify that any failure in the font stage aborts and leaves output unwritten."""
        with tempfile.TemporaryDirectory() as td:
            mock_temp_path = Path(td) / "work"
            mock_temp_path.mkdir(parents=True, exist_ok=True)
            mock_tempdir.return_value.__enter__.return_value = str(mock_temp_path)
            mock_is_file.return_value = True
            mock_compute_sha256.return_value = EXPECTED_DBI_SHA256

            intermediate_file = mock_temp_path / "intermediate.nro"
            intermediate_file.write_bytes(b"INTERMEDIATE_NRO_BYTES")

            rev_parse_result = MagicMock()
            rev_parse_result.stdout = f"{PINNED_COMMIT_SHA}\n"
            mock_subproc_run.side_effect = [
                MagicMock(returncode=0),  # clone
                MagicMock(returncode=0),  # fetch
                MagicMock(returncode=0),  # checkout
                rev_parse_result,         # rev-parse
                MagicMock(returncode=0),  # patch CLI
            ]

            mock_patch_nro_font.side_effect = ValueError("Font repair failed")

            dummy_nro = Path(td) / "DBI.905.ru.nro"
            dummy_output = Path(td) / "out" / "DBI.905.ru_patched.nro"

            with self.assertRaises(ValueError) as ctx:
                patch_dbi(dummy_nro, dummy_output)

            self.assertIn("Font repair failed", str(ctx.exception))
            self.assertFalse(dummy_output.exists(), "Final output must not be created on font stage failure")

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
