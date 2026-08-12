#!/usr/bin/env python3
"""Wrapper script to execute pinned upstream DBI 898 assembly patcher.

This script clones BohdanBuinich/dbi-i18n into a temporary directory at an
exact pinned commit, verifies the commit hash, and executes the upstream
patcher CLI against a user-supplied pristine DBI 898 NRO.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM_REPO_URL = "https://github.com/BohdanBuinich/dbi-i18n.git"
PINNED_COMMIT_SHA = "f1f8bebec2b423694e8f058f2d3540a35382b1fd"


def patch_dbi(nro_path: Path, output_path: Path, debug: str = "none") -> None:
    """Clone upstream at pinned SHA and run tools/patch_dbi.py."""
    resolved_nro = nro_path.resolve()
    if not resolved_nro.is_file():
        raise FileNotFoundError(f"Input NRO file not found: {resolved_nro}")

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

        patch_script = temp_repo / "tools" / "patch_dbi.py"
        if not patch_script.is_file():
            raise FileNotFoundError(f"Upstream patch script not found at {patch_script}")

        # Invoke upstream patcher
        subprocess.run(
            [
                sys.executable,
                str(patch_script),
                "--nro",
                str(resolved_nro),
                "--output",
                str(resolved_output),
                "--debug",
                debug,
            ],
            check=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply DBI 898 assembly patches using pinned upstream dbi-i18n tooling."
    )
    parser.add_argument(
        "--nro",
        type=Path,
        required=True,
        help="Path to pristine DBI 898 input file (e.g. DBI.898.ru.nro)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to save patched DBI 898 NRO output file (e.g. DBI.898.ru_patched.nro)",
    )
    parser.add_argument(
        "--debug",
        choices=["none", "file", "console", "both"],
        default="none",
        help="Debug output mode for the upstream patcher (default: none)",
    )
    args = parser.parse_args()

    try:
        patch_dbi(args.nro, args.output, args.debug)
    except FileNotFoundError as err:
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
