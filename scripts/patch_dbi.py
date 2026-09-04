#!/usr/bin/env python3
"""Wrapper script to execute pinned upstream DBI 905 assembly patcher and repair Cyrillic font glyphs.

This script clones 0xroast/dbi-translate into a temporary directory at an
exact pinned commit, verifies the commit hash, executes the upstream
patcher CLI against a user-supplied pristine DBI 905 NRO into an intermediate
binary, and applies in-memory Cyrillic glyph repairs to the embedded bitmap font
before writing the final shared patched NRO.

Cyrillic font-glyph repair logic is adapted from Bohdan Buinich's dbi-i18n
reference implementation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import zstandard

UPSTREAM_REPO_URL = "https://github.com/0xroast/dbi-translate.git"
PINNED_COMMIT_SHA = "1320e138fd017db70c1436b537aef7be030f0668"
EXPECTED_DBI_SHA256 = "f4360db14ea7ed1043a5a0c7d076d4861cc3383f3b254b9b38d2eec6d175686f"
TARGET_DBI_VERSION = "905"

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
GLYPH_SIZE = 32
GLYPH_COUNT = 65536
FONT_SIZE = GLYPH_SIZE * GLYPH_COUNT  # 2,097,152 bytes
FONT_COMPRESSION_LEVEL = 18

MIRRORED_GLYPHS = (
    (0x042D, 0x0404),  # Cyrillic capital E (Э) -> Ukrainian capital Ye (Є)
    (0x044D, 0x0454),  # Cyrillic small e (э) -> Ukrainian small ye (є)
)
COPIED_GLYPHS = (
    (0x0049, 0x0406),  # Latin capital I -> Ukrainian/Belarusian/Kazakh capital I (І)
    (0x0069, 0x0456),  # Latin small i -> Ukrainian/Belarusian/Kazakh small i (і)
    (0x00CF, 0x0407),  # Latin capital I with diaeresis (Ï) -> Ukrainian capital Yi (Ї)
    (0x00EF, 0x0457),  # Latin small i with diaeresis (ï) -> Ukrainian small yi (ї)
)
REPAIRED_GLYPH_CODEPOINTS = frozenset(dst for _, dst in MIRRORED_GLYPHS + COPIED_GLYPHS)


@dataclass(frozen=True, slots=True)
class EmbeddedFontFrame:
    """One embedded Zstandard frame containing a 2 MiB DBI bitmap font."""

    offset: int
    compressed_size: int
    raw: bytes
    has_checksum: bool


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


def reverse_16_bits(value: int) -> int:
    """Reverse bits of a 16-bit unsigned integer (for horizontal mirroring)."""
    value = ((value & 0x5555) << 1) | ((value >> 1) & 0x5555)
    value = ((value & 0x3333) << 2) | ((value >> 2) & 0x3333)
    value = ((value & 0x0F0F) << 4) | ((value >> 4) & 0x0F0F)
    return ((value & 0x00FF) << 8) | ((value >> 8) & 0x00FF)


def copy_mirrored_glyph(font: bytearray, source_cp: int, destination_cp: int) -> None:
    """Copy a 16x16 glyph while mirroring each little-endian 16-bit bitmap row."""
    src_offset = source_cp * GLYPH_SIZE
    dst_offset = destination_cp * GLYPH_SIZE
    for row in range(16):
        src_row = src_offset + row * 2
        dst_row = dst_offset + row * 2
        val = int.from_bytes(font[src_row : src_row + 2], "little")
        font[dst_row : dst_row + 2] = reverse_16_bits(val).to_bytes(2, "little")


def copy_glyph(font: bytearray, source_cp: int, destination_cp: int) -> None:
    """Copy one 32-byte glyph slot to another."""
    src_offset = source_cp * GLYPH_SIZE
    dst_offset = destination_cp * GLYPH_SIZE
    font[dst_offset : dst_offset + GLYPH_SIZE] = font[src_offset : src_offset + GLYPH_SIZE]


def patch_cyrillic_glyphs(font_bytes: bytes) -> bytes:
    """Derive repaired Cyrillic glyphs in the 2 MiB bitmap font."""
    if len(font_bytes) != FONT_SIZE:
        raise ValueError(f"Unexpected bitmap font size: {len(font_bytes)} (expected {FONT_SIZE})")

    font = bytearray(font_bytes)
    for src, dst in MIRRORED_GLYPHS:
        copy_mirrored_glyph(font, src, dst)
    for src, dst in COPIED_GLYPHS:
        copy_glyph(font, src, dst)
    return bytes(font)


def decompress_font_frame(data: bytes | bytearray, offset: int) -> EmbeddedFontFrame | None:
    """Attempt to decompress a Zstandard frame at offset and check for supported 2 MiB font."""
    source = bytes(data[offset:])
    try:
        decompressor = zstandard.ZstdDecompressor().decompressobj()
        raw = decompressor.decompress(source)
        if not decompressor.eof or len(raw) != FONT_SIZE:
            return None
        parameters = zstandard.get_frame_parameters(source)
    except zstandard.ZstdError:
        return None

    compressed_size = len(source) - len(decompressor.unused_data)
    return EmbeddedFontFrame(
        offset=offset,
        compressed_size=compressed_size,
        raw=raw,
        has_checksum=bool(parameters.has_checksum),
    )


def find_embedded_font(data: bytes | bytearray) -> EmbeddedFontFrame:
    """Find the single supported Zstandard bitmap font frame in the NRO binary."""
    matches: list[EmbeddedFontFrame] = []
    start = 0
    while True:
        offset = data.find(ZSTD_MAGIC, start)
        if offset < 0:
            break
        frame = decompress_font_frame(data, offset)
        if frame is not None:
            matches.append(frame)
        start = offset + 1

    if not matches:
        raise ValueError("No supported embedded bitmap font frame found in NRO")
    if len(matches) > 1:
        offsets_str = ", ".join(f"0x{m.offset:X}" for m in matches)
        raise ValueError(
            f"Embedded bitmap font is ambiguous: found {len(matches)} matching frames at {offsets_str}"
        )
    return matches[0]


def patch_nro_font(nro_data: bytearray) -> bytearray:
    """Discover, patch Cyrillic glyphs, recompress, and verify the embedded font in memory."""
    frame = find_embedded_font(nro_data)
    patched_font = patch_cyrillic_glyphs(frame.raw)

    compressor = zstandard.ZstdCompressor(
        level=FONT_COMPRESSION_LEVEL,
        write_checksum=frame.has_checksum,
        write_content_size=True,
    )
    compressed = compressor.compress(patched_font)

    if len(compressed) > frame.compressed_size:
        raise ValueError(
            f"Patched font does not fit its compressed frame slot: "
            f"{len(compressed)} > {frame.compressed_size} bytes"
        )

    # In-place replacement within the original frame slot; untouched tail is preserved
    start = frame.offset
    nro_data[start : start + len(compressed)] = compressed

    # Verification: independent decompression of consumed bytes
    verified_frame = decompress_font_frame(nro_data, start)
    if verified_frame is None or verified_frame.raw != patched_font:
        raise RuntimeError("Repacked font failed round-trip verification")

    return nro_data


def patch_dbi(
    nro_path: Path,
    output_path: Path,
) -> None:
    """Clone upstream at pinned SHA, run runtime patcher into intermediate NRO, and repair font in memory."""
    resolved_nro = nro_path.resolve()
    if not resolved_nro.is_file():
        raise FileNotFoundError(f"Input NRO file not found: {resolved_nro}")

    verify_nro_sha256(resolved_nro)

    resolved_output = output_path.resolve()
    if resolved_nro == resolved_output:
        raise ValueError(
            f"Output path cannot be identical to input NRO path: {resolved_output}"
        )

    resolved_output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="dbi_patch_") as temp_dir:
        temp_repo = Path(temp_dir)

        # Clone the current repository metadata, then explicitly fetch the pinned
        # commit. The pin may no longer be reachable from the upstream default ref.
        subprocess.run(
            ["git", "clone", "--no-checkout", UPSTREAM_REPO_URL, str(temp_repo)],
            check=True,
        )

        subprocess.run(
            ["git", "fetch", "--no-tags", "origin", PINNED_COMMIT_SHA],
            cwd=str(temp_repo),
            check=True,
        )

        # Detach and check out exact pinned commit.
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

        intermediate_nro = Path(temp_dir) / "intermediate.nro"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "dbi_translate.cli",
                "patch",
                "--nro",
                str(resolved_nro),
                "--output",
                str(intermediate_nro),
                "--version",
                TARGET_DBI_VERSION,
            ],
            cwd=str(temp_repo),
            env=env,
            check=True,
        )

        intermediate_data = bytearray(intermediate_nro.read_bytes())
        initial_len = len(intermediate_data)

        # Apply Cyrillic glyph repair and verify in memory before writing output
        patched_data = patch_nro_font(intermediate_data)
        if len(patched_data) != initial_len:
            raise RuntimeError(
                f"Patched NRO length mismatch: got {len(patched_data)}, expected {initial_len}"
            )

        resolved_output.write_bytes(patched_data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply DBI 905 assembly patches and Cyrillic font glyph repair."
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
