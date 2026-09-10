import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.errors import ExportError
from src.main import (
    DEFAULT_MIN_TRANSLATION_SIZE,
    MIN_CORRUPT_THRESHOLD,
    get_translation_size_threshold,
    verify_and_regenerate_translation,
    verify_remote_release_assets,
)


class TranslationSizeCheckTests(unittest.TestCase):
    def test_threshold_calculation_from_binaries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            # Create a small/corrupt file (50 KB)
            (p / "translation_corrupt.bin").write_bytes(b"x" * (50 * 1024))
            # Create valid binaries: 600 KB and 800 KB
            (p / "translation_a.bin").write_bytes(b"x" * 600_000)
            (p / "translation_b.bin").write_bytes(b"x" * 800_000)

            # Threshold should ignore 50 KB (< 100 KB), take min(600_000, 800_000) // 2 = 300_000
            threshold = get_translation_size_threshold(search_dirs=[p])
            self.assertEqual(threshold, 300_000)

    def test_threshold_fallback_when_no_valid_binaries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            # Only corrupt files (< 100 KB)
            (p / "translation_bad.bin").write_bytes(b"x" * 1024)

            threshold = get_translation_size_threshold(search_dirs=[p])
            self.assertEqual(threshold, DEFAULT_MIN_TRANSLATION_SIZE)

    def test_verify_and_regenerate_skips_valid_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            bin_path = p / "translation_en.bin"
            bin_path.write_bytes(b"x" * 500_000)

            with patch("src.main.regenerate_translation_bin") as mock_regen:
                out_path, sz = verify_and_regenerate_translation("en", bin_path, min_threshold=300_000)
                self.assertEqual(sz, 500_000)
                mock_regen.assert_not_called()

    def test_verify_and_regenerate_triggers_on_undersized(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            bin_path = p / "translation_en.bin"
            # Initially undersized (2 KB)
            bin_path.write_bytes(b"x" * 2048)

            def fake_regen(lc):
                # Regenerate to 400 KB
                bin_path.write_bytes(b"x" * 400_000)
                return bin_path

            with patch("src.main.regenerate_translation_bin", side_effect=fake_regen) as mock_regen:
                out_path, sz = verify_and_regenerate_translation("en", bin_path, min_threshold=300_000)
                mock_regen.assert_called_once_with("en")
                self.assertEqual(sz, 400_000)

    def test_verify_and_regenerate_raises_if_still_undersized(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            bin_path = p / "translation_en.bin"
            bin_path.write_bytes(b"x" * 2048)

            def fake_regen(lc):
                # Still undersized
                bin_path.write_bytes(b"x" * 4096)
                return bin_path

            with patch("src.main.regenerate_translation_bin", side_effect=fake_regen):
                with self.assertRaises(ExportError) as ctx:
                    verify_and_regenerate_translation("en", bin_path, min_threshold=300_000)
                self.assertIn("remains below minimum threshold", str(ctx.exception))

    def test_verify_remote_release_assets_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            local_bin = p / "translation_en.bin"
            local_bin.write_bytes(b"x" * 500_000)

            mock_gh_output = {
                "assets": [
                    {"name": "translation_en.bin", "size": 500_000}
                ]
            }

            fake_proc = MagicMock()
            fake_proc.returncode = 0
            fake_proc.stdout = json.dumps(mock_gh_output)

            with patch("subprocess.run", return_value=fake_proc):
                # Should not raise
                verify_remote_release_assets("905", [local_bin], min_threshold=300_000)

    def test_verify_remote_release_assets_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            local_bin = p / "translation_en.bin"
            local_bin.write_bytes(b"x" * 500_000)

            mock_gh_output = {
                "assets": [
                    {"name": "translation_en.bin", "size": 2672}
                ]
            }

            fake_proc = MagicMock()
            fake_proc.returncode = 0
            fake_proc.stdout = json.dumps(mock_gh_output)

            with patch("subprocess.run", return_value=fake_proc):
                with self.assertRaises(ExportError) as ctx:
                    verify_remote_release_assets("905", [local_bin], min_threshold=300_000)
                self.assertIn("failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
