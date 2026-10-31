"""The five hook trampolines. Each saves what the matcher clobbers, calls it, re-runs
the instruction displaced from the site, and branches back to resume."""

from __future__ import annotations

from .versions import StringCall, Version


def string_call_stub(call: StringCall, translator):
    """Translate one UI argument, then tail-call the original function.

    Keep all volatile GPRs, SIMD registers and NZCV: the caller may use a more
    specific clobber set for a known internal function than the general ABI.
    x19-x29 are preserved by translate_string and DBI's append.
    """
    program = [("I", "sub sp, sp, #0x2b0")]
    program += [("I", f"stp x{i}, x{i+1}, [sp, #{i * 8:#x}]") for i in range(0, 18, 2)]
    program += [("I", "stp x18, x30, [sp, #0x90]"), ("I", "mrs x9, nzcv"),
                ("I", "str x9, [sp, #0xa0]")]
    program += [("I", f"stp q{i}, q{i+1}, [sp, #{0xB0 + i * 16:#x}]") for i in range(0, 32, 2)]
    for i in range(call.count):
        program += [("I", f"ldr x0, [sp, #{call.argument * 8:#x}]")]
        if i:
            program += [("I", f"add x0, x0, #{i * 0x20:#x}")]
        program += [("I", f"bl {translator:#x}")]
    program += [("I", f"ldp q{i}, q{i+1}, [sp, #{0xB0 + i * 16:#x}]") for i in range(0, 32, 2)]
    program += [("I", "ldr x9, [sp, #0xa0]"), ("I", "msr nzcv, x9")]
    program += [("I", f"ldp x{i}, x{i+1}, [sp, #{i * 8:#x}]") for i in range(0, 18, 2)]
    return program + [("I", "ldp x18, x30, [sp, #0x90]"), ("I", "add sp, sp, #0x2b0"),
                      ("I", f"b {call.target:#x}")]


def string_wrap_stub(site, translator):
    """Entry hook (B) of a join helper that returns a std::string in x0: run the helper, then
    translate its result. The helper is a normal call (full AAPCS clobbers, it calls DBI's
    append), so only x0 and the frame are kept."""
    return [
        ("I", "stp x29, x30, [sp, #-0x20]!"),
        ("I", "str x0, [sp, #0x10]"),
        ("I", "bl {sw_body}"),
        ("I", "ldr x0, [sp, #0x10]"),
        ("I", f"bl {translator:#x}"),
        ("I", "ldr x0, [sp, #0x10]"),
        ("I", "ldp x29, x30, [sp], #0x20"),
        ("I", "ret"),
        ("L", "sw_body"),
        ("I", "stp x29, x30, [sp, #-0x30]!"),   # displaced WRAP_INSN; returns to the wrapper
        ("I", f"b {site + 4:#x}"),
    ]


def glog_hook(v: Version, pfxsfx_addr):   # x0=glog, x1=len, x2=data, x3=a4
    """Global-log append hook. Own frame; translates (data,len), re-runs the displaced STP,
    and continues the append with the English (or the original on a miss)."""
    return [
        ("I", "stp x29, x30, [sp, #-0x20]!"),
        ("I", "stp x0, x3, [sp, #0x10]"),        # save glog, a4 (matcher clobbers them)
        ("I", "mov x0, x2"),                      # x0=data (x1=len already)
        ("I", f"bl {pfxsfx_addr:#x}"),            # -> x0=newdata, x1=newlen
        ("I", "mov x2, x0"),                      # x2=newdata
        ("I", "ldp x0, x3, [sp, #0x10]"),         # restore glog, a4
        ("I", "ldp x29, x30, [sp], #0x20"),
        ("I", "stp x29, x30, [sp, #-0x90]!"),     # displaced STP X29,X30,[SP,#-0x90]!
        ("I", f"b {v.glog.resume:#x}"),
    ]


def reader_hook(v: Version, loader_addr):   # x0=len, x1=ptr, x8=out (reader args)
    """Eager load on the first SD file access. Own frame; saves the reader's args across
    `bl loader`, re-runs the displaced STP, continues the reader. The loader's own read
    re-enters here but its lock makes the inner load a no-op."""
    return [
        ("I", "stp x29, x30, [sp, #-0x30]!"),
        ("I", "stp x0, x1, [sp, #0x10]"), ("I", "str x8, [sp, #0x20]"),
        ("I", f"bl {loader_addr:#x}"),
        ("I", "ldp x0, x1, [sp, #0x10]"), ("I", "ldr x8, [sp, #0x20]"),
        ("I", "ldp x29, x30, [sp], #0x30"),
        ("I", "stp x29, x30, [sp, #-0x80]!"),        # displaced reader first instruction
        ("I", f"b {v.reader.resume:#x}"),
    ]


def ctor_hook(v: Version, pfxsfx_addr):   # x0=dest, x1=data, x2=len
    """std::string-ctor hook (own frame). Translates (data,len), re-runs the displaced STP,
    and continues the ctor so it builds from the English (or the original on a miss)."""
    return [
        ("I", "stp x29, x30, [sp, #-0x20]!"),
        ("I", "str x0, [sp, #0x10]"),                # save dest (matcher clobbers x0)
        ("I", "mov x0, x1"), ("I", "mov x1, x2"),    # x0=data, x1=len
        ("I", f"bl {pfxsfx_addr:#x}"),               # -> x0=ptr, x1=len
        ("I", "mov x2, x1"), ("I", "mov x1, x0"),    # x2=len, x1=ptr
        ("I", "ldr x0, [sp, #0x10]"),                # x0=dest
        ("I", "ldp x29, x30, [sp], #0x20"),
        ("I", "stp x29, x30, [sp, #-0x30]!"),        # displaced ctor first instruction
        ("I", f"b {v.ctor.resume:#x}"),
    ]


def sink_hook(v: Version, pfxsfx_addr):   # x0=console obj, x1=len, x2=data
    """Write-line wrapper hook. Own frame; translates (data,len), re-runs the displaced
    MOV X22,X1 (x22=newlen; downstream x23<-x2 carries the data). Idempotent: a line that
    also reaches glog double-translates harmlessly (English is never a key)."""
    return [
        ("I", "stp x29, x30, [sp, #-0x20]!"), ("I", "mov x29, sp"),
        ("I", "str x19, [sp, #0x10]"),
        ("I", "mov x19, x0"), ("I", "mov x0, x2"),   # save obj; x0=data (x1=len already)
        ("I", f"bl {pfxsfx_addr:#x}"),                # -> x0=newdata, x1=newlen
        ("I", "mov x2, x0"), ("I", "mov x0, x19"),    # x2=newdata, x0=obj
        ("I", "ldr x19, [sp, #0x10]"), ("I", "ldp x29, x30, [sp], #0x20"),
        ("I", "mov x22, x1"), ("I", f"b {v.sink.resume:#x}"),   # displaced MOV X22,X1
    ]


def ctor_stub(site, ctor_exact_addr):
    """Entry stub for one std::string(const char*, size_t) copy (B-entry): run the exact-match
    translator on (x1, x2), re-run the displaced ADD X5,X0,#0x10 and continue the copy."""
    return [
        ("I", "stp x29, x30, [sp, #-0x10]!"),
        ("I", f"bl {ctor_exact_addr:#x}"),
        ("I", "ldp x29, x30, [sp], #0x10"),
        ("I", "add x5, x0, #0x10"),                   # displaced CTOR_INSN
        ("I", f"b {site + 4:#x}"),
    ]
