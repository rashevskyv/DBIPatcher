# Upstream Assembly Patcher Integration

## Repository & Pinned Revision

- **Upstream Repository**: [BohdanBuinich/dbi-i18n](https://github.com/BohdanBuinich/dbi-i18n)
- **Pinned Commit SHA**: `f1f8bebec2b423694e8f058f2d3540a35382b1fd`

## DBI 898 Compatibility

The upstream patcher is specifically designed and validated for **DBI 898** (`DBI.898.ru.nro`). It performs ARM64 binary patching against the uncompressed and unpatched DBI binary to inject runtime translation loading hooks and hook string lookup tables.

Because offset mappings and assembly instructions are specific to DBI 898, running this patcher against other DBI versions is not supported and will fail or produce invalid binaries.

## Why Upstream Code Is Not Vendored or Submoduled

1. **No Code Redundancy**: This repository is focused strictly on the translation dataset and localization pipeline (`dictionary.xlsx`, AI translation, validation, and `.bin` serialization).
2. **Ephemeral Wrapper**: The wrapper script (`scripts/patch_dbi.py`) clones the upstream repository into a temporary directory (`tempfile.TemporaryDirectory()`), verifies the exact pinned commit hash (`git rev-parse HEAD`), executes the patch CLI, and automatically deletes the temporary clone. No upstream files persist in this repository.
3. **No Unintentional Drifts**: Pinned checkout ensures reproducible patching without git submodule maintenance overhead or accidental divergence.

## Licensing Caveat

The upstream repository currently does not include a standalone `LICENSE` file. To respect intellectual property and licensing boundaries, no upstream source code or binary patcher assets are vendored, distributed, or committed into this repository. Developers running the patch stage clone upstream ephemerally to build patched NRO binaries for their own local use.

## Patching Prerequisites

To execute the wrapper:
- **Environment**: Linux / WSL (Debian/Ubuntu)
- **Python**: >= 3.12 with `zstandard>=0.23,<1`
- **devkitPro**: `devkitA64` toolchain installed at `/opt/devkitpro` (specifically `aarch64-none-elf-as` and related utilities)
- **Pristine DBI NRO**: A clean, untampered `DBI.898.ru.nro`
