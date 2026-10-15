"""Patch a DBI NRO: inject the runtime and hooks into the code cave and redirect the
hook sites into it. Modifies only the cave and the five hook-site instructions."""

from __future__ import annotations

import struct

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

from .asm import assemble, enc_b, enc_bl
from .hooks import ctor_hook, glog_hook, reader_hook, sink_hook
from .runtime import PATH_STR, STATE_MAGIC, loader, make_fmt, make_pfxsfx, shared_lookup
from .versions import BASE, Version


class PatchError(Exception):
    """The input NRO does not match the target version, or the build fails its self-check."""


def _check_site(data, site, label):
    got = struct.unpack_from("<I", data, site.addr)[0]
    if got != site.insn:
        raise PatchError(
            f"{label} site {site.addr:#x}: expected {site.insn:#010x}, found {got:#010x} "
            f"(is this the right DBI version?)"
        )


SCRATCH_MAX = 0x200   # make_pfxsfx caps a rebuilt line at 0x200 bytes


def _check_state_area(v, data):
    """state/persist/scratch must sit between the program's __bss_end__ (MOD0) and the end of
    the mapped image: below __bss_end__ is live data, including the main thread's TLS block."""
    mod0 = struct.unpack_from("<I", data, 4)[0]
    if data[mod0:mod0 + 4] != b"MOD0":
        raise PatchError("MOD0 not found")
    bss_end = mod0 + struct.unpack_from("<i", data, mod0 + 12)[0]
    data_off, data_size = struct.unpack_from("<II", data, 0x30)
    image_end = data_off + data_size + struct.unpack_from("<I", data, 0x38)[0]
    lo, hi = min(v.state, v.persist, v.scratch), v.scratch + SCRATCH_MAX
    if lo < bss_end or hi > image_end:
        raise PatchError(f"state area {lo:#x}..{hi:#x} is outside {bss_end:#x}..{image_end:#x}")
    if v.bss_end:
        addr, old, new = v.bss_end
        got = struct.unpack_from("<I", data, addr)[0]
        if addr != mod0 + 12 or got != old or mod0 + new != image_end:
            raise PatchError(f"MOD0 bss_end field {addr:#x}: expected {old:#x}, found {got:#x}")


def patch_nro(v: Version, data: bytes):
    """Return (patched_bytes, report_lines). Raises PatchError on version mismatch or
    self-check failure."""
    data = bytearray(data)
    orig = bytes(data)
    cave_start, cave_end = v.cave
    if v.clear_cave:
        data[cave_start:cave_end] = bytes(cave_end - cave_start)

    for site, label in ((v.reader, "reader"), (v.fmt, "fmt"), (v.glog, "glog"),
                        (v.ctor, "ctor"), (v.sink, "sink")):
        _check_site(data, site, label)
    _check_state_area(v, data)

    # cave layout: [path][pool][shared_lookup][loader][fmt][pfxsfx][glog][ctor][sink][reader]
    # pool = one 8-aligned STATE_MAGIC literal shared by shared_lookup + loader (LDR, not MOVK).
    path_addr = cave_start
    pool_addr = (cave_start + len(PATH_STR) + 7) & ~7
    addr = pool_addr + 8
    sl = assemble(shared_lookup(v, pool_addr), addr); sl_base = addr; addr += len(sl)
    ld = assemble(loader(v, path_addr, pool_addr), addr); ld_base = addr; addr += len(ld)
    fmt = assemble(make_fmt(v, sl_base), addr); fmt_base = addr; addr += len(fmt)
    px = assemble(make_pfxsfx(v, sl_base), addr); px_base = addr; addr += len(px)
    lg = assemble(glog_hook(v, px_base), addr); lg_base = addr; addr += len(lg)
    ch = assemble(ctor_hook(v, px_base), addr); ch_base = addr; addr += len(ch)
    sk = assemble(sink_hook(v, px_base), addr); sk_base = addr; addr += len(sk)
    rh = assemble(reader_hook(v, ld_base), addr); rh_base = addr; addr += len(rh)

    total = addr - cave_start
    if total > cave_end - cave_start:
        raise PatchError(f"cave too small: need {total}, have {cave_end - cave_start}")
    if any(data[cave_start:addr]):
        raise PatchError("cave is not zero-filled (non-zero bytes present)")

    data[path_addr:path_addr + len(PATH_STR)] = PATH_STR
    struct.pack_into("<Q", data, pool_addr, STATE_MAGIC)
    data[sl_base:sl_base + len(sl)] = sl
    data[ld_base:ld_base + len(ld)] = ld
    data[fmt_base:fmt_base + len(fmt)] = fmt
    data[px_base:px_base + len(px)] = px
    data[lg_base:lg_base + len(lg)] = lg
    data[ch_base:ch_base + len(ch)] = ch
    data[sk_base:sk_base + len(sk)] = sk
    data[rh_base:rh_base + len(rh)] = rh
    struct.pack_into("<I", data, v.fmt.addr, enc_b(v.fmt.addr, fmt_base))
    struct.pack_into("<I", data, v.glog.addr, enc_b(v.glog.addr, lg_base))
    struct.pack_into("<I", data, v.ctor.addr, enc_b(v.ctor.addr, ch_base))
    struct.pack_into("<I", data, v.sink.addr, enc_bl(v.sink.addr, sk_base))
    struct.pack_into("<I", data, v.reader.addr, enc_b(v.reader.addr, rh_base))
    if v.bss_end:
        struct.pack_into("<I", data, v.bss_end[0], v.bss_end[2])

    _self_check(v, orig, data, addr,
                {"fmt": fmt_base, "glog": lg_base, "ctor": ch_base, "sink": sk_base, "reader": rh_base})

    report = [
        f"path @ {path_addr:#x}  pool @ {pool_addr:#x}  shared_lookup @ {sl_base:#x}({len(sl)}B)  "
        f"loader @ {ld_base:#x}({len(ld)}B)",
        f"cave used {total}/{cave_end - cave_start}",
    ]
    return bytes(data), report


def _self_check(v, orig, data, cave_top, bases):
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

    def expect(site, base, mnem):
        w = struct.unpack_from("<I", data, site.addr)[0]
        i = next(md.disasm(struct.pack("<I", w), BASE + site.addr))
        if not (i.mnemonic == mnem and int(i.op_str.lstrip("#"), 0) == BASE + base):
            raise PatchError(
                f"self-check: {site.addr:#x} -> {i.mnemonic} {i.op_str}, expected {mnem} {BASE + base:#x}"
            )

    expect(v.fmt, bases["fmt"], "b")
    expect(v.glog, bases["glog"], "b")
    expect(v.ctor, bases["ctor"], "b")
    expect(v.sink, bases["sink"], "bl")
    expect(v.reader, bases["reader"], "b")

    sites = {v.reader.addr, v.fmt.addr, v.glog.addr, v.ctor.addr, v.sink.addr}
    if v.bss_end:
        sites.add(v.bss_end[0])
    cave_start = v.cave[0]
    if v.clear_cave:   # the whole dead function was zeroed on purpose
        cave_top = v.cave[1]
    stray = [i for i in range(len(orig)) if orig[i] != data[i]
             and not (cave_start <= i < cave_top) and not any(s <= i < s + 4 for s in sites)]
    if stray:
        raise PatchError(f"self-check: {len(stray)} byte(s) changed outside the cave and hook sites")
