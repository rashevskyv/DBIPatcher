"""Patch a DBI NRO: inject the runtime and hooks into the code cave and redirect the
hook sites into it. Modifies only the cave and the configured hook-site instructions."""

from __future__ import annotations

import struct

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

from .asm import assemble, enc_b, enc_bl
from .hooks import (ctor_hook, ctor_stub, glog_hook, reader_hook, sink_hook, string_call_stub,
                    string_wrap_stub)
from .runtime import (PATH_STR, STATE_MAGIC, ctor_exact, loader, make_fmt, make_pfxsfx,
                      shared_lookup, translate_string, value_lookup)
from .versions import BASE, CTOR_INSN, WRAP_INSN, Site, Version


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
    ctor_sites = [Site(a, CTOR_INSN, a + 4, "B") for a in v.ctors]
    for site in ctor_sites:
        _check_site(data, site, "ctor copy")
    for call in v.string_calls:
        if not v.string_append or not 0 <= call.argument <= 7 or not 1 <= call.count <= 8:
            raise PatchError("UI string calls require an append function and an argument register x0..x7")
        _check_site(data, Site(call.addr, enc_bl(call.addr, call.target), 0, "BL"), "UI string call")
    wrap_sites = [Site(a, WRAP_INSN, a + 4, "B") for a in v.string_wraps]
    if wrap_sites and not v.string_append:
        raise PatchError("string wraps require an append function")
    for site in wrap_sites:
        _check_site(data, site, "string wrap")
    _check_state_area(v, data)

    # cave layout: [path][pool][shared_lookup][loader][fmt][pfxsfx][glog][ctor][sink][reader]
    # pool = one 8-aligned STATE_MAGIC literal shared by shared_lookup + loader (LDR, not MOVK).
    path_addr = cave_start
    pool_addr = (cave_start + len(PATH_STR) + 7) & ~7
    addr = pool_addr + 8
    sl = assemble(shared_lookup(v, pool_addr), addr); sl_base = addr; addr += len(sl)
    vl = assemble(value_lookup(v, pool_addr), addr); vl_base = addr; addr += len(vl)
    ld = assemble(loader(v, path_addr, pool_addr), addr); ld_base = addr; addr += len(ld)
    fmt = assemble(make_fmt(v, sl_base), addr); fmt_base = addr; addr += len(fmt)
    px = assemble(make_pfxsfx(v, sl_base, vl_base), addr); px_base = addr; addr += len(px)
    lg = assemble(glog_hook(v, px_base), addr); lg_base = addr; addr += len(lg)
    ch = assemble(ctor_hook(v, px_base), addr); ch_base = addr; addr += len(ch)
    sk = assemble(sink_hook(v, px_base), addr); sk_base = addr; addr += len(sk)
    rh = assemble(reader_hook(v, ld_base), addr); rh_base = addr; addr += len(rh)
    # [ctor_exact][one stub per std::string(const char*, size_t) copy]
    stubs = []
    if ctor_sites:
        ce = assemble(ctor_exact(v, sl_base, vl_base), addr); ce_base = addr; addr += len(ce)
        stubs.append((ce_base, ce))
        for site in ctor_sites:
            st = assemble(ctor_stub(site.addr, ce_base), addr)
            stubs.append((addr, st)); addr += len(st)

    # Share one translator and one trampoline per (target, argument, count), rather
    # than hooking every std::string constructor in the binary.
    ui_code, ui_stubs, ui_wrappers, wrap_stubs = [], [], {}, []
    if v.string_calls or wrap_sites:
        translator = addr
        code = assemble(translate_string(v, sl_base), addr)
        ui_code.append((addr, code)); addr += len(code)
        for key in sorted({(c.target, c.argument, c.count) for c in v.string_calls}):
            call = next(c for c in v.string_calls if (c.target, c.argument, c.count) == key)
            ui_wrappers[key] = addr
            code = assemble(string_call_stub(call, translator), addr)
            ui_code.append((addr, code)); addr += len(code)
        ui_stubs = [(Site(c.addr, enc_bl(c.addr, c.target), 0, "BL"), ui_wrappers[(c.target, c.argument, c.count)])
                    for c in v.string_calls]
        for site in wrap_sites:
            code = assemble(string_wrap_stub(site.addr, translator), addr)
            ui_code.append((addr, code)); wrap_stubs.append((site, addr)); addr += len(code)

    total = addr - cave_start
    if total > cave_end - cave_start:
        raise PatchError(f"cave too small: need {total}, have {cave_end - cave_start}")
    if any(data[cave_start:addr]):
        raise PatchError("cave is not zero-filled (non-zero bytes present)")

    data[path_addr:path_addr + len(PATH_STR)] = PATH_STR
    struct.pack_into("<Q", data, pool_addr, STATE_MAGIC)
    data[sl_base:sl_base + len(sl)] = sl
    data[vl_base:vl_base + len(vl)] = vl
    data[ld_base:ld_base + len(ld)] = ld
    data[fmt_base:fmt_base + len(fmt)] = fmt
    data[px_base:px_base + len(px)] = px
    data[lg_base:lg_base + len(lg)] = lg
    data[ch_base:ch_base + len(ch)] = ch
    data[sk_base:sk_base + len(sk)] = sk
    data[rh_base:rh_base + len(rh)] = rh
    for base, code in stubs:
        data[base:base + len(code)] = code
    for base, code in ui_code:
        data[base:base + len(code)] = code
    struct.pack_into("<I", data, v.fmt.addr, enc_b(v.fmt.addr, fmt_base))
    struct.pack_into("<I", data, v.glog.addr, enc_b(v.glog.addr, lg_base))
    struct.pack_into("<I", data, v.ctor.addr, enc_b(v.ctor.addr, ch_base))
    struct.pack_into("<I", data, v.sink.addr, enc_bl(v.sink.addr, sk_base))
    struct.pack_into("<I", data, v.reader.addr, enc_b(v.reader.addr, rh_base))
    stub_bases = [base for base, _ in stubs[1:]]
    for site, base in zip(ctor_sites, stub_bases):
        struct.pack_into("<I", data, site.addr, enc_b(site.addr, base))
    for site, base in ui_stubs:
        struct.pack_into("<I", data, site.addr, enc_bl(site.addr, base))
    for site, base in wrap_stubs:
        struct.pack_into("<I", data, site.addr, enc_b(site.addr, base))
    if v.bss_end:
        struct.pack_into("<I", data, v.bss_end[0], v.bss_end[2])

    _self_check(v, orig, data, addr,
                {"fmt": fmt_base, "glog": lg_base, "ctor": ch_base, "sink": sk_base, "reader": rh_base},
                list(zip(ctor_sites, stub_bases)) + wrap_stubs, ui_stubs)

    report = [
        f"path @ {path_addr:#x}  pool @ {pool_addr:#x}  shared_lookup @ {sl_base:#x}({len(sl)}B)  "
        f"loader @ {ld_base:#x}({len(ld)}B)",
        f"cave used {total}/{cave_end - cave_start}  ({len(ctor_sites)} ctor copies hooked)",
        "bases " + " ".join(f"{k}={b:#x}" for k, b in (
            ("loader", ld_base), ("shared_lookup", sl_base), ("value_lookup", vl_base), ("pfxsfx", px_base),
            ("fmt", fmt_base), ("ctor_exact", stubs[0][0] if stubs else 0))),
    ]
    return bytes(data), report


def _self_check(v, orig, data, cave_top, bases, ctor_stubs=(), ui_stubs=()):
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
    for site, base in ctor_stubs:
        expect(site, base, "b")
    for site, base in ui_stubs:
        expect(site, base, "bl")

    sites = {v.reader.addr, v.fmt.addr, v.glog.addr, v.ctor.addr, v.sink.addr}
    sites.update(site.addr for site, _ in ctor_stubs)
    sites.update(site.addr for site, _ in ui_stubs)
    if v.bss_end:
        sites.add(v.bss_end[0])
    cave_start = v.cave[0]
    if v.clear_cave:   # the whole dead function was zeroed on purpose
        cave_top = v.cave[1]
    stray = [i for i in range(len(orig)) if orig[i] != data[i]
             and not (cave_start <= i < cave_top) and not any(s <= i < s + 4 for s in sites)]
    if stray:
        raise PatchError(f"self-check: {len(stray)} byte(s) changed outside the cave and hook sites")
