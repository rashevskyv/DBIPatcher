# 💎 DBI Patcher: Universal Localization

[English](README.md) | [Español](README_ES.md)

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/rashevskyv/DBIPatcher)](https://github.com/rashevskyv/DBIPatcher/releases)
[![GitHub downloads](https://img.shields.io/github/downloads/rashevskyv/DBIPatcher/total)](https://github.com/rashevskyv/DBIPatcher/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An advanced, AI-powered localization engine for [DBI](https://github.com/rashevskyv/dbi) — the ultimate Nintendo Switch homebrew tool. This project provides high-quality translations for 22+ languages, ensuring that every Switch user can enjoy DBI in their native tongue.

---

## 🌟 Features

- **🤖 AI-Powered Precision**: Uses **Claude 3.5 Sonnet** (via OmniRoad) or **gemini-3.6-flash** (via Web2API) to provide context-aware, literary-grade translations.
- **🌍 23+ Languages**: Comprehensive support from Ukrainian to Japanese, with automatic English fallbacks.
- **📏 Visual Perfection**: Smart alignment engine that ensures colons and brackets match the original UI layout.
- **✅ Strict Validation**: Automated checks for token preservation (`[[LF]]`, `[[TAB]]`), bracket balance, and placeholder integrity.
- **🚀 One-Click Deploy**: Fully automated pipeline from translation to GitHub Release.

---

## 🛠️ Supported Languages

| Code | Language | Code | Language |
| :--- | :--- | :--- | :--- |
| **UA** | Ukrainian | **EN** | English (US) |
| **BE** | Belarusian | **ENGB** | English (UK) |
| **PL** | Polish | **DE** | German |
| **FR** | French | **FRCA** | French (Canada) |
| **IT** | Italian | **ES** | Spanish (Spain) |
| **JP** | Japanese | **ES419** | Spanish (Latin America) |
| **KR** | Korean | **PT** | Portuguese (Portugal) |
| **ZHCN** | Simplified Chinese | **PTBR** | Portuguese (Brazil) |
| **ZHTW** | Traditional Chinese | **NL** | Dutch |
| **KK** | Kazakh | **ET** | Estonian |
| **LT** | Lithuanian | **LV** | Latvian |
| **TR** | Turkish | | |

---

## 📥 Installation

1. Go to the [Latest Release](https://github.com/rashevskyv/DBIPatcher/releases/latest).
2. Download the compatible **`DBI.nro`** and the `translation_XX.bin` for your language.
3. **Rename** the translation file to `translation.bin` (it must be exactly this name).
4. Place both files (`DBI.nro` and `translation.bin`) in the same folder on your SD card (usually `/switch/DBI/`).

> [!CAUTION]
> These translations are **strictly compatible only with the version of DBI provided in the release assets**. Using them with other versions of DBI may lead to layout issues or crashes.

---

## 🏗️ For Developers: Pipeline Usage

If you want to run the patcher locally:

### Prerequisites
- Python 3.12+
- GitHub CLI (`gh`) for deployment
- Access to Claude 3.5 API (via proxy)

### Local setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Translation quality checks
```powershell
# Validate the Spanish (Latin America) CSV and its binary output
python -m unittest discover -s tests -v

# Build only the ES-419 translation
python scripts/build_translation_bin.py translations/es419.csv -o output/translation_es419.bin

# Synchronize reviewed ES-419 strings with the master dictionary
python scripts/import_translation_csv.py es419
```

### DBI 905 NRO Patching
To patch a pristine `DBI.905.ru.nro` binary to support external runtime translations:
- Requires **Python 3.10+** with `keystone-engine==0.9.2`, `capstone==5.0.9`, and `zstandard>=0.23,<1`.
- Uses the pinned upstream patcher from [0xroast/dbi-translate](https://github.com/0xroast/dbi-translate) (see [UPSTREAM.md](UPSTREAM.md)).
- Automatically repairs embedded Cyrillic font glyphs (`Є`, `І`, `Ї`, `є`, `і`, `ї`) used by Ukrainian, Belarusian, and Kazakh translations directly in the shared patched NRO.

```powershell
python scripts/patch_dbi.py --nro /path/to/DBI.905.ru.nro --output DBI.905.ru_patched.nro
```

### Commands
```powershell
# Run the full test cycle (sync, translate, align, validate, build)
python -m src.main test

# Deploy a new version (Commit, Push, GitHub Release)
python -m src.main deploy

# Individual steps
python -m src.main sync       # Update dictionary from source CSVs
# Web2API translates independent rows concurrently; default is 4 workers (1..8).
$env:DBI_TRANSLATE_WORKERS=4; python -m src.main translate
python -m src.main align      # Fix UI alignment for specific blocks
python -m src.main validate   # Verify data integrity
python -m src.main build      # Generate binary .bin files
```

---

## ⚠️ Known Issues

- ~~**Hardcoded Strings**: Some interface elements are hardcoded within the DBI binary and cannot be localized via `translation.bin`. For example, confirmation prompts may still display in Russian: **Да** (Yes) and **Нет** (No).~~ ✅ Fixed!
- **Shadok Fables**: Satirical blocks use intentional adapted parody localization (not literal DBI Shadok translation) via `python -m src.main shadok`.
- ~~**System Language Names**: Names of languages in the DBI settings menu are hardcoded in the binary.~~ ✅ Fixed!
- **Launcher Compatibility**: Translations have been tested exclusively on [Kefir](https://github.com/rashevskyv/kefir). On Kefir, the translation works successfully regardless of whether DBI is launched via [Sphaira](https://github.com/ITotalJustice/sphaira) or [nx-hbmenu](https://github.com/switchbrew/nx-hbmenu/releases/). If you experience issues with translations not applying on other custom firmwares, please refer to [#12](https://github.com/rashevskyv/DBIPatcher/issues/12).

---

## 🤝 Contributing

Translations are stored in the `translations/` directory as CSV files. To improve a translation:
1. Fork the repo.
2. Edit the `.csv` for your language.
3. Submit a Pull Request!

Spanish (Latin America) contributions should follow the
[ES-419 style guide](docs/es419-style-guide.md).

---

## 📜 Credits

- **DBI Creator**: [duckbill](https://github.com/rashevskyv/dbi)
- **Localization Engine**: [tg:@buinich_bohdan](https://github.com/rashevskyv)
- **Assembly Patcher**: [0xroast/dbi-translate](https://github.com/0xroast/dbi-translate)
- **Special Thanks**: Claude 3.5 Sonnet for the heavy lifting.

> *Created with ❤️ for the Switch community.*
