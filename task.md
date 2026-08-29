- [x] Active: safe Shadok localization command (`python -m src.main shadok`).
  - [x] Helpers: `get_shadok_target_langs`, `resolve_shadok_mapping_rows`, `parse_and_validate_shadok_block`.
  - [x] Serial `cmd_shadok` writes only after full validated block; never mutates Original; no version bump.
  - [x] `cmd_translate` / `cmd_align` exclude Shadok rows; `cmd_validate` adds Shadok integrity phase.
  - [x] Prompt + `translate_shadok_block` enforce expected_lines / max_line_length; remove stale `translated_langs`.
  - [x] Screen reflow contract: literary localize then word-wrap into N lines ≤ max (words may cross lines).
  - [x] Per-lang retries (×3) with escalating stricter prompts + JSON `\n` fallback fix.
  - [x] Screen budget: height<=35, width<=39; fewer OK; 34–35 merged into 33 dict slots; model 3.7.
  - [x] Offline tests in `tests/test_shadok_localization.py` (mock AI; no live pipeline).

- [x] Завершене: заходи підвищення надійності релізу (Release Hardening) та синхронізація документації.
  - [x] Запобігти деструктивному патчингу NRO при однакових шляхах входу та виходу (`scripts/patch_dbi.py`) до клонування чи виклику CLI.
  - [x] Усунути дублювання логування помилок HTTP-запитів у `src/core/ai_client.py` (рівно один запис логу на одну спробу).
  - [x] Оновити розрахунок київського часу в `src/main.py` на стандартну бібліотеку `ZoneInfo("Europe/Kyiv")`.
  - [x] Оновити посилання на модель Web2API (`gemini-3.6-flash`) у `README.md` та уточнити розподіл ролей валідації у `plan.md`.
  - [x] Додати точкові регресійні тести та перевірити всі тестові набори у WSL без зміни даних словника.

- [x] Попереднє активне: усунення шляхів втрати даних у словнику після DBI 905 / Web2API рев'ю (закомічено в 12a4bf9).
  - [x] Збереження існуючого перекладу до моменту прийняття валідної заміни; помилка рядка не стирає дані.
  - [x] Дедуплікація рядків у `cmd_sync` без застарілих індексів та з об'єднанням непорожніх мовних колонок.
  - [x] Додавання точкових регресійних тестів, одноразова ітерація версії словника до 0.0.87.

- [x] Previous active: migrate the external patching stage to pinned `0xroast/dbi-translate` for DBI 905, resolve PR #23's temperature aliases durably in the workbook/CSV pipeline, and make only Web2API row translation bounded-parallel.
  - [x] Preserve the union of PR #22's literal `$°$` DBI 898 aliases, PR #23's clean-`°` DBI 905 aliases, and the three canonical temperature rows in every language column.
  - [x] Replace the DBI 898 `dbi-i18n` wrapper with the pinned DBI 905 `dbi-translate` CLI; retain reproducible download and digest verification.
  - [x] Repair the duplicated `cmd_sync` definition and seed Turkish values before adding the missing rows, so later export cannot erase PR aliases or Turkish translations.
  - [x] Add bounded row-level concurrency only for the stateless Web2API provider; only the main thread may mutate or save `dictionary.xlsx`.
  - [x] Add focused regression checks, update user/developer documentation, bump the workbook version once, and create a focused commit. Do not run `deploy`.

- [x] Previous: pin and run BohdanBuinich/dbi-i18n as the external DBI 898 patching stage.
  - [x] Add a reproducible wrapper pinned to f1f8bebec2b423694e8f058f2d3540a35382b1fd.
  - [x] Document the WSL/devkitA64 command and upstream attribution.
  - [x] Add a focused regression check and bump the workbook version.

- [x] Фаза 1: Аналіз структури CSV та Excel.
- [x] Фаза 2: Синхронізація ua.csv -> dictionary.xlsx.
- [x] Фаза 3: Переклад через AI (Gemini Proxy).
    - [x] Налаштування continuous chat та системних інструкцій.
    - [x] Стійкий парсинг JSON-відповідей (враховуючи "думки" AI).
    - [x] Автоматичне відновлення сесії: 2 ретрая + реініціалізація при збої.
    - [x] Пропуск AI для рядків без кирилиці (копіювання as-is).
- [x] Фаза 3.1: Обробка рядків-шадоків одним блоком.
    - [x] Створити `data/shadok.json` з точними рядками зі словника.
    - [x] Окрема літературна системна інструкція для перекладу.
    - [x] Переклад всього тексту як єдиного блоку, розбиття на рядки.
    - [x] Контроль max_line_length (39) та кількості рядків.
    - [x] Виключення шадоків з валідації та звичайного перекладу.
- [x] Фаза 4.1: Підготовка до Align (Блочне вирівнювання)
    - [x] Складання списку блоків (NSP, Settings, Info).
    - [x] Формування `data/blocks.json` з Regex-патернами.
    - [x] Вирішення конфліктів дублікатів через суфікси (% , mAh, {:s}).
- [/] Фаза 4.2: Реалізація та запуск Align
    - [x] Оновити `src/main.py` для роботи з Regex в `blocks.json`.
    - [ ] Запуск автоматичного вирівнювання колонок (після завершення перекладу).
    - [ ] Перевірка цілісності плейсхолдерів.
- [x] Фаза 5: Фіналізація, Оркестрація та Реліз
    - [x] Створити Orchestrator (команда `all` в `main.py`).
    - [x] Валідатор (`src/core/validator.py`): плейсхолдери, токени, двокрапки, баланс дужок.
    - [x] Regex-контроль: перевірка відповідності фінального результату патерну з `blocks.json`.
- [x] Фаза 5.2: Експорт та Розпаковка (Unpacking)
    - [x] Зворотна заміна в `detokenize()`: `[[LF]]` -> `\\n`, `[[TAB]]` -> `\\t`, `[[ESC]]` -> `\\x1b`, `[[CR]]` -> `\\r`.
    - [x] Генерація індивідуальних CSV для кожної мови (`cmd_export`).
    - [x] Компіляція бінарних файлів (`cmd_build`).
    - [ ] Створення релізу на GitHub: ітерація версії, ченджлог англійською, README.
- [x] Аудит та виправлення
    - [x] Не записувати невалідні переклади в Excel.
    - [x] Retry логіка для `refine()`.
    - [x] `visual_length()` для коректного вирівнювання.
    - [x] Виключити `{}` з перевірки балансу дужок.
    - [x] Очищення логу при кожному старті.
    - [x] Видалено `"br": "Brasilian"` з `languages.json`.
    - [x] Оновлено повідомлення про оновлення релізу: завжди вказувати на необхідність завантаження як `DBI.nro`, так і файлів перекладу.

# [x] Emergency follow-up: fetch the pinned upstream DBI 905 commit explicitly before checkout, because it is no longer advertised by the upstream default ref.

# [x] Release notes: disclose possible untranslated/fallback strings and credit Bohdan Buinich (`dbi-i18n`) and 0xroast (`dbi-translate`).
