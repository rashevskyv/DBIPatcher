#!/usr/bin/env python3
"""Porting tool: propose a dbi_translate Version entry for a new DBI release.

Takes a release the engine already supports (its Version entry and pristine NRO) and the
new pristine NRO, and finds in the new NRO:
  - the five hook sites, by normalized instruction sequence around each old site;
  - the code cave: the old cave function, by its body, plus a check that nothing outside
    it branches, ADR/ADRP+ADDs or points into it;
  - the state area past MOD0 __bss_end__ and the MOD0 bss_end field;
  - the std::string(const char*, size_t) copies (Version.ctors candidates), with call
    counts, and the copy that matches the old panel copy best.

usage: find_sites.py OLD_VERSION OLD.nro NEW.nro [NEW_NAME]
Run from the DBIPatcher root (imports vendor/dbi_translate). See docs/PORTING.md.
"""
from __future__ import annotations

import re
import struct
import sys
from collections import Counter
from pathlib import Path

import capstone

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor"))
from dbi_translate.versions import CTOR_INSN, VERSIONS  # noqa: E402

MD = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
MD.skipdata = True


def text_end(d: bytes) -> int:
    off, size = struct.unpack_from("<II", d, 0x20)
    return off + size


def norm(d: bytes, a: int, n: int) -> tuple:
    """n instructions from a, immediates replaced (addresses move between releases)."""
    return tuple(i.mnemonic + " " + re.sub(r"#-?0x[0-9a-f]+|#-?\d+", "#i", i.op_str)
                 for i in MD.disasm(d[a:a + 4 * n], a))


def find_window(old: bytes, new: bytes, site: int, before: int, after: int) -> list[int]:
    """Addresses in new where the normalized window [site-4*before, site+4*after) matches."""
    ref = norm(old, site - 4 * before, before + after)
    w = struct.unpack_from("<I", old, site)[0]
    hits = []
    for a in range(4 * before, text_end(new) - 4 * after, 4):
        if struct.unpack_from("<I", new, a)[0] == w and norm(new, a - 4 * before, before + after) == ref:
            hits.append(a)
    return hits


def branch_target(w: int, a: int) -> int | None:
    if w >> 26 in (0x05, 0x25):                                   # B / BL
        return a + ((((w & 0x3FFFFFF) ^ 0x2000000) - 0x2000000) << 2)
    if (w & 0xFF000010) == 0x54000000 or (w >> 24) & 0x7E == 0x34:  # B.cond / CBZ / CBNZ
        return a + ((((w >> 5) & 0x7FFFF) ^ 0x40000) - 0x40000) * 4
    if (w >> 24) & 0x7E == 0x36:                                  # TBZ / TBNZ
        return a + ((((w >> 5) & 0x3FFF) ^ 0x2000) - 0x2000) * 4
    if (w & 0x9F000000) == 0x10000000:                            # ADR
        return a + (((((w >> 5) & 0x7FFFF) << 2 | (w >> 29) & 3) ^ 0x100000) - 0x100000)
    return None


def outside_refs(d: bytes, lo: int, hi: int) -> list[str]:
    """Anything outside [lo, hi) that reaches into it: branches, ADR, ADRP+ADD, data pointers."""
    refs, end, pages = [], text_end(d), {}
    for a in range(0, end, 4):
        if lo <= a < hi:
            continue
        w = struct.unpack_from("<I", d, a)[0]
        t = branch_target(w, a)
        if t is not None and lo <= t < hi:
            refs.append(f"branch {a:#x}")
        if (w & 0x9F000000) == 0x90000000:                        # ADRP
            imm = ((w >> 29) & 3) | (((w >> 5) & 0x7FFFF) << 2)
            pages[w & 31] = (a & ~0xFFF) + (((imm ^ 0x100000) - 0x100000) << 12)
        elif (w & 0xFF800000) == 0x91000000 and (w >> 5) & 31 in pages:   # ADD imm
            t = pages[(w >> 5) & 31] + ((w >> 10) & 0xFFF)
            if lo <= t < hi:
                refs.append(f"adrp+add {a:#x}")
    for so, ss in (struct.unpack_from("<II", d, 0x28), struct.unpack_from("<II", d, 0x30)):
        for o in range(so, so + ss - 7, 8):
            v = struct.unpack_from("<Q", d, o)[0]
            v = v - 0x7100000000 if v >= 0x7100000000 else v
            if lo <= v < hi:
                refs.append(f"pointer {o:#x}")
    return refs


def call_counts(d: bytes, targets: set[int]) -> Counter:
    c = Counter()
    for a in range(0, text_end(d), 4):
        w = struct.unpack_from("<I", d, a)[0]
        if w >> 26 == 0x25:
            t = branch_target(w, a)
            if t in targets:
                c[t] += 1
    return c


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    v = VERSIONS[sys.argv[1]]
    old, new = Path(sys.argv[2]).read_bytes(), Path(sys.argv[3]).read_bytes()
    name = sys.argv[4] if len(sys.argv) > 4 else "NEW"
    out = {}
    for label in ("reader", "fmt", "glog", "ctor", "sink"):
        site = getattr(v, label)
        before = 0 if site.entry == "B" else 12
        hits = find_window(old, new, site.addr, before, 24)
        status = "OK" if len(hits) == 1 else f"{len(hits)} matches - check by hand"
        print(f"{label:6} old {site.addr:#x} -> {[hex(h) for h in hits]}  {status}")
        out[label] = (hits[0] if len(hits) == 1 else None, site)

    cave_lo, cave_hi = v.cave
    size = cave_hi - cave_lo
    caves = find_window(old, new, cave_lo, 0, 64) if v.clear_cave else []
    cave = None
    for c in caves:
        if norm(old, cave_lo, size // 4) == norm(new, c, size // 4):
            refs = outside_refs(new, c, c + size)
            print(f"cave   {c:#x} ({size} B), outside references: {refs[:5] or 'none'}")
            if not refs:
                cave = c
    if cave is None:
        print("cave   NOT FOUND: look for another unreferenced function (docs/PORTING.md)")

    mod0 = struct.unpack_from("<I", new, 4)[0]
    bss_end = mod0 + struct.unpack_from("<i", new, mod0 + 12)[0]
    data_off, data_size, bss_size = struct.unpack_from("<III", new, 0x30)
    image_end = data_off + data_size + bss_size
    state = (bss_end + 0xF) & ~0xF
    print(f"bss    __bss_end__ {bss_end:#x}, image end {image_end:#x}, "
          f"free {image_end - bss_end:#x} bytes (need 0x280)")

    ref = norm(old, v.ctors[0], 40) if v.ctors else None
    ctors = []
    if ref:
        for a in range(0, text_end(new), 4):
            if struct.unpack_from("<I", new, a)[0] == CTOR_INSN and norm(new, a, 40) == ref:
                ctors.append(a)
        old_calls = call_counts(old, set(v.ctors))
        new_calls = call_counts(new, set(ctors))
        print(f"ctors  {len(ctors)} std::string(const char*, size_t) copies")
        for oc in v.ctors:
            best = sorted(ctors, key=lambda a: abs(new_calls[a] - old_calls[oc]))[:3]
            print(f"       old {oc:#x} ({old_calls[oc]} calls) -> closest by calls: "
                  + ", ".join(f"{a:#x} ({new_calls[a]})" for a in best))

    def site(label):
        a, s = out[label]
        return f"Site(0x{a:X}, 0x{s.insn:08X}, 0x{a + 4:X}, \"{s.entry}\")" if a is not None else "Site(?)"

    old_field = struct.unpack_from("<I", new, mod0 + 12)[0]

    def h(x):
        return f"0x{x:X}"

    print(f"""
V{name} = Version(
    name="{name}",
    cave=({h(cave or 0)}, {h(cave or 0)} + {size}),
    state={h(state)},
    persist={h(state + 0x20)},
    scratch={h(state + 0x80)},
    reader_fn={h(out['reader'][0] or 0)},
    reader={site('reader')},
    fmt={site('fmt')},
    glog={site('glog')},
    ctor={site('ctor')},
    sink={site('sink')},
    bss_end=({h(mod0 + 12)}, {h(old_field)}, {h(image_end - mod0)}),
    clear_cave=True,
    ctors=(?,),   # pick from the candidates above, then test on a console
)""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
