from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.patch_dbi import (
    EXPECTED_DBI_SHA256,
    PINNED_COMMIT_SHA,
    TARGET_DBI_VERSION,
    UPSTREAM_REPO_URL,
    compute_sha256,
    patch_dbi,
    verify_nro_sha256,
)


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

    @patch("scripts.patch_dbi.compute_sha256")
    @patch("scripts.patch_dbi.subprocess.run")
    @patch("scripts.patch_dbi.tempfile.TemporaryDirectory")
    @patch("pathlib.Path.is_file")
    def test_patch_dbi_invokes_upstream_with_expected_args_and_sha(
        self,
        mock_is_file: MagicMock,
        mock_tempdir: MagicMock,
        mock_subproc_run: MagicMock,
        mock_compute_sha256: MagicMock,
    ) -> None:
        """Verify wrapper validates SHA-256, creates temp clone, checks out pinned SHA, and calls upstream CLI."""
        mock_temp_path = str(Path("/tmp/mock_temp_dir"))
        mock_tempdir.return_value.__enter__.return_value = mock_temp_path
        mock_is_file.return_value = True
        mock_compute_sha256.return_value = EXPECTED_DBI_SHA256

        rev_parse_result = MagicMock()
        rev_parse_result.stdout = f"{PINNED_COMMIT_SHA}\n"
        mock_subproc_run.side_effect = [
            MagicMock(returncode=0),  # git clone
            MagicMock(returncode=0),  # git checkout
            rev_parse_result,         # git rev-parse HEAD
            MagicMock(returncode=0),  # python -m dbi_translate.cli patch
        ]

        with tempfile.TemporaryDirectory() as td:
            dummy_nro = Path(td) / "DBI.905.ru.nro"
            dummy_output = Path(td) / "out" / "DBI.905.ru_patched.nro"

            patch_dbi(dummy_nro, dummy_output)

            # Verify compute_sha256 called with resolved input NRO
            mock_compute_sha256.assert_called_once_with(dummy_nro.resolve())

            # Expected environment with PYTHONPATH containing temp clone's src directory
            expected_src_dir = str(Path(mock_temp_path) / "src")

            # Verify subprocess call sequence
            self.assertEqual(mock_subproc_run.call_count, 4)

            # Call 1: git clone
            c1 = mock_subproc_run.call_args_list[0]
            self.assertEqual(
                c1,
                call(["git", "clone", UPSTREAM_REPO_URL, mock_temp_path], check=True),
            )

            # Call 2: git checkout
            c2 = mock_subproc_run.call_args_list[1]
            self.assertEqual(
                c2,
                call(
                    ["git", "checkout", "--detach", PINNED_COMMIT_SHA],
                    cwd=mock_temp_path,
                    check=True,
                ),
            )

            # Call 3: git rev-parse HEAD
            c3 = mock_subproc_run.call_args_list[2]
            self.assertEqual(
                c3,
                call(
                    ["git", "rev-parse", "HEAD"],
                    cwd=mock_temp_path,
                    capture_output=True,
                    text=True,
                    check=True,
                ),
            )

            # Call 4: dbi_translate.cli patch
            c4 = mock_subproc_run.call_args_list[3]
            cmd_args, cmd_kwargs = c4
            self.assertEqual(
                cmd_args[0],
                [
                    sys.executable,
                    "-m",
                    "dbi_translate.cli",
                    "patch",
                    "--nro",
                    str(dummy_nro.resolve()),
                    "--output",
                    str(dummy_output.resolve()),
                    "--version",
                    "905",
                ],
            )
            self.assertEqual(cmd_kwargs["cwd"], mock_temp_path)
            self.assertTrue(cmd_kwargs["check"])
            self.assertIn("PYTHONPATH", cmd_kwargs["env"])
            self.assertTrue(cmd_kwargs["env"]["PYTHONPATH"].startswith(expected_src_dir))

            # Verify output parent directory created
            self.assertTrue(dummy_output.parent.is_dir())

    def test_nonexistent_nro_raises_file_not_found(self) -> None:
        """Verify FileNotFoundError is raised when input NRO does not exist."""
        with tempfile.TemporaryDirectory() as td:
            nonexistent = Path(td) / "nonexistent" / "DBI.905.ru.nro"
            dummy_output = Path(td) / "out" / "DBI.905.ru_patched.nro"
            with self.assertRaises(FileNotFoundError):
                patch_dbi(nonexistent, dummy_output)

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

            # Error must state expected and actual digest
            err_msg = str(ctx.exception)
            self.assertIn("Invalid NRO SHA-256", err_msg)
            self.assertIn(EXPECTED_DBI_SHA256, err_msg)
            actual_digest = compute_sha256(dummy_nro)
            self.assertIn(actual_digest, err_msg)

            # Ensure git clone was never called
            mock_subproc_run.assert_not_called()

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
            MagicMock(returncode=0),  # git clone
            MagicMock(returncode=0),  # git checkout
            rev_parse_result,         # git rev-parse HEAD
        ]

        with tempfile.TemporaryDirectory() as td:
            dummy_nro = Path(td) / "DBI.905.ru.nro"
            dummy_output = Path(td) / "out" / "DBI.905.ru_patched.nro"

            with self.assertRaises(RuntimeError) as ctx:
                patch_dbi(dummy_nro, dummy_output)
            self.assertIn("Checkout verification failed", str(ctx.exception))

    def test_signature_has_no_version_parameter(self) -> None:
        """Verify patch_dbi only accepts nro_path and output_path (no public version override)."""
        import inspect

        sig = inspect.signature(patch_dbi)
        params = list(sig.parameters.keys())
        self.assertEqual(params, ["nro_path", "output_path"])

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


if __name__ == "__main__":
    unittest.main()
