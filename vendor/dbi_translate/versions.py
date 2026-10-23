"""Per-version patch configuration. Adding a DBI version is a new Version entry here."""

from __future__ import annotations

from dataclasses import dataclass

BASE = 0x7100000000   # NRO load address; the offsets below are file offsets
CTOR_INSN = 0x91004005   # ADD X5,X0,#0x10: first insn of std::string(const char*, size_t)


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
    # Entry points of the std::string(const char*, size_t) copies (one per translation unit,
    # first instruction CTOR_INSN). Each gets an exact-match hook; the game info panel builds
    # its labels (Контент, Тикеты, Язык, ...) through them, not through `ctor`.
    ctors: tuple[int, ...] = ()


V905 = Version(
    name="905",
    # The .text zero tail (0xB90B3C..0xB91000, 0x4C4 bytes) is full; use the same unreferenced
    # libde265 function as 912 (identical 1302-instruction body, no reference from outside).
    cave=(0x90B4A4, 0x90B4A4 + 5208),
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
    clear_cave=True,
    ctors=(0x435CA0,),                                  # = 912 0x43B6F0 (game info panel, 205 calls)
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
    # Only the copy the game info panel uses. Hooking all 43 copies hangs DBI at a black
    # screen (the copies at 0x4F2910..0x5BC160 are enough to trigger it; cause not found),
    # so copies are opted in one at a time, each with a console test.
    ctors=(0x43B6F0,),
)

# 920: sites matched to 912 by instruction sequence (all five words identical). Only 0x248
# bytes are free past __bss_end__, so the state area is packed without 912's 0x40 gap after
# persist: scratch ends exactly at the image end (pfxsfx writes at most 0x200 bytes, no NUL).
V920 = Version(
    name="920",
    cave=(0x95120C, 0x95120C + 5208),
    state=0x1274DC0,             # __bss_end__ = 0x1274DB8, image end = 0x1275000
    persist=0x1274DE0,
    scratch=0x1274E00,
    reader_fn=0x147A70,
    reader=Site(0x147A70, 0xA9B87BFD, 0x147A74, "B"),   # STP X29,X30,[SP,#-0x80]!
    fmt=Site(0x705EB0, 0xD10983FF, 0x705EB4, "B"),      # SUB SP,SP,#0x260
    glog=Site(0x1B41D0, 0xA9B77BFD, 0x1B41D4, "B"),     # STP X29,X30,[SP,#-0x90]!
    ctor=Site(0x7EC60, 0xA9BD7BFD, 0x7EC64, "B"),       # STP X29,X30,[SP,#-0x30]!
    sink=Site(0x6869A0, 0xAA0103F6, 0x6869A4, "BL"),    # MOV X22,X1
    clear_cave=True,
    bss_end=(0xFC, 0x1274CC8, 0x1274F10),               # MOD0 @0xF0: bss_end 0x1274DB8 -> 0x1275000
    ctors=(0x442A60,),                                  # = 912 0x43B6F0 (game info panel, 205 calls)
)

VERSIONS = {v.name: v for v in (V905, V912, V920)}
