#!/usr/bin/env python3
"""Wrapper script to execute pinned upstream DBI 905 assembly patcher.

This script clones 0xroast/dbi-translate into a temporary directory at an
exact pinned commit, verifies the commit hash, and executes the upstream
patcher CLI against a user-supplied pristine DBI 905 NRO.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM_REPO_URL = "https://github.com/0xroast/dbi-translate.git"
PINNED_COMMIT_SHA = "1320e138fd017db70c1436b537aef7be030f0668"
EXPECTED_DBI_SHA256 = "f4360db14ea7ed1043a5a0c7d076d4861cc3383f3b254b9b38d2eec6d175686f"
TARGET_DBI_VERSION = "905"


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 digest of a file in chunks."""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_nro_sha256(nro_path: Path) -> None:
    """Verify input NRO file matches the expected pristine DBI 905 release SHA-256."""
    actual_sha = compute_sha256(nro_path)
    if actual_sha.lower() != EXPECTED_DBI_SHA256.lower():
        raise ValueError(
            f"Invalid NRO SHA-256 for DBI {TARGET_DBI_VERSION}:\n"
            f"  Expected: {EXPECTED_DBI_SHA256}\n"
            f"  Actual:   {actual_sha}"
        )


def patch_dbi(
    nro_path: Path,
    output_path: Path,
) -> None:
    """Clone upstream at pinned SHA and run dbi_translate.cli patch command."""
    resolved_nro = nro_path.resolve()
    if not resolved_nro.is_file():
        raise FileNotFoundError(f"Input NRO file not found: {resolved_nro}")

    verify_nro_sha256(resolved_nro)

    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="dbi_patch_") as temp_dir:
        temp_repo = Path(temp_dir)

        # Clone upstream repository
        subprocess.run(
            ["git", "clone", UPSTREAM_REPO_URL, str(temp_repo)],
            check=True,
        )

        # Detach and check out exact pinned commit
        subprocess.run(
            ["git", "checkout", "--detach", PINNED_COMMIT_SHA],
            cwd=str(temp_repo),
            check=True,
        )

        # Verify HEAD matches pinned SHA
        verify_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(temp_repo),
            capture_output=True,
            text=True,
            check=True,
        )
        current_sha = verify_proc.stdout.strip()
        if current_sha != PINNED_COMMIT_SHA:
            raise RuntimeError(
                f"Checkout verification failed: expected {PINNED_COMMIT_SHA}, got {current_sha}"
            )

        # Execute upstream patch CLI with temporary clone's src directory in PYTHONPATH
        env = os.environ.copy()
        src_dir = str(temp_repo / "src")
        env["PYTHONPATH"] = (
            f"{src_dir}{os.pathsep}{env['PYTHONPATH']}"
            if "PYTHONPATH" in env and env["PYTHONPATH"]
            else src_dir
        )

        subprocess.run(
            [
                sys.executable,
                "-m",
                "dbi_translate.cli",
                "patch",
                "--nro",
                str(resolved_nro),
                "--output",
                str(resolved_output),
                "--version",
                TARGET_DBI_VERSION,
            ],
            cwd=str(temp_repo),
            env=env,
            check=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply DBI 905 assembly patches using pinned upstream dbi-translate tooling."
    )
    parser.add_argument(
        "--nro",
        type=Path,
        required=True,
        help="Path to pristine DBI 905 input file (e.g. DBI.905.ru.nro)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to save patched DBI 905 NRO output file (e.g. DBI.905.ru_patched.nro)",
    )
    args = parser.parse_args()

    try:
        patch_dbi(args.nro, args.output)
    except FileNotFoundError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as err:
        print(f"Subprocess failed with exit code {err.returncode}: {err}", file=sys.stderr)
        return err.returncode or 1
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    print(f"Successfully patched DBI NRO -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
