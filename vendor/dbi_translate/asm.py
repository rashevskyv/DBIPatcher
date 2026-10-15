"""AArch64 assembly helpers: a tiny program encoder over keystone plus the fixed
encodings for the branch/ADRP/LDR-literal forms the builder emits directly.

A program is a list of tuples:
  ("I", "add x0, x0, #1")     keystone-assembled instruction ({label} placeholders allowed)
  ("L", "name")               a label
  ("ADRP", rd, target)        ADRP xrd, page(target)
  ("LDRLIT", rt, target)      LDR xrt, <target>   (64-bit, PC-relative)
"""

from __future__ import annotations

import struct

from keystone import Ks, KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN


def movk_seq(rd, val):
    """movz/movk sequence loading a 64-bit immediate into xrd."""
    ch = [(val >> s) & 0xFFFF for s in (0, 16, 32, 48)]
    out = [("I", f"movz x{rd}, #{ch[0]:#x}")]
    for i, sh in enumerate((16, 32, 48), start=1):
        out.append(("I", f"movk x{rd}, #{ch[i]:#x}, lsl #{sh}"))
    return out


def enc_adrp(pc, target, rd):
    dd = ((target & ~0xFFF) - (pc & ~0xFFF)) >> 12
    dd &= 0x1FFFFF
    return 0x90000000 | ((dd & 3) << 29) | (((dd >> 2) & 0x7FFFF) << 5) | (rd & 0x1F)


def enc_bl(site, target):
    return 0x94000000 | (((target - site) >> 2) & 0x03FFFFFF)


def enc_b(site, target):
    return 0x14000000 | (((target - site) >> 2) & 0x03FFFFFF)


def enc_ldr_lit(pc, target, rt):   # LDR Xt, <literal> (64-bit, PC-relative, +-1MB)
    return 0x58000000 | (((target - pc) >> 2) & 0x7FFFF) << 5 | (rt & 0x1F)


def assemble(prog, base):
    """Assemble a program to bytes at absolute address `base`."""
    ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
    labels, addr = {}, base
    for kind, *rest in prog:
        if kind == "L":
            labels[rest[0]] = addr
        else:
            addr += 4
    out, addr = bytearray(), base
    for kind, *rest in prog:
        if kind == "L":
            continue
        if kind == "ADRP":
            w = enc_adrp(addr, rest[1], rest[0])
        elif kind == "LDRLIT":
            w = enc_ldr_lit(addr, rest[1], rest[0])
        else:
            enc, n = ks.asm(rest[0].format(**{k: hex(v) for k, v in labels.items()}), addr)
            if n != 1:
                raise RuntimeError(f"asm {rest[0]!r} -> {n}")
            w = int.from_bytes(bytes(enc), "little")
        out += struct.pack("<I", w)
        addr += 4
    return bytes(out)
