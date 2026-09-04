# Upstream Assembly Patcher Integration

## Repository & Pinned Revision

- **Upstream Repository**: [0xroast/dbi-translate](https://github.com/0xroast/dbi-translate)
- **Pinned Commit SHA**: `1320e138fd017db70c1436b537aef7be030f0668`

## DBI 905 Compatibility

The upstream patcher is specifically designed and validated for **DBI 905** (`DBI.905.ru.nro` from official release [905ru](https://github.com/rashevskyv/dbi/releases/tag/905ru), SHA-256 `f4360db14ea7ed1043a5a0c7d076d4861cc3383f3b254b9b38d2eec6d175686f`). It performs ARM64 binary patching against the uncompressed and unpatched DBI binary to inject runtime translation loading hooks and hook string lookup tables into the `.text` code cave.

Because offset mappings and assembly instructions are specific to DBI 905, running this patcher against other DBI versions is not supported and will fail verification.

## Why Upstream Code Is Not Vendored or Submoduled

1. **No Code Redundancy**: This repository is focused strictly on the translation dataset and localization pipeline (`dictionary.xlsx`, AI translation, validation, and `.bin` serialization).
2. **Ephemeral Wrapper**: The wrapper script (`scripts/patch_dbi.py`) clones the upstream repository into a temporary directory (`tempfile.TemporaryDirectory()`), verifies the exact pinned commit hash (`git rev-parse HEAD`), executes the patch CLI, and automatically deletes the temporary clone. No upstream files persist in this repository.
3. **No Unintentional Drifts**: Pinned checkout ensures reproducible patching without git submodule maintenance overhead or accidental divergence.

## Licensing

The upstream repository is MIT licensed. To maintain separation between translation dataset development and patching tooling, no upstream source code or binary patcher assets are vendored or committed into this repository.

## Patching Prerequisites

To execute the wrapper:
- **Python**: >= 3.10 with `keystone-engine==0.9.2`, `capstone==5.0.9`, and `zstandard>=0.23,<1`
- **Pristine DBI NRO**: A clean, untampered `DBI.905.ru.nro` matching SHA-256 `f4360db14ea7ed1043a5a0c7d076d4861cc3383f3b254b9b38d2eec6d175686f`
- No WSL, devkitA64 toolchain, or external assembler is required.

## Embedded Cyrillic Font-Glyph Repair Stage

Following the upstream assembly patch stage, `scripts/patch_dbi.py` applies an in-memory bitmap font repair before emitting the final patched NRO. This logic is adapted from [Bohdan Buinich](https://github.com/BohdanBuinich)'s reference implementation for `dbi-i18n`.

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
- **Automatic Frame Discovery**: Rather than relying on fragile hardcoded offsets, the wrapper searches the binary for Zstandard frame candidates (magic bytes `28 B5 2F FD`) that decompress to exactly 2,097,152 bytes (65,536 glyphs × 32 bytes). Exactly one supported frame must exist; zero or multiple matching frames trigger a hard error.
- **Fit & Recompression**: The repaired font is recompressed at Zstandard level 18 while preserving the original frame checksum flag and content size header. If the recompressed frame exceeds the original compressed slot size, patching is rejected.
- **Round-Trip Validation**: The repacked frame is decompressed from the in-memory NRO buffer and verified byte-for-byte against the expected repaired font before the final output file is written.
- **No External Font Binary or Fixed Offset**: The entire 2 MiB font is decoded, transformed, and validated directly from the binary itself without vendoring external font assets or hardcoding legacy DBI 810 offsets.
