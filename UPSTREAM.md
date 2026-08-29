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
- **Python**: >= 3.10 with `keystone-engine==0.9.2` and `capstone==5.0.9`
- **Pristine DBI NRO**: A clean, untampered `DBI.905.ru.nro` matching SHA-256 `f4360db14ea7ed1043a5a0c7d076d4861cc3383f3b254b9b38d2eec6d175686f`
- No WSL, devkitA64 toolchain, or external assembler is required.
