"""Build and read the DBITRNS translation table (translation.bin).

Layout:
  header (0x20 bytes): magic "DBITRNS\\0", u32 version=2, u32 count, u32 stride,
                       u32 ru_off=4, u32 tr_off, u32 reserved=0
  entry (stride bytes, x count): u16 ru_len, u16 tr_len, ru bytes @ru_off (NUL-padded),
                                 tr bytes @tr_off (NUL-padded)
Lookup matches the exact UTF-8 source text.
"""

from __future__ import annotations

import csv
import re
import struct
from pathlib import Path

MAGIC = b"DBITRNS\x00"
VERSION = 2
HEADER_SIZE = 0x20
RU_OFF = 4


def _unescape(s: str) -> str:
    s = s.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
    return re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), s)


def load_csv(path: Path) -> list[tuple[bytes, bytes]]:
    """Read unique (source, target) UTF-8 pairs from an 'original,translation' CSV.
    Skips empty cells, identity rows, and duplicate sources."""
    pairs, seen = [], set()
    with Path(path).open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "original" not in reader.fieldnames or "translation" not in reader.fieldnames:
            raise SystemExit(f"{path}: CSV needs 'original' and 'translation' columns; got {reader.fieldnames}")
        for row in reader:
            ru = _unescape(row.get("original", "") or "").encode("utf-8")
            tr = _unescape(row.get("translation", "") or "").encode("utf-8")
            if not ru or not tr or ru == tr or ru in seen:
                continue
            seen.add(ru)
            pairs.append((ru, tr))
    return pairs


def build_table(pairs: list[tuple[bytes, bytes]]) -> bytes:
    """Pack (source, target) pairs into a translation.bin image."""
    if not pairs:
        raise SystemExit("no translation pairs")
    max_ru = max(len(ru) for ru, _ in pairs)
    max_tr = max(len(tr) for _, tr in pairs)
    if max_ru > 0xFFFF or max_tr > 0xFFFF:
        raise SystemExit(f"string too long for u16 length: max_ru={max_ru}, max_tr={max_tr}")
    tr_off = RU_OFF + ((max_ru + 3) & ~3)
    stride = tr_off + ((max_tr + 3) & ~3)

    buf = bytearray(HEADER_SIZE)
    buf[0:8] = MAGIC
    struct.pack_into("<IIIIII", buf, 8, VERSION, len(pairs), stride, RU_OFF, tr_off, 0)
    for ru, tr in pairs:
        entry = bytearray(stride)
        struct.pack_into("<HH", entry, 0, len(ru), len(tr))
        entry[RU_OFF:RU_OFF + len(ru)] = ru
        entry[tr_off:tr_off + len(tr)] = tr
        buf += entry
    return bytes(buf)


def build_from_csv(csv_path: Path) -> bytes:
    return build_table(load_csv(csv_path))


def parse_table(data: bytes) -> dict[bytes, bytes]:
    """Read a translation.bin image back into a {source: target} dict."""
    if data[:8] != MAGIC:
        raise ValueError("not a DBITRNS table")
    count, stride, ru_off, tr_off = struct.unpack_from("<IIII", data, 12)
    out = {}
    for i in range(count):
        r = HEADER_SIZE + i * stride
        ru_len, tr_len = struct.unpack_from("<HH", data, r)
        out[data[r + ru_off:r + ru_off + ru_len]] = data[r + tr_off:r + tr_off + tr_len]
    return out
