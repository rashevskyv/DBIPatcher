"""The runtime injected into the code cave: the boot loader, the exact-match table
lookup, the prefix/suffix matcher, and the fmt-template translator. Each returns an
assembly program (see asm.py) parameterized by the target Version."""

from __future__ import annotations

from .asm import movk_seq
from .versions import Version

STATE_MAGIC = 0x534E415254494244    # "DBITRANS": state.magic when a table is loaded
FILE_MAGIC = 0x00534E5254494244     # "DBITRNS\0": translation.bin header magic
STATE_READY_HI = 0xABCD             # state-ready sentinel = STATE_READY_HI<<48 (1-instr MOVZ)
STATE_READY = STATE_READY_HI << 48  # full 64-bit: leftover bss bytes can't match it
PATH_STR = b"sdmc:/switch/DBI/translation.bin"   # 32 bytes (reader strips "sdmc:")
assert len(PATH_STR) == 32


def shared_lookup(v: Version, pool_addr):
    """(X0=key_ptr, X1=key_len) -> (X0=tr_ptr|0, X1=tr_len). Leaf; clobbers x0-x17.
    Exact scan of the DBITRNS table at state.tableptr."""
    return [
        ("ADRP", 9, v.state), ("I", f"add x9, x9, #{v.state & 0xFFF:#x}"),
        ("I", "ldr x10, [x9, #0x10]"),                      # magic
        ("LDRLIT", 11, pool_addr),
        ("I", "cmp x10, x11"), ("I", "b.ne {sl_miss}"),
        ("I", "ldr x12, [x9, #0x18]"), ("I", "cbz x12, {sl_miss}"),   # tableptr
        ("I", "ldr w13, [x12, #0xc]"),   # count
        ("I", "ldr w14, [x12, #0x10]"),  # stride
        ("I", "ldr w15, [x12, #0x14]"),  # ru_off
        ("I", "ldr w16, [x12, #0x18]"),  # tr_off
        ("I", "ldr w9, [x12, #8]"), ("I", "cmp w9, #3"), ("I", "b.ne {sl_linear}"),
    ] + _hash_probe("slh", False) + [
        ("I", "ldrh w9, [x13, #2]"),     # trlen
        ("I", "sub w10, w14, w16"), ("I", "cmp w9, w10"), ("I", "b.hi {sl_miss}"),
        ("I", "add x0, x13, x16"), ("I", "mov x1, x9"), ("I", "ret"),
        ("L", "slh_miss"),
        ("I", "mov x0, #0"), ("I", "ret"),
        ("L", "sl_linear"),
        ("I", "add x17, x12, #0x20"),    # entry ptr
        ("L", "sl_loop"),
        ("I", "cbz w13, {sl_miss}"),
        ("I", "ldrh w9, [x17]"),         # keylen
        ("I", "sub w10, w16, w15"), ("I", "cmp w9, w10"), ("I", "b.hi {sl_miss}"),
        ("I", "cmp w1, w9"), ("I", "b.ne {sl_next}"),
        ("I", "add x10, x17, x15"), ("I", "mov x11, x0"), ("I", "mov w12, w9"),
        ("L", "sl_cmp"),
        ("I", "ldrb w6, [x10], #1"), ("I", "ldrb w7, [x11], #1"),
        ("I", "cmp w6, w7"), ("I", "b.ne {sl_next}"),
        ("I", "subs w12, w12, #1"), ("I", "b.ne {sl_cmp}"),
        ("I", "ldrh w9, [x17, #2]"),     # trlen
        ("I", "sub w10, w14, w16"), ("I", "cmp w9, w10"), ("I", "b.hi {sl_miss}"),
        ("I", "add x0, x17, x16"), ("I", "mov x1, x9"), ("I", "ret"),
        ("L", "sl_next"),
        ("I", "add x17, x17, x14"), ("I", "sub w13, w13, #1"), ("I", "b {sl_loop}"),
        ("L", "sl_miss"),
        ("I", "mov x0, #0"), ("I", "ret"),
    ]


FNV_BASIS = 0x811C9DC5
FNV_PRIME = 0x01000193


def _hash_probe(t, by_value):
    """Version-3 tables: probe the FNV-1a index that follows the entries. Expects x0=ptr,
    x1=len, x12=table, w13=count, w14=stride, w15=ru_off, w16=tr_off. Uses only x6, x7, x9-x17
    (the fmt hook relies on x2, x3 and x8 surviving). Index layout: u32 nbuckets (power of 2),
    u32 key_buckets[n], u32 value_buckets[n]; a bucket holds entry index + 1, 0 = empty.
    Jumps to {t}_hit with x13 = entry, or to {t}_miss."""
    data_off, len_off = ("w16", 2) if by_value else ("w15", 0)
    return [
        ("I", "umull x17, w13, w14"), ("I", "add x17, x17, #0x20"), ("I", "add x17, x12, x17"),
        ("I", "ldr w10, [x17], #4"),              # nbuckets; x17 -> key buckets
        *([("I", "add x17, x17, x10, lsl #2")] if by_value else []),   # -> value buckets
        ("I", "sub w10, w10, #1"),                # mask
        ("I", f"mov w9, #{FNV_BASIS & 0xFFFF:#x}"), ("I", f"movk w9, #{FNV_BASIS >> 16:#x}, lsl #16"),
        ("I", f"mov w11, #{FNV_PRIME & 0xFFFF:#x}"), ("I", f"movk w11, #{FNV_PRIME >> 16:#x}, lsl #16"),
        ("I", "mov x6, #0"),
        ("L", f"{t}_h"),
        ("I", "cmp x6, x1"), ("I", f"b.hs {{{t}_hd}}"),
        ("I", "ldrb w7, [x0, x6]"), ("I", "eor w9, w9, w7"), ("I", "mul w9, w9, w11"),
        ("I", "add x6, x6, #1"), ("I", f"b {{{t}_h}}"),
        ("L", f"{t}_hd"),
        ("I", "and w9, w9, w10"),
        ("L", f"{t}_p"),
        ("I", "ldr w11, [x17, w9, uxtw #2]"), ("I", f"cbz w11, {{{t}_miss}}"),
        ("I", "sub w11, w11, #1"),
        ("I", "ldr w13, [x12, #0xc]"), ("I", "cmp w11, w13"), ("I", f"b.hs {{{t}_miss}}"),   # corrupt index
        ("I", "umull x13, w11, w14"), ("I", "add x13, x13, x12"), ("I", "add x13, x13, #0x20"),
        ("I", f"ldrh w6, [x13, #{len_off}]"), ("I", "cmp w6, w1"), ("I", f"b.ne {{{t}_pn}}"),
        ("I", f"add x11, x13, {data_off.replace('w', 'x')}"), ("I", "mov x6, #0"),
        ("L", f"{t}_c"),
        ("I", "cmp x6, x1"), ("I", f"b.hs {{{t}_hit}}"),
        ("I", "ldrb w7, [x11, x6]"), ("I", "ldrb w13, [x0, x6]"),
        ("I", "cmp w7, w13"), ("I", f"b.ne {{{t}_pn2}}"),
        ("I", "add x6, x6, #1"), ("I", f"b {{{t}_c}}"),
        ("L", f"{t}_pn2"),
        ("I", "ldr w13, [x12, #0xc]"),
        ("L", f"{t}_pn"),
        ("I", "add w9, w9, #1"), ("I", "and w9, w9, w10"), ("I", f"b {{{t}_p}}"),
        ("L", f"{t}_hit"),
        ("I", f"sub x13, x11, {data_off.replace('w', 'x')}"),     # entry
    ]


def value_lookup(v: Version, pool_addr):
    """(X0=ptr, X1=len) -> X0=1 if (ptr, len) equals the translation of some entry, else 0.
    Leaf; clobbers x0-x17. Lets the matchers leave already-translated text alone: for
    Cyrillic targets (ua/be/kk) a translation can start with a Russian key ("Дампити"
    starts with the key "Да")."""
    return [
        ("ADRP", 9, v.state), ("I", f"add x9, x9, #{v.state & 0xFFF:#x}"),
        ("I", "ldr x10, [x9, #0x10]"),
        ("LDRLIT", 11, pool_addr),
        ("I", "cmp x10, x11"), ("I", "b.ne {vl_miss}"),
        ("I", "ldr x12, [x9, #0x18]"), ("I", "cbz x12, {vl_miss}"),
        ("I", "ldr w13, [x12, #0xc]"),   # count
        ("I", "ldr w14, [x12, #0x10]"),  # stride
        ("I", "ldr w15, [x12, #0x14]"),  # ru_off
        ("I", "ldr w16, [x12, #0x18]"),  # tr_off
        ("I", "ldr w9, [x12, #8]"), ("I", "cmp w9, #3"), ("I", "b.ne {vl_linear}"),
    ] + _hash_probe("vlh", True) + [
        ("I", "mov x0, #1"), ("I", "ret"),
        ("L", "vlh_miss"),
        ("I", "mov x0, #0"), ("I", "ret"),
        ("L", "vl_linear"),
        ("I", "add x17, x12, #0x20"),
        ("L", "vl_loop"),
        ("I", "cbz w13, {vl_miss}"),
        ("I", "ldrh w9, [x17, #2]"),     # trlen
        ("I", "sub w10, w14, w16"), ("I", "cmp w9, w10"), ("I", "b.hi {vl_miss}"),
        ("I", "cmp w1, w9"), ("I", "b.ne {vl_next}"),
        ("I", "cbz w9, {vl_next}"),
        ("I", "add x10, x17, x16"), ("I", "mov x11, x0"), ("I", "mov w12, w9"),
        ("L", "vl_cmp"),
        ("I", "ldrb w6, [x10], #1"), ("I", "ldrb w7, [x11], #1"),
        ("I", "cmp w6, w7"), ("I", "b.ne {vl_next}"),
        ("I", "subs w12, w12, #1"), ("I", "b.ne {vl_cmp}"),
        ("I", "mov x0, #1"), ("I", "ret"),
        ("L", "vl_next"),
        ("I", "add x17, x17, x14"), ("I", "sub w13, w13, #1"), ("I", "b {vl_loop}"),
        ("L", "vl_miss"),
        ("I", "mov x0, #0"), ("I", "ret"),
    ]


def _letter_or(reg, target, tag):
    """Branch to `target` when the byte in `reg` is not a letter; fall through when it is.
    Letter = ASCII alnum or any byte >= 0x80 (part of a multi-byte UTF-8 letter). Clobbers w12."""
    return [
        ("I", f"cmp {reg}, #0x80"), ("I", f"b.hs {{{tag}}}"),
        ("I", f"sub w12, {reg}, #0x30"), ("I", "cmp w12, #10"), ("I", f"b.lo {{{tag}}}"),
        ("I", f"orr w12, {reg}, #0x20"), ("I", "sub w12, w12, #0x61"), ("I", "cmp w12, #26"),
        ("I", f"b.lo {{{tag}}}"),
        ("I", f"b {{{target}}}"),
        ("L", tag),
    ]


def loader(v: Version, path_addr, pool_addr):
    """Load the table once (idempotent; guarded by state.magic/lock/retry): read
    translation.bin into the persistent bss std::string, validate DBITRNS, publish
    state.tableptr + magic."""
    return [
        ("I", "stp x29, x30, [sp, #-0x20]!"),
        ("I", "str x19, [sp, #0x10]"),
        ("ADRP", 19, v.state), ("I", f"add x19, x19, #{v.state & 0xFFF:#x}"),
        # Self-heal launcher-leftover state: DBI never zeroes this bss tail, so a chain-loader
        # can leave a garbage lock (reads as held) or retry (reads as exhausted) that would
        # silently block loading. Zero lock/retry once, gated by the full-64-bit state-ready
        # sentinel so a re-entrant call skips it and the recursion guard holds.
        ("I", "ldr x9, [x19, #8]"), ("I", f"movz x10, #{STATE_READY_HI:#x}, lsl #48"),
        ("I", "cmp x9, x10"), ("I", "b.eq {sh_done}"),
        ("I", "str xzr, [x19]"),           # lock=0 and retry=0 (adjacent u32 fields)
        ("I", "str x10, [x19, #8]"),        # state_ready = sentinel
        ("L", "sh_done"),
        ("I", "ldr x9, [x19, #0x10]"), ("LDRLIT", 10, pool_addr),
        ("I", "cmp x9, x10"), ("I", "b.eq {ld_ret}"),      # already loaded
        ("I", "ldr w9, [x19]"), ("I", "cbnz w9, {ld_ret}"),          # lock held
        ("I", "ldr w9, [x19, #4]"), ("I", "cmp w9, #30"), ("I", "b.hs {ld_ret}"),
        ("I", "mov w9, #1"), ("I", "str w9, [x19]"),                 # lock = 1
        # reader args: X0=len, X1=ptr, X8=out
        ("I", "mov x0, #32"),
        ("ADRP", 1, path_addr), ("I", f"add x1, x1, #{path_addr & 0xFFF:#x}"),
        ("ADRP", 8, v.persist), ("I", f"add x8, x8, #{v.persist & 0xFFF:#x}"),
        ("I", f"bl {v.reader_fn:#x}"),
        ("ADRP", 9, v.persist), ("I", f"add x9, x9, #{v.persist & 0xFFF:#x}"),
        ("I", "ldr x10, [x9]"),          # buf = string.data
        ("I", "ldr x11, [x9, #8]"),      # len = string.len
        ("I", "cmp x11, #32"), ("I", "b.lo {ld_fail}"),
        ("I", "ldr x12, [x10]"), *movk_seq(13, FILE_MAGIC),
        ("I", "cmp x12, x13"), ("I", "b.ne {ld_fail}"),
        ("I", "ldr w15, [x10, #8]"),     # version: 2 = plain, 3 = plain + hash index
        ("I", "cmp w15, #2"), ("I", "b.eq {ld_ver}"),
        ("I", "cmp w15, #3"), ("I", "b.ne {ld_fail}"),
        ("L", "ld_ver"),
        # size check: reject a truncated/corrupt file whose header survived, else the
        # lookup would scan `count` entries past the short buffer -> OOB read -> crash.
        ("I", "ldr w12, [x10, #0xc]"),   # count
        ("I", "ldr w13, [x10, #0x10]"),  # stride
        ("I", "umull x12, w12, w13"),    # count*stride
        ("I", "add x12, x12, #0x20"),    # + 32-byte header
        ("I", "cmp w15, #2"), ("I", "b.eq {ld_size}"),
        # v3: u32 nbuckets (power of 2, non-zero) + 2*nbuckets u32 after the entries
        ("I", "add x13, x12, #4"), ("I", "cmp x11, x13"), ("I", "b.lo {ld_fail}"),
        ("I", "ldr w13, [x10, x12]"), ("I", "cbz w13, {ld_fail}"),
        ("I", "sub w14, w13, #1"), ("I", "tst w13, w14"), ("I", "b.ne {ld_fail}"),
        ("I", "add x12, x12, #4"), ("I", "add x12, x12, x13, lsl #3"),
        ("L", "ld_size"),
        ("I", "cmp x11, x12"), ("I", "b.ne {ld_fail}"),   # must equal the file length
        ("I", "str x10, [x19, #0x18]"),  # tableptr = buf
        ("LDRLIT", 9, pool_addr), ("I", "str x9, [x19, #0x10]"),    # magic = SET
        ("I", "str wzr, [x19]"), ("I", "b {ld_ret}"),                # lock = 0
        ("L", "ld_fail"),
        ("I", "ldr w9, [x19, #4]"), ("I", "add w9, w9, #1"), ("I", "str w9, [x19, #4]"),
        ("I", "str wzr, [x19]"),
        ("L", "ld_ret"),
        ("I", "ldr x19, [sp, #0x10]"), ("I", "ldp x29, x30, [sp], #0x20"), ("I", "ret"),
    ]


def ctor_exact(sl_addr, vl_addr):
    """(X0=dest, X1=data, X2=len) -> same registers, with X1/X2 replaced by the translation on
    an exact hit. Called from the entry stub of a std::string(const char*, size_t) copy, so
    only X0-X2 are live. Exact match only (no prefix/suffix rebuild): these constructors also
    build paths and file names. Skips strings longer than 0x100 or without a byte >= 0x80.
    Text that already is a translation is left alone. When the data continues past len and the
    whole NUL-terminated string is a translation, the whole translation is copied: DBI copies
    words with their Russian byte length (std::string w(tmp.data(), 14)) after translating tmp,
    which would cut "Видалити" to "Видалит". The other way round, a translation shorter than
    the Russian length (EN "LFS mode : -" for the 14-byte "LFS мод.: -") arrives with its NUL
    and stale stack bytes inside len: copied whole, DBI draws a NUL glyph or throws
    "Invalid UTF-8" (issue #29). When the bytes before a NUL inside len are a translation,
    the copy is cut at that NUL."""
    return [
        ("I", "cbz x2, {ce_ret}"),
        ("I", "cmp x2, #0x100"), ("I", "b.hi {ce_ret}"),
        ("I", "mov x9, #0"),
        ("L", "ce_nscan"),                          # NUL inside len?
        ("I", "ldrb w10, [x1, x9]"), ("I", "cbz w10, {ce_nul}"),
        ("I", "add x9, x9, #1"), ("I", "cmp x9, x2"), ("I", "b.lo {ce_nscan}"),
        ("I", "b {ce_start}"),
        ("L", "ce_nul"),
        ("I", "cbz x9, {ce_ret}"),
        ("I", "stp x29, x30, [sp, #-0x30]!"),
        ("I", "stp x0, x1, [sp, #0x10]"), ("I", "stp x2, x9, [sp, #0x20]"),
        ("I", "mov x0, x1"), ("I", "mov x1, x9"),
        ("I", f"bl {vl_addr:#x}"),                  # is the text before the NUL a translation?
        ("I", "mov x10, x0"),
        ("I", "ldp x0, x1, [sp, #0x10]"), ("I", "ldp x2, x9, [sp, #0x20]"),
        ("I", "ldp x29, x30, [sp], #0x30"),
        ("I", "cbz x10, {ce_ret}"),                 # no: leave the copy alone
        ("I", "mov x2, x9"), ("I", "ret"),          # yes: copy up to the NUL
        ("L", "ce_start"),
        ("I", "mov x9, #0"),
        ("L", "ce_scan"),
        ("I", "ldrb w10, [x1, x9]"), ("I", "cmp w10, #0x80"), ("I", "b.hs {ce_go}"),
        ("I", "add x9, x9, #1"), ("I", "cmp x9, x2"), ("I", "b.lo {ce_scan}"),
        ("L", "ce_ret"),
        ("I", "ret"),
        ("L", "ce_go"),
        ("I", "stp x29, x30, [sp, #-0x30]!"),
        ("I", "stp x0, x1, [sp, #0x10]"), ("I", "str x2, [sp, #0x20]"),
        ("I", "mov x0, x1"), ("I", "mov x1, x2"),
        ("I", f"bl {vl_addr:#x}"),                  # already a translation -> unchanged
        ("I", "cbnz x0, {ce_keep}"),
        ("I", "ldp x0, x1, [sp, #0x10]"), ("I", "ldr x2, [sp, #0x20]"),
        ("I", "ldrb w9, [x1, x2]"), ("I", "cbz w9, {ce_key}"),   # data ends at len
        ("I", "mov x9, x2"),
        ("L", "ce_len"),                            # bounded strlen
        ("I", "ldrb w10, [x1, x9]"), ("I", "cbz w10, {ce_lend}"),
        ("I", "add x9, x9, #1"), ("I", "cmp x9, #0x100"), ("I", "b.lo {ce_len}"),
        ("I", "b {ce_key}"),
        ("L", "ce_lend"),
        ("I", "str x9, [sp, #0x28]"),
        ("I", "mov x0, x1"), ("I", "mov x1, x9"),
        ("I", f"bl {vl_addr:#x}"),                  # is the whole string a translation?
        ("I", "cbz x0, {ce_key}"),
        ("I", "ldp x0, x1, [sp, #0x10]"), ("I", "ldr x2, [sp, #0x28]"),
        ("I", "ldp x29, x30, [sp], #0x30"), ("I", "ret"),
        ("L", "ce_key"),
        ("I", "ldr x0, [sp, #0x18]"), ("I", "ldr x1, [sp, #0x20]"),
        ("I", f"bl {sl_addr:#x}"),                  # (x0=key, x1=len) -> (x0=tr|0, x1=trlen)
        ("I", "cbz x0, {ce_keep}"),
        ("I", "mov x2, x1"), ("I", "mov x1, x0"), ("I", "ldr x0, [sp, #0x10]"),
        ("I", "ldp x29, x30, [sp], #0x30"), ("I", "ret"),
        ("L", "ce_keep"),
        ("I", "ldp x0, x1, [sp, #0x10]"), ("I", "ldr x2, [sp, #0x20]"),
        ("I", "ldp x29, x30, [sp], #0x30"), ("I", "ret"),
    ]


def make_fmt(v: Version, sl_addr):
    # fmt hook (B-entry, no LR saved at the site). x0=fmt_ptr, x1=fmt_len, x2=argdesc, x3=args,
    # x8=out. Calls _shared_lookup on the template (no gate: it returns 0 until the table loads,
    # so an early call just misses); on a hit x0/x1 become the English template. x2/x3/x8 survive
    # the leaf call, so only the template is saved/restored.
    #
    # arg-translate: the value words on "label : {}" rows (e.g. Да/Нет/Разрешено) are fmt
    # ARGUMENTS, not template text, so the template swap never reaches them. When argdesc(x2)==0xC
    # the sole arg is a char* at [x3]; if it leads with a Cyrillic byte, translate it and overwrite
    # the pointer with the (NUL-terminated) table value. x2/x3 survive the template lookup.
    arg = [
        ("I", "cmp x2, #0xc"), ("I", "b.ne {fargd}"),
        ("I", "ldr x9, [x3]"),                 # arg0 char*
        ("I", "ldrb w10, [x9]"), ("I", "cmp w10, #0x80"), ("I", "b.lo {fargd}"),  # ASCII-lead -> skip
        ("I", "mov x10, x9"),
        ("L", "fslen"), ("I", "ldrb w11, [x10], #1"), ("I", "cbnz w11, {fslen}"),
        ("I", "sub x11, x10, x9"), ("I", "sub x11, x11, #1"),   # strlen(arg0)
        ("I", "stp x0, x1, [sp, #0x10]"),      # save final template across the arg lookup
        ("I", "mov x0, x9"), ("I", "mov x1, x11"), ("I", f"bl {sl_addr:#x}"),
        ("I", "cbz x0, {fargr}"),
        ("I", "str x0, [x3]"),                 # overwrite arg0 with the English value ptr
        ("L", "fargr"),
        ("I", "ldp x0, x1, [sp, #0x10]"),      # restore final template
        ("L", "fargd"),
    ]
    return [
        ("I", "stp x29, x30, [sp, #-0x20]!"),
        ("I", "stp x0, x1, [sp, #0x10]"),      # save orig template (sl clobbers x0/x1)
        ("I", f"bl {sl_addr:#x}"),             # (x0=ptr,x1=len) -> (x0=tr|0, x1=trlen)
        ("I", "cbnz x0, {fhit}"),
        ("I", "ldp x0, x1, [sp, #0x10]"),      # miss: restore original template
        ("L", "fhit"),
    ] + arg + [
        ("I", "ldp x29, x30, [sp], #0x20"),
        ("I", "sub sp, sp, #0x260"), ("I", f"b {v.fmt.resume:#x}"),
    ]


def make_pfxsfx(v: Version, sl_addr, vl_addr):
    """_pfxsfx2(x0=data, x1=len) -> (x0=ptr, x1=len). Preserves x19-x28.
    0. Skip a leading run of control bytes (<0x20): in-place progress lines carry a leading
       \\r cursor-reset. x28 keeps the original ptr; a miss returns (x28, full len) so the \\r
       survives, a hit re-prepends the skipped bytes.
    1. exact lookup.
    0b. text that already is a translation is returned unchanged (no second pass).
    2. gate: bail to the original unless len<=256 and a byte is >=0x80 (Cyrillic), keeping
       ASCII byte-progress off the O(len) scan.
    3. longest-prefix + longest-suffix rebuild in SCRATCH (lead bytes prepended). A prefix or
       suffix hit counts only on a word boundary, so the key "Да" cannot match "Дампити"."""
    return [
        ("I", "stp x29, x30, [sp, #-0x60]!"), ("I", "mov x29, sp"),
        ("I", "stp x19, x20, [sp, #0x10]"), ("I", "stp x21, x22, [sp, #0x20]"),
        ("I", "stp x23, x24, [sp, #0x30]"), ("I", "stp x25, x26, [sp, #0x40]"),
        ("I", "stp x27, x28, [sp, #0x50]"),
        ("I", "mov x19, x0"), ("I", "mov x20, x1"),
        # (0) lead-control skip: x28 = original ptr; advance x19/x20 past bytes <0x20
        ("I", "mov x28, x19"),
        ("L", "lead"),
        ("I", "cbz x20, {leadd}"),
        ("I", "ldrb w9, [x19]"), ("I", "cmp w9, #0x20"), ("I", "b.hs {leadd}"),
        ("I", "add x19, x19, #1"), ("I", "sub x20, x20, #1"), ("I", "b {lead}"),
        ("L", "leadd"),
        # (0b) already a translation (another hook ran first): leave it alone
        ("I", "mov x0, x19"), ("I", "mov x1, x20"), ("I", f"bl {vl_addr:#x}"),
        ("I", "cbnz x0, {miss}"),
        # (1) exact
        ("I", "mov x0, x19"), ("I", "mov x1, x20"), ("I", f"bl {sl_addr:#x}"),
        ("I", "cbnz x0, {out}"),
        # (2) gate
        ("I", "cmp x20, #0x100"), ("I", "b.hi {miss}"),
        ("I", "cmp x20, #2"), ("I", "b.lt {miss}"),
        ("I", "mov x11, #0"),
        ("L", "ds"),
        ("I", "cmp x11, x20"), ("I", "b.ge {miss}"),
        ("I", "ldrb w13, [x19, x11]"), ("I", "cmp w13, #0x80"), ("I", "b.hs {dgo}"),
        ("I", "add x11, x11, #1"), ("I", "b {ds}"),
        ("L", "dgo"),
        # (3) longest prefix + longest suffix
        ("I", "mov x21, #0"), ("I", "mov x24, #0"), ("I", "mov x27, x20"),
        ("L", "pfx"),
        ("I", "cmp x27, #2"), ("I", "b.lt {pfxd}"),
        ("I", "mov x0, x19"), ("I", "mov x1, x27"), ("I", f"bl {sl_addr:#x}"),
        ("I", "cbz x0, {pfxn}"),
        # word boundary: the key's last byte or the byte after it must be a non-letter
        ("I", "add x9, x19, x27"), ("I", "ldurb w10, [x9, #-1]"), ("I", "ldrb w11, [x9]"),
    ] + _letter_or("w10", "pfxok", "pfx_l1") + _letter_or("w11", "pfxok", "pfx_l2") + [
        ("I", "b {pfxn}"),
        ("L", "pfxok"),
        ("I", "mov x21, x27"), ("I", "mov x22, x0"), ("I", "mov x23, x1"), ("I", "b {pfxd}"),
        ("L", "pfxn"), ("I", "sub x27, x27, #1"), ("I", "b {pfx}"),
        ("L", "pfxd"),
        ("I", "mov x27, x20"),
        ("L", "sfx"),
        ("I", "cmp x27, #2"), ("I", "b.lt {sfxd}"),
        ("I", "sub x9, x20, x27"), ("I", "add x0, x19, x9"), ("I", "mov x1, x27"), ("I", f"bl {sl_addr:#x}"),
        ("I", "cbz x0, {sfxn}"),
        # word boundary: the key's first byte or the byte before it must be a non-letter
        ("I", "sub x9, x20, x27"), ("I", "add x9, x19, x9"),
        ("I", "ldrb w10, [x9]"), ("I", "ldurb w11, [x9, #-1]"),
    ] + _letter_or("w10", "sfxok", "sfx_l1") + _letter_or("w11", "sfxok", "sfx_l2") + [
        ("I", "b {sfxn}"),
        ("L", "sfxok"),
        ("I", "mov x24, x27"), ("I", "mov x25, x0"), ("I", "mov x26, x1"), ("I", "b {sfxd}"),
        ("L", "sfxn"), ("I", "sub x27, x27, #1"), ("I", "b {sfx}"),
        ("L", "sfxd"),
        ("I", "orr x9, x21, x24"), ("I", "cbz x9, {miss}"),
        ("I", "add x9, x21, x24"), ("I", "cmp x9, x20"), ("I", "b.ls {noov}"), ("I", "mov x24, #0"),
        ("L", "noov"),
        ("I", "sub x10, x20, x21"), ("I", "sub x10, x10, x24"),
        ("I", "mov x11, x10"),
        ("I", "cbz x21, {t1}"), ("I", "add x11, x11, x23"),
        ("L", "t1"), ("I", "cbz x24, {t2}"), ("I", "add x11, x11, x26"),
        ("L", "t2"),
        ("I", "sub x9, x19, x28"),        # leadn (skipped leading control bytes)
        ("I", "add x11, x11, x9"),        # total length includes the lead
        ("I", "cmp x11, #0x200"), ("I", "b.hi {miss}"),
        ("ADRP", 12, v.scratch), ("I", f"add x12, x12, #{v.scratch & 0xFFF:#x}"),
        ("I", "mov x13, x12"),
        ("I", "cbz x9, {nolead}"),        # prepend the skipped leading control bytes to SCRATCH
        ("I", "mov x14, x28"),
        ("L", "lp2"),
        ("I", "ldrb w15, [x14], #1"), ("I", "strb w15, [x13], #1"),
        ("I", "subs x9, x9, #1"), ("I", "b.ne {lp2}"),
        ("L", "nolead"),
        ("I", "cbz x21, {cm}"),
        ("I", "mov x14, x22"), ("I", "mov x15, x23"),
        ("L", "cp"),
        ("I", "ldrb w9, [x14], #1"), ("I", "strb w9, [x13], #1"),
        ("I", "subs x15, x15, #1"), ("I", "b.ne {cp}"),
        ("L", "cm"),
        ("I", "add x14, x19, x21"), ("I", "mov x15, x10"), ("I", "cbz x15, {cs}"),
        ("L", "cmid"),
        ("I", "ldrb w9, [x14], #1"), ("I", "strb w9, [x13], #1"),
        ("I", "subs x15, x15, #1"), ("I", "b.ne {cmid}"),
        ("L", "cs"),
        ("I", "cbz x24, {done}"),
        ("I", "mov x14, x25"), ("I", "mov x15, x26"),
        ("L", "csf"),
        ("I", "ldrb w9, [x14], #1"), ("I", "strb w9, [x13], #1"),
        ("I", "subs x15, x15, #1"), ("I", "b.ne {csf}"),
        ("L", "done"),
        ("I", "mov x0, x12"), ("I", "mov x1, x11"), ("I", "b {out}"),
    ] + [
        ("L", "miss"),
        # no translation: return the ORIGINAL (x28, full len) so leading control bytes
        # survive, then fall into the shared epilogue.
        ("I", "sub x9, x19, x28"), ("I", "add x1, x20, x9"), ("I", "mov x0, x28"),
        ("L", "out"),
        # hits arrive with x0/x1 already final (exact or prefix/suffix); the prefix/suffix
        # path prepended any lead bytes itself. An exact hit after a lead skip drops the lead
        # -- a cosmetic \r on a transient line; the N/N scan line is prefix/suffix and keeps it.
        ("I", "ldp x27, x28, [sp, #0x50]"), ("I", "ldp x25, x26, [sp, #0x40]"),
        ("I", "ldp x23, x24, [sp, #0x30]"), ("I", "ldp x21, x22, [sp, #0x20]"),
        ("I", "ldp x19, x20, [sp, #0x10]"), ("I", "ldp x29, x30, [sp], #0x60"),
        ("I", "ret"),
    ]
