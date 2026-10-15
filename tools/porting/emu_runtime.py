"""Porting tool. Compare the injected matchers (pfxsfx, ctor_exact) of a patched NRO, run in Unicorn, against a
Python model of the intended rules; also count instructions per call.

usage: emu_runtime.py PATCHED.nro translation.bin pfxsfx_addr ctor_exact_addr state_addr"""
import struct
import sys

from unicorn import UC_ARCH_ARM64, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm64_const import (UC_ARM64_REG_CPACR_EL1, UC_ARM64_REG_LR, UC_ARM64_REG_PC,
                                 UC_ARM64_REG_SP, UC_ARM64_REG_X0, UC_ARM64_REG_X1,
                                 UC_ARM64_REG_X2, UC_ARM64_REG_X8)

B = 0x7100000000
HEAP, STACK, STOP = 0x7400000000, 0x7300000000, 0x7500000000
MAGIC = 0x534E415254494244


def load_table(path):
    return load_table_bytes(open(path, "rb").read())


def load_table_bytes(t):
    count, stride, ru_off, tr_off = struct.unpack_from("<IIII", t, 0xC)
    keys, values = {}, set()
    for i in range(count):
        e = 0x20 + i * stride
        kl, tl = struct.unpack_from("<HH", t, e)
        k, v = t[e + ru_off:e + ru_off + kl], t[e + tr_off:e + tr_off + tl]
        keys.setdefault(k, v)
        if tl:
            values.add(v)
    return t, keys, values


def letter(c):
    return c >= 0x80 or chr(c).isalnum()


def model_pfxsfx(K, V, b):
    i = 0
    while i < len(b) and b[i] < 0x20:
        i += 1
    lead, s = b[:i], b[i:]
    if s in V:
        return b
    if s in K:
        return K[s]
    if len(s) > 0x100 or len(s) < 2 or not any(c >= 0x80 for c in s):
        return b
    p = next((n for n in range(len(s), 1, -1) if s[:n] in K and
              (not letter(s[n - 1]) or not letter(s[n]))), 0)
    q = next((n for n in range(len(s), 1, -1) if s[len(s) - n:] in K and
              (not letter(s[len(s) - n]) or not letter(s[len(s) - n - 1]))), 0)
    if not p and not q:
        return b
    if p + q > len(s):
        q = 0
    out = lead + (K[s[:p]] if p else b"") + s[p:len(s) - q] + (K[s[len(s) - q:]] if q else b"")
    if len(out) > 0x200:
        return b
    return out


def model_ctor(K, V, buf, n):
    s = buf[:n]
    if n == 0 or n > 0x100 or not any(c >= 0x80 for c in s):
        return s
    if s in V:
        return s
    if n < len(buf) and buf[n] != 0:
        z = buf.find(b"\0")
        L = z if z >= 0 else len(buf)
        if L < 0x100 and buf[:L] in V:
            return buf[:L]
    return K.get(s, s)


class Emu:
    def __init__(self, nro, table, state):
        mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        mu.mem_map(B, 0x1280000)
        mu.mem_write(B, nro[:0xFDA000])
        mu.reg_write(UC_ARM64_REG_CPACR_EL1, 0x300000)
        mu.mem_map(HEAP, 0x400000)
        mu.mem_write(HEAP, table)
        mu.mem_write(B + state + 0x10, struct.pack("<QQ", MAGIC, HEAP))
        mu.mem_map(STACK, 0x10000)
        mu.mem_map(STOP, 0x1000)
        self.mu, self.count = mu, 0
        mu.hook_add(UC_HOOK_CODE, self._count)

    def _count(self, uc, a, s, _):
        self.count += 1

    def call(self, fn, data, n, x0=0):
        mu, src = self.mu, HEAP + 0x300000
        mu.mem_write(src, data + b"\0" * 8)
        regs = ((UC_ARM64_REG_X0, x0 or src), (UC_ARM64_REG_X1, n if not x0 else src),
                (UC_ARM64_REG_SP, STACK + 0x8000), (UC_ARM64_REG_LR, STOP))
        for r, v in regs:
            mu.reg_write(r, v)
        if x0:
            mu.reg_write(UC_ARM64_REG_X2, n)
        self.count = 0
        mu.emu_start(B + fn, STOP, count=50_000_000)
        return mu.reg_read(UC_ARM64_REG_X0), mu.reg_read(UC_ARM64_REG_X1), mu.reg_read(UC_ARM64_REG_X2)

    def pfxsfx(self, fn, b):
        p, n, _ = self.call(fn, b, len(b))
        return bytes(self.mu.mem_read(p, n))

    def ctor(self, fn, buf, n):
        _, p, ln = self.call(fn, buf, n, x0=HEAP + 0x380000)
        return bytes(self.mu.mem_read(p, ln))


def run_loader(nro, table, state, loader, reader_fn):
    """Run the injected loader with DBI's file reader replaced by a stub that returns `table`.
    Returns True when the loader published the table (state magic set, tableptr = buffer)."""
    mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    mu.mem_map(B, 0x1280000)
    mu.mem_write(B, nro[:0xFDA000])
    mu.reg_write(UC_ARM64_REG_CPACR_EL1, 0x300000)
    mu.mem_map(HEAP, 0x400000)
    buf = HEAP + 0x10000
    mu.mem_write(buf, table)
    mu.mem_map(STACK, 0x10000)
    mu.mem_map(STOP, 0x1000)

    def reader(uc, addr, size, _):            # X8 = out std::string: {data, size, ...}
        out = uc.reg_read(UC_ARM64_REG_X8)
        uc.mem_write(out, struct.pack("<QQ", buf, len(table)))
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))

    mu.hook_add(UC_HOOK_CODE, reader, begin=B + reader_fn, end=B + reader_fn)
    mu.reg_write(UC_ARM64_REG_SP, STACK + 0x8000)
    mu.reg_write(UC_ARM64_REG_LR, STOP)
    mu.emu_start(B + loader, STOP, count=1_000_000)
    magic, ptr = struct.unpack("<QQ", mu.mem_read(B + state + 0x10, 16))
    return magic == MAGIC and ptr == buf


def corpus(K, V, step=7):
    keys = sorted(K)[::step]
    vals = sorted(V)[::step]
    out = []
    for k in keys:
        out += [k, k + b" 42", b"\x1b[32;1m" + k + b"\x1b[37;1m", b"[x] " + k, b"\r" + k]
    out += vals
    out += [v + b" 42" for v in vals[::3]]
    out += ["Сдампить на SD карту".encode(), "Дампити на SD-карту".encode(), "Видалити".encode(),
            "Общее время игры      : - (2)".encode(), "Языки: RU,EN".encode(),
            "Дамп на SD".encode(), "Данные".encode(), "привет".encode(), b"hello", b""]
    return [c for c in out if len(c) <= 0x180]


def ctor_corpus(K, V, step=5):
    out = [(k, len(k)) for k in sorted(K)[::step]] + [(v, len(v)) for v in sorted(V)[::step]]
    out += [(v + b"\0", n) for v in sorted(V)[::step * 2] for n in (len(v) - 2, len(v) // 2) if n > 0]
    out += [("Видалити".encode() + b"\0", 14), ("Відкрити".encode() + b"\0", 14),
            ("C:/Сохранения/x".encode(), 20)]
    return out


if __name__ == "__main__":
    nro = open(sys.argv[1], "rb").read()
    table, K, V = load_table(sys.argv[2])
    px, ce, state = (int(x, 16) for x in sys.argv[3:6])
    emu = Emu(nro, table, state)
    bad = 0
    cases = corpus(K, V)
    for c in cases:
        got, want = emu.pfxsfx(px, c), model_pfxsfx(K, V, c)
        if got != want:
            bad += 1
            if bad <= 15:
                print("PFX MISMATCH", c.decode("utf-8", "replace")[:60], "|", got.decode("utf-8", "replace")[:60],
                      "| model", want.decode("utf-8", "replace")[:60])
    ctor_cases = ctor_corpus(K, V)
    for buf, n in ctor_cases:
        got, want = emu.ctor(ce, buf, n), model_ctor(K, V, buf, n)
        if got != want:
            bad += 1
            if bad <= 30:
                print("CTOR MISMATCH", buf[:n].decode("utf-8", "replace"), "|", got.decode("utf-8", "replace"),
                      "| model", want.decode("utf-8", "replace"))
    for s in ("Сдампить на SD карту", "Дампити на SD-карту", "Видалити", "Відкрити вміст через MTP"):
        out = emu.pfxsfx(px, s.encode())
        print(f"pfxsfx {s!r} -> {out.decode('utf-8', 'replace')!r}  ({emu.count} insns)")
    for s, n in (("Видалити", 14), ("Відкрити", 14), ("Удалить", 14)):
        out = emu.ctor(ce, s.encode() + b"\0", n)
        print(f"ctor {s!r}[:{n}] -> {out.decode('utf-8', 'replace')!r}  ({emu.count} insns)")
    print(f"{len(cases)} pfxsfx + {len(ctor_cases)} ctor cases, mismatches: {bad}")
    sys.exit(1 if bad else 0)
