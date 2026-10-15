#!/usr/bin/env python3
"""Patch a pristine DBI NRO for runtime translation and repair Cyrillic font glyphs.

The runtime-translation engine is the vendored `dbi_translate` package in
`vendor/dbi_translate` (originally 0xroast/dbi-translate, MIT). The DBI version is
detected from the input SHA-256; each supported release has a `Version` entry in
`vendor/dbi_translate/versions.py`.

Cyrillic font-glyph repair logic is adapted from Bohdan Buinich's dbi-i18n
reference implementation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sys

import zstandard

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))

from dbi_translate import VERSIONS, patch_nro  # noqa: E402

# Pristine russian release NROs from https://github.com/rashevskyv/dbi/releases
DBI_SHA256 = {
    "f4360db14ea7ed1043a5a0c7d076d4861cc3383f3b254b9b38d2eec6d175686f": "905",
    "e77da77f95a24f94fb39df23513961846a75d07aa2f970f39846ed7bbbd22bd2": "912",
}

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


def detect_version(nro_path: Path) -> str:
    """Return the DBI version of a pristine release NRO, identified by its SHA-256."""
    actual_sha = compute_sha256(nro_path)
    version = DBI_SHA256.get(actual_sha.lower())
    if version is None:
        known = ", ".join(f"{v} ({sha})" for sha, v in DBI_SHA256.items())
        raise ValueError(
            f"Unsupported NRO SHA-256: {actual_sha}; "
            f"supported pristine DBI releases: {known}"
        )
    return version


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
) -> str:
    """Patch a pristine DBI NRO for runtime translation and repair the font in memory.
    Returns the detected DBI version."""
    resolved_nro = nro_path.resolve()
    if not resolved_nro.is_file():
        raise FileNotFoundError(f"Input NRO file not found: {resolved_nro}")

    version = detect_version(resolved_nro)

    resolved_output = output_path.resolve()
    if resolved_nro == resolved_output:
        raise ValueError(
            f"Output path cannot be identical to input NRO path: {resolved_output}"
        )

    data = resolved_nro.read_bytes()
    translated, report = patch_nro(VERSIONS[version], data)
    for line in report:
        print(line)

    patched_data = patch_nro_font(bytearray(translated))
    if len(patched_data) != len(data):
        raise RuntimeError(
            f"Patched NRO length mismatch: got {len(patched_data)}, expected {len(data)}"
        )

    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_bytes(patched_data)
    return version


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply DBI runtime-translation patches and Cyrillic font glyph repair."
    )
    parser.add_argument(
        "--nro",
        type=Path,
        required=True,
        help="Path to a pristine DBI release NRO (e.g. DBI.912.ru.nro)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to save the patched NRO (e.g. DBI.912.ru_patched.nro)",
    )
    args = parser.parse_args()

    try:
        version = patch_dbi(args.nro, args.output)
    except (FileNotFoundError, ValueError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    print(f"Successfully patched DBI {version} NRO -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
