"""Per-version patch configuration. Adding a DBI version is a new Version entry here."""

from __future__ import annotations

from dataclasses import dataclass

BASE = 0x7100000000   # NRO load address; the offsets below are file offsets


@dataclass(frozen=True)
class Site:
    """A hook site: the patched offset, the instruction it replaces (verified and
    re-run inside the hook), where the hook branches back to, and the branch style.
    entry='B' for a function's first instruction (LR not yet saved); 'BL' where LR
    is already saved."""

    addr: int
    insn: int
    resume: int
    entry: str


@dataclass(frozen=True)
class Version:
    """Everything the builder needs to target one DBI release."""

    name: str
    cave: tuple[int, int]        # [start, end) zero-fill in .text
    state: int                   # +0 lock, +4 retry, +8 state-ready, +0x10 magic, +0x18 tableptr
    persist: int                 # 32-byte std::string the loader fills and leaks
    scratch: int                 # rebuild buffer
    reader_fn: int               # file reader the loader calls (X0=len, X1=path, X8=out)
    reader: Site
    fmt: Site
    glog: Site
    ctor: Site
    sink: Site
    clear_cave: bool = False     # cave is a dead function, not a zero tail: zero it first
    # MOD0 bss_end field (addr, old word, new word). state/persist/scratch must lie past the
    # program's __bss_end__: the main thread's static TLS block (DBI's decrypted UI strings)
    # runs right up to it. Moving bss_end to the image end makes crt0 zero that tail on boot.
    bss_end: tuple[int, int, int] | None = None


V905 = Version(
    name="905",
    cave=(0xB90B3C, 0xB91000),
    state=0x11FE6E0,             # __bss_end__ = 0x11FE6D8, image end = 0x11FF000
    persist=0x11FE700,
    scratch=0x11FE760,
    reader_fn=0x143A80,
    reader=Site(0x143A80, 0xA9B87BFD, 0x143A84, "B"),   # STP X29,X30,[SP,#-0x80]!
    fmt=Site(0x6F6460, 0xD10983FF, 0x6F6464, "B"),      # SUB SP,SP,#0x260
    glog=Site(0x1AC470, 0xA9B77BFD, 0x1AC474, "B"),     # STP X29,X30,[SP,#-0x90]!
    ctor=Site(0x7E180, 0xA9BD7BFD, 0x7E184, "B"),       # STP X29,X30,[SP,#-0x30]!
    sink=Site(0x6771B0, 0xAA0103F6, 0x6771B4, "BL"),    # MOV X22,X1
    bss_end=(0xFC, 0x11FE5E8, 0x11FEF10),               # MOD0 @0xF0: bss_end 0x11FE6D8 -> 0x11FF000
)

# 912: the .text zero tail is only 0x244 bytes and the runtime needs 0x4b8, so the runtime
# goes into FUN_7100939dac (libde265, 5208 B). No branch, ADR, ADRP+ADD, RELR or data pointer
# reaches it. Sites were matched to 905 by instruction sequence; all five site words are
# identical to 905.
V912 = Version(
    name="912",
    cave=(0x939DAC, 0x939DAC + 5208),
    state=0x12789A0,             # __bss_end__ = 0x1278988, image end = 0x1279000
    persist=0x12789C0,
    scratch=0x1278A20,
    reader_fn=0x147510,
    reader=Site(0x147510, 0xA9B87BFD, 0x147514, "B"),   # STP X29,X30,[SP,#-0x80]!
    fmt=Site(0x6FCA60, 0xD10983FF, 0x6FCA64, "B"),      # SUB SP,SP,#0x260
    glog=Site(0x1B2650, 0xA9B77BFD, 0x1B2654, "B"),     # STP X29,X30,[SP,#-0x90]!
    ctor=Site(0x7E780, 0xA9BD7BFD, 0x7E784, "B"),       # STP X29,X30,[SP,#-0x30]!
    sink=Site(0x67E160, 0xAA0103F6, 0x67E164, "BL"),    # MOV X22,X1
    clear_cave=True,
    bss_end=(0xFC, 0x1278898, 0x1278F10),               # MOD0 @0xF0: bss_end 0x1278988 -> 0x1279000
)

VERSIONS = {v.name: v for v in (V905, V912)}
