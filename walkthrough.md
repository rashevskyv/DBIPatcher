# Walkthrough: DBI 905 Cyrillic glyph repair (v0.0.90)

## Outcome

The shared DBI 905 NRO now repairs the embedded bitmap characters used by the
Ukrainian, Belarusian, and Kazakh translations. The patch runs once for the NRO,
independent of the selected `translation.bin`: `Э/э` are mirrored into `Є/є`,
Latin `I/i` are copied into Cyrillic `І/і`, and `Ï/ï` into `Ї/ї`.

### Pipeline and safeguards

- `scripts/patch_dbi.py` still validates the exact pristine DBI 905 SHA-256 and
  pinned `0xroast/dbi-translate` commit before producing a temporary runtime-
  patched NRO.
- The wrapper then discovers the unique Zstandard frame that expands to the
  65,536 × 32-byte font. No legacy fixed offset or external font asset is used.
- The repaired frame preserves the original checksum flag, must fit the original
  compressed slot, and is decompressed and compared byte-for-byte before the
  final output is written. Missing/ambiguous frames or failed validation abort.
- `zstandard>=0.23,<1` is the only new dependency. Workbook metadata advanced
  from `0.0.89` to `0.0.90`; translation cells and CSV files did not change.

### Verification

- Focused WSL suites: 13/13 patch/font tests and 5/5 workbook/alias tests passed;
  `compileall` and `git diff --check` passed.
- Full suite: 115/118 passed; the remaining three are pre-existing ES-419/Shadok
  baseline failures unrelated to this patch.
- Official DBI 905 smoke test: pristine SHA verified, one frame at `0xBBDC80`,
  exactly six changed glyph slots, patched frame `593,503 / 594,283` bytes, and
  unchanged final NRO length of `16,158,253` bytes. Temporary binaries were removed.

# Walkthrough: Safe Shadok localization command

## Overview

Added a dedicated, serial `python -m src.main shadok` path that localizes approved
parody lines from `data/shadok.json` `mapping[*].new` into workbook rows matched by
`mapping[*].orig`. Original/`orig` is never rewritten. Malformed AI blocks are
rejected with zero writes for that language (no truncation).

### Key changes

1. **Helpers / CLI** in `src/main.py`: `get_shadok_target_langs`,
   `resolve_shadok_mapping_rows`, `parse_and_validate_shadok_block`, `cmd_shadok`.
2. **Guards**: `cmd_translate` always skips resolved Shadok rows (aborts if mapping
   cannot resolve); `cmd_align` excludes them; `cmd_validate` keeps structural skip
   and adds a Shadok integrity phase.
3. **Prompt / AI**: `data/prompts.json` shadok prompt treats the fable as one UI
   screen block: literary localize, then word-wrap/reflow into exactly
   `expected_lines` rows each `<= max_line_length` (words may move across lines).
   `translate_shadok_block` sends those limits. Removed stale `translated_langs`.
4. **Docs / tests**: README Known Issues updated; offline
   `tests/test_shadok_localization.py` covers production command paths with mocks.
5. **Retries**: each language gets up to 3 AI attempts; attempt 2/3 append stricter
   correction prompts with the previous error and output. JSON fallback unescapes `\n`.

# Walkthrough: Оновлення тексту сповіщення про оновлення релізу

## Огляд змін

Оновлено формування тексту плашки-попередження (`update_notice`), яка додається до опису релізу на GitHub у разі оновлення існуючого релізу через команду `deploy`.

### Деталі змін

1. **[src/main.py](file:///d:/git/dev/dbi_patcher/src/main.py)**:
   - Раніше плашка `update_notice` умовним чином вказувала `**translation files**` або `**DBI.nro** and **translation files**` на основі перевірки зміни розміру файлу NRO на GitHub.
   - Тепер плашка завжди чітко вказує завантажувати обидва компоненти:
     ```markdown
     > [!WARNING]
     > 🔄 **Release updated on {kyiv_time} (Kyiv time).** Please re-download both **DBI.nro** and **translation files** to get the latest version.
     ```
   - Прибрано зайву евристичну перевірку розміру файлу `nro_changed`, що спростило код та виключило помилкові випадки, коли користувачам не пропонувалося оновити бінарник.

2. **Версіонування**:
   - Ітеровано версію словника до `v0.0.85` у [data/dictionary.xlsx](file:///d:/git/dev/dbi_patcher/data/dictionary.xlsx).

3. **Документація та плани**:
   - Оновлено [task.md](file:///d:/git/dev/dbi_patcher/task.md), [plan.md](file:///d:/git/dev/dbi_patcher/plan.md), [gemini.md](file:///d:/git/dev/dbi_patcher/gemini.md).

## [2026-08-29] DBI 905, temperature aliases та паралельний Web2API

### Дані та сумісність DBI

- `dictionary.xlsx` є єдиним source of truth: додано 45 точних lookup-alias-ів
  температури (24 literal `$°$` для DBI 898 та 21 clean-`°` для DBI 905). Їхні
  значення копіюються з трьох canonical-рядків для кожної мови, тому alias-и не
  потребують AI-перекладу й не зникають після `export`.
- Додано колонку `tr` та перенесено 1,236 наявних Turkish-перекладів. Сім
  відсутніх старих Turkish-комірок лишаються порожніми в workbook; експорт
  застосовує наявний English fallback, не вигадуючи AI-текст.
- У `src/main.py` прибрано перевизначену `cmd_sync`; тепер лишається одна
  реалізація, яка забезпечує всі language-колонки з `data/languages.json`.

### Патчер DBI 905

- `scripts/patch_dbi.py` пінить `0xroast/dbi-translate` на
  `1320e138fd017db70c1436b537aef7be030f0668` і приймає лише pristine DBI 905
  з SHA-256 `f4360db14ea7ed1043a5a0c7d076d4861cc3383f3b254b9b38d2eec6d175686f`.
- Wrapper використовує тимчасовий clone, явно fetch-ить pinned SHA навіть якщо його
  більше немає на default ref, перевіряє detached SHA та передає
  temporary `src` через `PYTHONPATH` і запускає `dbi_translate.cli patch`.
  Upstream-код не vendor-иться. Потрібні `keystone-engine==0.9.2` та
  `capstone==5.0.9`; WSL/devkitA64/zstandard більше не потрібні.

### Web2API concurrency

- `DBI_TRANSLATE_WORKERS` має default `4` і валідний діапазон `1..8`.
  Лише `WEB2API` виконує незалежні source rows у `ThreadPoolExecutor`.
  `GEMINI_PROXY` і `OMNIROAD` лишаються послідовними.
- Worker виконує HTTP, normalize, validation та refine, але повертає тільки
  результат; він не отримує workbook. Головний потік єдиний записує комірки й
  зберігає checkpoint після кожного завершеного row.
- Web2API перевіряє `/v1/models` перед стартом, використовує максимум один
  client-side retry і ніколи не переініціалізує сесію з worker-а. Лог append
  захищено lock-ом. Stateless refine передає source, candidate values, languages
  та validation errors у кожному запиті.

### Перевірка

- Focused alias, wrapper, Web2API concurrency, core та MTP suites: 80 tests
  passed у Gemini-верифікації.
- Read-only live preflight `GET /v1/models` повернув HTTP 200, а перелік містив
  `gemini-3.6-flash`.
- Реальний patch smoke-test потребує окремо завантаженого pristine
  `DBI.905.ru.nro`; бінарник навмисно не зберігається в репозиторії.

## [2026-08-29] Виправлення втрати даних у workbook (v0.0.87)

### Виправлені дефекти

1. **Збереження існуючих значень при помилці перекладу (`cmd_translate`)**:
   - Усунено передчасне стирання комірки `ws.cell(row, col_map[lc], "")` під час сканування невалідних перекладів у `cmd_translate`.
   - Рядок планується на переклад, але попереднє значення зберігається в пам'яті та в усіх чекпоінтах і перезаписується лише у разі отримання валідного та прийнятого перекладу в головному потоці (`apply_row_result`).

2. **Об'єднання та глобальне видалення дублікатів (`cmd_sync`)**:
   - Перед видаленням дублікатних рядків непорожні значення комірок переносяться у порожні клітинки першого рядка (якщо обидва непорожні та відрізняються, зберігається первинне значення).
   - Усі індекси рядків-дублікатів збираються у глобальний список і видаляються за один спадний прохід (`sorted(all_duplicate_rows, reverse=True)`), що усуває зміщення індексів для наступних груп і гарантує збереження всіх унікальних рядків (наприклад, `A, B, A, B, C` -> `A, B, C`).

3. **Версіонування та регресійне покриття**:
   - Версію метаданих `data/dictionary.xlsx` ітеровано з `0.0.86` до `0.0.87` без зміни даних перекладів.
   - Додано регресійні тести в `tests/test_web2api_concurrency.py` та `tests/test_temperature_aliases_and_sync.py`.

## [2026-08-29] Підвищення надійності релізу (Release Hardening)

### Виконані заходи

1. **Запобігання перезапису вхідного NRO (`scripts/patch_dbi.py`)**:
   - Додано валідацію `resolved_nro == resolved_output`, яка викидає `ValueError` до створення вихідної директорії, клонування репозиторію upstream чи виклику CLI.
   - Додано регресійний тест `test_same_input_and_output_path_raises_value_error_before_clone` у `tests/test_patch_dbi.py`.

2. **Усунення дублювання логування HTTP-помилок (`src/core/ai_client.py`)**:
   - Вилучено надлишковий виклик `_log_interaction` перед `raise requests.HTTPError` у гілці non-200. Кожна спроба тепер логується рівно один раз у спільному обробнику винятків.
   - Додано регресійний тест `test_web2api_failed_http_attempts_log_exactly_once_per_attempt` у `tests/test_web2api_concurrency.py`, що перевіряє створення рівно 2 записів логу при 2 невдалих HTTP 500 спробах.

3. **Синхронізація документації та часового поясу**:
   - У `src/main.py` замінено фіксоване зміщення `timezone(timedelta(hours=3))` на стандартну бібліотеку `ZoneInfo("Europe/Kyiv")`.
   - У `README.md` оновлено посилання на активну модель Web2API (`gemini-3.6-flash`).
   - У `plan.md` виправлено опис розподілу обов'язків: валідацію рядків виконують потоки-воркери, тоді як головний потік лишається єдиним мутатором workbook.
