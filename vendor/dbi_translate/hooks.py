"""The five hook trampolines. Each saves what the matcher clobbers, calls it, re-runs
the instruction displaced from the site, and branches back to resume."""

from __future__ import annotations

from .versions import Version


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
