# Vendored Runtime-Translation Engine

## Origin

- **Upstream**: [0xroast/dbi-translate](https://github.com/0xroast/dbi-translate) (MIT).
- **Base commit**: `1320e138fd017db70c1436b537aef7be030f0668`.
- **Location here**: [`vendor/dbi_translate/`](vendor/dbi_translate/), with the upstream `LICENSE` and a `NOTICE` that lists every local change.

The engine is part of this repository. `scripts/patch_dbi.py` imports it directly; it no longer clones upstream at build time.

## Local changes to the engine

1. **DBI 912 support** (`V912` in `versions.py`). The five hook sites were matched to 905 by instruction sequence; the instruction words are identical. The 912 `.text` zero tail is only 0x244 bytes (the runtime needs 0x4B8), so the runtime goes into an unreferenced libde265 function at `0x939DAC` (5208 bytes), zeroed before use.
2. **Patcher state moved out of DBI's TLS block** (905 and 912). The state, the persistent string and the scratch buffer used to sit on the last bss page, below MOD0 `__bss_end__`. That range is the main thread's static TLS block, where DBI decrypts its UI strings, so DBI strings and the patcher state could overwrite each other. The state now sits between `__bss_end__` and the image end, and MOD0 `bss_end` is raised to the image end so crt0 zeroes it on every boot. `patch_nro` rejects any state area inside `__bss_end__`.
3. **Line-length gate** of `make_pfxsfx` raised from 128 to 256 bytes (formerly a text replacement in `patch_dbi.py`).
4. **Game info panel labels** (`Контент`, `Тикеты`, `Сохранения`, `Язык`, ...; issue #25 §3). DBI has ~43 copies of `std::string(const char*, size_t)`, one per translation unit, and the panel uses one the `ctor` hook does not cover (912 `0x43B6F0`, 905 `0x435CA0`). That copy gets a 5-instruction entry stub into an exact-match translator (`ctor_exact` in `runtime.py`): strings without a byte ≥ 0x80 or longer than 256 bytes are skipped, and there is no prefix/suffix rebuild, so paths and file names stay intact. Hooking all copies hangs DBI 912 at a black screen (the group `0x4F2910`–`0x5BC160` triggers it; cause not found), so further copies are added one at a time after a console test.
5. **905 code cave.** The 905 `.text` zero tail (0x4C4 bytes) is full, so the 905 runtime now lives in the same unreferenced libde265 function as 912 (`0x90B4A4`, identical 1302-instruction body, no reference from outside).
6. **Matcher rules** (`make_pfxsfx`, `ctor_exact`):
   - Text that already is a translation is never translated again (`value_lookup`). Several hooks see the same text, and for Cyrillic targets (UA/BE/KK) a translation can start with a Russian key: "Дампити на SD-карту" became "Такмпити на SD-карту" through the key "Да".
   - A prefix or suffix hit counts only on a word boundary (the key ends or starts with a non-letter, or the neighbouring byte is a non-letter).
   - DBI builds some menu words as `std::string tmp(slot, 14); std::string w(tmp.data(), 14);`. When the hooked copy is asked for a prefix of a whole translation, it copies the whole translation, so "Видалити" is not cut to "Видалит".
7. **Hash index (DBITRNS version 3).** `scripts/build_translation_bin.py` appends an FNV-1a open-addressing index for keys and for translations; the runtime probes it instead of scanning every entry. Measured in Unicorn on DBI 912 with the UA table: a 71-byte line with no match 1.74 M → 42 K instructions, an exact hit 23 K → 0.9 K. Version 2 tables (`--format 2`) still load and fall back to the linear scan; NROs patched before version 3 reject version 3 tables.

Tests: `tests/test_runtime_rules.py` runs the injected loader and matchers of patched 905/912 builds in Unicorn and compares them with the Python model in `tools/porting/emu_runtime.py` (set `DBI_905_NRO` / `DBI_912_NRO`).

## Supported DBI releases

| DBI | Pristine NRO SHA-256 |
|---|---|
| 905 | `f4360db14ea7ed1043a5a0c7d076d4861cc3383f3b254b9b38d2eec6d175686f` |
| 912 | `e77da77f95a24f94fb39df23513961846a75d07aa2f970f39846ed7bbbd22bd2` |

`patch_dbi.py` detects the version from the input SHA-256 and rejects any other file.

## Embedded Cyrillic Font-Glyph Repair Stage

After the engine patch, `scripts/patch_dbi.py` applies an in-memory bitmap font repair before writing the patched NRO. This logic is adapted from [Bohdan Buinich](https://github.com/BohdanBuinich)'s reference implementation for `dbi-i18n`.

### Repaired Unicode Destinations
The pristine Russian DBI font lacks Ukrainian, Belarusian, and Kazakh glyphs. The repair stage derives exactly six destination glyphs from existing glyphs:
- `U+0404` (Є): Horizontally mirrors each little-endian 16-bit bitmap row from `U+042D` (Э).
- `U+0454` (є): Horizontally mirrors each little-endian 16-bit bitmap row from `U+044D` (э).
- `U+0406` (І): Direct copy from Latin `U+0049` (I).
- `U+0456` (і): Direct copy from Latin `U+0069` (i).
- `U+0407` (Ї): Direct copy from Latin `U+00CF` (Ï).
- `U+0457` (ї): Direct copy from Latin `U+00EF` (ï).

All other 65,530 glyphs remain untouched.

### Dynamic Frame Discovery & Trust Boundary
- **Automatic Frame Discovery**: The wrapper searches the binary for Zstandard frame candidates (magic bytes `28 B5 2F FD`) that decompress to exactly 2,097,152 bytes (65,536 glyphs × 32 bytes). Exactly one supported frame must exist; zero or multiple matching frames trigger a hard error.
- **Fit & Recompression**: The repaired font is recompressed at Zstandard level 18 while preserving the original frame checksum flag and content size header. If the recompressed frame exceeds the original compressed slot size, patching is rejected.
- **Round-Trip Validation**: The repacked frame is decompressed from the in-memory NRO buffer and verified byte-for-byte against the expected repaired font before the final output file is written.
