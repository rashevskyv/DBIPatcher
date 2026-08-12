from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.patch_dbi import PINNED_COMMIT_SHA, UPSTREAM_REPO_URL, patch_dbi


class PatchDbiWrapperTests(unittest.TestCase):
    """Offline focused tests for scripts/patch_dbi.py."""

    def test_pinned_constants(self) -> None:
        """Verify upstream repository URL and exact SHA commit pinning."""
        self.assertEqual(
            UPSTREAM_REPO_URL,
            "https://github.com/BohdanBuinich/dbi-i18n.git",
        )
        self.assertEqual(
            PINNED_COMMIT_SHA,
            "f1f8bebec2b423694e8f058f2d3540a35382b1fd",
        )

    @patch("scripts.patch_dbi.subprocess.run")
    @patch("scripts.patch_dbi.tempfile.TemporaryDirectory")
    @patch("pathlib.Path.is_file")
    def test_patch_dbi_invokes_upstream_with_expected_args_and_sha(
        self,
        mock_is_file: MagicMock,
        mock_tempdir: MagicMock,
        mock_subproc_run: MagicMock,
    ) -> None:
        """Verify wrapper creates temp clone, checks out pinned SHA, and calls upstream CLI."""
        mock_tempdir.return_value.__enter__.return_value = "/tmp/mock_temp_dir"
        mock_is_file.return_value = True

        rev_parse_result = MagicMock()
        rev_parse_result.stdout = f"{PINNED_COMMIT_SHA}\n"
        mock_subproc_run.side_effect = [
            MagicMock(returncode=0),  # git clone
            MagicMock(returncode=0),  # git checkout
            rev_parse_result,         # git rev-parse HEAD
            MagicMock(returncode=0),  # python tools/patch_dbi.py
        ]

        with tempfile.TemporaryDirectory() as td:
            dummy_nro = Path(td) / "DBI.898.ru.nro"
            dummy_output = Path(td) / "out" / "DBI.898.ru_patched.nro"

            patch_dbi(dummy_nro, dummy_output, debug="file")

            # Verify git clone
            mock_subproc_run.assert_has_calls(
                [
                    call(
                        ["git", "clone", UPSTREAM_REPO_URL, "/tmp/mock_temp_dir"],
                        check=True,
                    ),
                    call(
                        ["git", "checkout", "--detach", PINNED_COMMIT_SHA],
                        cwd="/tmp/mock_temp_dir",
                        check=True,
                    ),
                    call(
                        ["git", "rev-parse", "HEAD"],
                        cwd="/tmp/mock_temp_dir",
                        capture_output=True,
                        text=True,
                        check=True,
                    ),
                    call(
                        [
                            sys.executable,
                            str(Path("/tmp/mock_temp_dir") / "tools" / "patch_dbi.py"),
                            "--nro",
                            str(dummy_nro.resolve()),
                            "--output",
                            str(dummy_output.resolve()),
                            "--debug",
                            "file",
                        ],
                        check=True,
                    ),
                ]
            )
            self.assertTrue(dummy_output.parent.is_dir())

    def test_nonexistent_nro_raises_file_not_found(self) -> None:
        """Verify FileNotFoundError is raised when input NRO does not exist."""
        with tempfile.TemporaryDirectory() as td:
            nonexistent = Path(td) / "nonexistent" / "DBI.nro"
            dummy_output = Path(td) / "out" / "DBI.898.ru_patched.nro"
            with self.assertRaises(FileNotFoundError):
                patch_dbi(nonexistent, dummy_output)

    @patch("scripts.patch_dbi.subprocess.run")
    @patch("scripts.patch_dbi.tempfile.TemporaryDirectory")
    @patch("pathlib.Path.is_file")
    def test_sha_mismatch_raises_runtime_error(
        self,
        mock_is_file: MagicMock,
        mock_tempdir: MagicMock,
        mock_subproc_run: MagicMock,
    ) -> None:
        """Verify RuntimeError is raised when checked out commit differs from pinned SHA."""
        mock_tempdir.return_value.__enter__.return_value = "/tmp/mock_temp_dir"
        mock_is_file.return_value = True

        rev_parse_result = MagicMock()
        rev_parse_result.stdout = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n"
        mock_subproc_run.side_effect = [
            MagicMock(returncode=0),  # git clone
            MagicMock(returncode=0),  # git checkout
            rev_parse_result,         # git rev-parse HEAD
        ]

        with tempfile.TemporaryDirectory() as td:
            dummy_nro = Path(td) / "DBI.898.ru.nro"
            dummy_output = Path(td) / "out" / "DBI.898.ru_patched.nro"

            with self.assertRaises(RuntimeError) as ctx:
                patch_dbi(dummy_nro, dummy_output)
            self.assertIn("Checkout verification failed", str(ctx.exception))

    @patch("scripts.patch_dbi.subprocess.run")
    @patch("scripts.patch_dbi.tempfile.TemporaryDirectory")
    @patch("pathlib.Path.is_file")
    def test_subprocess_failure_propagates(
        self,
        mock_is_file: MagicMock,
        mock_tempdir: MagicMock,
        mock_subproc_run: MagicMock,
    ) -> None:
        """Verify subprocess.CalledProcessError propagates on failure."""
        mock_tempdir.return_value.__enter__.return_value = "/tmp/mock_temp_dir"
        mock_is_file.return_value = True

        mock_subproc_run.side_effect = subprocess.CalledProcessError(
            returncode=128, cmd=["git", "clone"]
        )

        with tempfile.TemporaryDirectory() as td:
            dummy_nro = Path(td) / "DBI.898.ru.nro"
            dummy_output = Path(td) / "out" / "DBI.898.ru_patched.nro"

            with self.assertRaises(subprocess.CalledProcessError):
                patch_dbi(dummy_nro, dummy_output)


if __name__ == "__main__":
    unittest.main()
