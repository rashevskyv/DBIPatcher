- [x] Завершено: оптимізація запуску Shadok (пропуск готових перекладів), форсований режим -f та CLI-аргументи в run.bat (v0.0.99).
  - [x] Реалізувати `is_shadok_block_complete` у `src/main.py`: перевірка повноти всіх 33 слотів, відсутності витоків російського оригіналу та наявності реального багаторядкового контенту.
  - [x] Оновити `cmd_shadok`: автоматичний пропуск мов з уже готовим перекладом Шадоків без викликів AI-сесії, якщо не передано прапорець `-f` / `--force`.
  - [x] Підтримка цілісного перекладу блоку для мов з неповними або відсутніми перекладами.
  - [x] Оновити `run.bat`: детальна інструкція з запуску форсованого перекладу (`run.bat shadok -f`, `--langs`) та пряме прокидання параметрів CLI (`%*` до `python -m src.main`).
  - [x] Оновити опис пункту `shadok` у меню `menu.py` (`skips complete`).
  - [x] Підтвердити повне збереження логіки та рядків PR #26 (всі 6 рядків та подяка @aldokeita).
  - [x] Додати юніт-тести в `tests/test_shadok_localization.py` на перевірку повноти, пропуск готових мов та форсований перезапис з `-f`.
  - [x] Ітерувати версію словника до `0.0.99` та оновити `tests/test_temperature_aliases_and_sync.py`.
  - [x] Оновити документацію в `README.md`, `README_ES.md`, `plan.md`, `task.md`, `walkthrough.md`.
  - [x] Успішно виконати всі 141 тест паралельно (`pytest tests -n auto`: 141 passed).

- [x] Завершено: виправлення локалізації ES-419 та 100% успішне проходження всіх 138 тестів (v0.0.98).
  - [x] Відновити автентичні латиноамериканські переклади PR #16 у `data/dictionary.xlsx` та `translations/es419.csv` (142 оновлені клітинки).
  - [x] Усунути європейські терміни (`ajustes`, `lanzar`, `sticks`, `copias de seguridad`, `partidas guardadas`, `borrando`) на користь правильних термінів стилю ES-419.
  - [x] Токенізувати рядки (`[[ESC]]`, `[[LF]]`) для безпомилкової структурної валідації.
  - [x] Перекомпілювати бінарники `output/translation_es419.bin` та `dist/es419/translation.bin`.
  - [x] Ітерувати версію словника до `0.0.98` та оновити тести `tests/test_temperature_aliases_and_sync.py`.
  - [x] Запустити повний тестовий набір паралельно (`pytest tests -n auto`: 138 passed, 0 failed).
  - [x] Оновити документацію в `plan.md`, `task.md`, `walkthrough.md`.

- [x] Завершено: вкладення дій під All з таб-відступами та ізоляція Deploy/Clear (v0.0.97).
  - [x] Переробити склад `all`: включити всі кроки побудови, локалізації та тестів (`sync`, `translate`, `shadok`, `align`, `validate`, `export`, `build`, `dist`, `check`, `test`), окрім `deploy` та `clear`.
  - [x] Візуально відділити всі підпорядковані дії таб-відступом (4 пробіли) під пунктом `all` у `menu.py`.
  - [x] Забезпечити незалежність операцій `deploy` та `clear` (верхній рівень без відступу).
  - [x] Нормалізувати CRLF-символи у `run.bat` для чистого виконання без зайвого ехо команд.
  - [x] Ітерувати версію словника до `0.0.97` та скоригувати тести `tests/test_temperature_aliases_and_sync.py`.
  - [x] Оновити та розширити юніт-тести в `tests/test_menu.py`.
  - [x] Оновити документацію в `README.md`, `README_ES.md`, `plan.md`, `task.md`, `walkthrough.md`.
  - [x] Запустити всі тести паралельно (`pytest -n auto`).

- [x] Завершено: Python TUI-інтерфейс на базі Kefirosphere/build.py та спрощення run.bat (v0.0.96).
  - [x] Розробити `menu.py` з інтерактивним чекбокс-вибором (msvcrt / ANSI, навігація стрілками, SPACE, ENTER).
  - [x] Реалізувати зв'язку чекбокса `all` з кроками пайплайну (`sync`, `translate`, `align`, `validate`, `export`, `build`) та окремий `dist`.
  - [x] Забезпечити фіксований канонічний порядок виконання обраних дій незалежно від порядку вибору.
  - [x] Спростити `run.bat` до запуску `menu.py`.
  - [x] Ітерувати версію словника до `0.0.96` та скоригувати тести.
  - [x] Додати юніт-тести логіки меню в `tests/test_menu.py`.
  - [x] Оновити документацію в `README.md`, `README_ES.md`, `plan.md`, `task.md`, `walkthrough.md`.
  - [x] Запустити всі тести паралельно (`pytest -n auto`).

- [x] Завершено: інтерактивний run.bat та контроль розміру файлів перекладу (v0.0.95).
  - [x] Дослідити поточні розміри файлів перекладу у `dist/` (знайдено `en`: 2.61 KB при порозі ~330 KB).
  - [x] Створити інтерактивний `run.bat` для швидкого запуску всіх операцій пайплайну.
  - [x] Реалізувати модуль/функції обчислення порогу розміру та перевірки розмірів у `src/main.py`.
  - [x] Реалізувати механізм автоматичної перегенерації бінарника при виявленні заниженого розміру.
  - [x] Інтегрувати перевірку розміру в `cmd_build`, `cmd_dist`, `cmd_deploy` (включаючи верифікацію завантажених на GitHub Release файлів через `gh release view --json assets`) та `cmd_check`.
  - [x] Оновити версію словника до `0.0.95` та скоригувати тести `tests/test_temperature_aliases_and_sync.py`.
  - [x] Додати юніт-тести для перевірки розмірів та авто-перегенерації в `tests/test_translation_size_check.py`.
  - [x] Оновити документацію в `README.md` та `README_ES.md`.
  - [x] Запустити всі тести паралельно (`pytest -n auto`).
  - [x] Запустити `dist` для виправлення розміру `dist/en/translation.bin`.

- [x] Завершено: оновлення релізного опису, плашки деплою під PR #26 та підготовка бінарників (v0.0.94).
  - [x] Оновити шаблон релізу та `update_notice` у `src/main.py` під додавання 6 нових рядків DBI 905 з посиланням на PR #26 та Issue #25.
  - [x] Оновити блок Credits у `README.md` та `README_ES.md`.
  - [x] Виконати `python -m src.main dist` для структурування всіх мовних папок з `DBI.nro` та `translation.bin`.
  - [x] Ітерувати версію словника до `0.0.94` та оновити тести `tests/test_temperature_aliases_and_sync.py`.
  - [x] Прогнати тести паралельно (`pytest -n auto`).
  - [x] Задеплоїти оновлення на GitHub Release 905 (`python -m src.main deploy`) та запушити зміни в `origin/master`.

- [x] Завершено: інтеграція відсутніх рядків DBI 905 (PR #26), синхронізація, AI-переклад та збірка (v0.0.93).
  - [x] Прийняти та підтягнути PR #26 (`data/ua.csv`: 6 нових вихідних рядків від @aldokeita).
  - [x] Синхронізувати `data/dictionary.xlsx` через `cmd_sync` (кількість рядків зросла до 1294).
  - [x] Перекласти додані рядки для всіх 24 мов через Web2API (`cmd_translate`).
  - [x] Провалідувати переклади через `cmd_validate` (30264 перевірок, 0 помилок).
  - [x] Експортувати переклади в `translations/*.csv` та зібрати бінарники `translation_*.bin` через `cmd_export` / `cmd_build`.
  - [x] Оновити регресійні тести `tests/test_temperature_aliases_and_sync.py` та `tests/test_indonesian_translation.py` для 1294 рядків та версії 0.0.93.
  - [x] Прогнати тести паралельно (`pytest -n auto`).

- [x] Завершено: інтеграція індонезійського перекладу (PR #24), оновлення релізного шаблону та деплой.
  - [x] Підтягнути зміни PR #24 (`translations/id.csv` та реєстрацію `id` у `data/languages.json`).
  - [x] Синхронізувати `data/dictionary.xlsx`: додати колонку `id`, заповнити всі 1288 рядків з `id.csv`, ітерувати версію до `0.0.91`.
  - [x] Оновити `cmd_deploy` у `src/main.py`: додати `ID` до списку мов, секцію Indonesian Localization, подяку @aldokeita у Credits та оновити повідомлення про реліз.
  - [x] Оновити таблиці підтримуваних мов у `README.md` та `README_ES.md`.
  - [x] Закреслити пункти Shadok Fables та Launcher Compatibility у Known Issues у `README.md`, `README_ES.md` та шаблоні релізу.
  - [x] Додати набір тестів `tests/test_indonesian_translation.py` та оновити `tests/test_temperature_aliases_and_sync.py` для версії 0.0.91.
  - [x] Зібрати всі переклади (`python -m src.main build`), сформувати структуру папок (`python -m src.main dist`) та задеплоїти оновлення на GitHub Release 905 (`python -m src.main deploy`).

- [x] Completed: restore the Cyrillic glyph-repair stage for the shared DBI 905 NRO.
  - [x] After the pinned `dbi-translate` runtime patch, auto-discover the unique embedded 2 MiB Zstandard bitmap font; do not use a version-specific font offset or bundled font asset.
  - [x] Derive `Є/є`, `І/і`, and `Ї/ї` from existing glyphs, preserving support for every translation language that uses those codepoints (`ua`, `be`, `kk`) through the one shared NRO.
  - [x] Fail safely when the font is missing/ambiguous, does not fit its original frame, or fails decompression verification; add focused regression coverage.
  - [x] Restore the required Zstandard dependency, update DBI patching docs/credits, bump workbook metadata to `0.0.90`, verify in WSL including an official DBI 905 smoke test, and create one focused commit. Do not deploy or push.

- [x] Active: safe Shadok localization command (`python -m src.main shadok`).
  - [x] Helpers: `get_shadok_target_langs`, `resolve_shadok_mapping_rows`, `parse_and_validate_shadok_block`.
  - [x] Serial `cmd_shadok` writes only after full validated block; never mutates Original; no version bump.
  - [x] `cmd_translate` / `cmd_align` exclude Shadok rows; `cmd_validate` adds Shadok integrity phase.
  - [x] Prompt + `translate_shadok_block` enforce expected_lines / max_line_length; remove stale `translated_langs`.
  - [x] Screen reflow contract: literary localize then word-wrap into N lines ≤ max (words may cross lines).
  - [x] Per-lang retries (×3) with escalating stricter prompts + JSON `\n` fallback fix.
  - [x] Screen budget: height<=35, width<=39; fewer OK; 34–35 packed into last slot via [[LF]]; model 3.7; war allegory in prompt.
  - [x] Blank trailing slots + export no RU fallback; prompt: blanks/format, Пиздоболов puns, русня naming; `--pad-only`.
  - [ ] Dictionary-wide Shadok/Шадок → русня (and per-lang analogues) — separate step.
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
