# Walkthrough: Вирівнювання колонок блоків для id та es419, сумісність аліасів температури та версія v0.0.100

## Результати
- **Вирівнювання блоків інтерфейсу (`cmd_align`)**:
  - Під час запуску повного пайплайну `cmd_align()` перевірив структуровані блоки у [`data/blocks.json`](file:///d:/git/dev/dbi_patcher/data/blocks.json).
  - Для індонезійської мови (`id`, доданої у PR #24) та відновленої автентичної латиноамериканської іспанської (`es419`) виконано вирівнювання двокрапок за найдовшим префіксом у блоках (`SYSTEM_INFO_STATUS`, `BATTERY_INFO`, `MAX17050_INFO`, `TITLE_INFO` тощо).
  - При цьому у словнику [`data/dictionary.xlsx`](file:///d:/git/dev/dbi_patcher/data/dictionary.xlsx) версію оновлено до **`0.0.100`**.
- **Сумісність перевірки аліасів температури у тестах**:
  - Канонічні рядки температури в `id` (`Температура        : {}°C`, `Температура батареи             : {}°C`, `Средняя температура: {}°C`) отримали вирівнювальні пробіли відповідно до вимог блоків DBI, тоді як 45 аліасів зберегли базову форму з відступами вихідного перекладу (аналогічно до турецької мови `tr`).
  - У [`tests/test_temperature_aliases_and_sync.py`](file:///d:/git/dev/dbi_patcher/tests/test_temperature_aliases_and_sync.py) оновлено умову:
    `if lc in ("tr", "id"): self.assertEqual(str(actual_val).split(), str(expected_val).split(), ...)`.
  - Оновлено очікувану версію словника до **`0.0.100`**.
- **Експорт та збірка**:
  - Експортовано оновлені файли [`translations/id.csv`](file:///d:/git/dev/dbi_patcher/translations/id.csv) та [`translations/es419.csv`](file:///d:/git/dev/dbi_patcher/translations/es419.csv).
  - Скомпільовано всі 24 бінарники `output/translation_*.bin` та перепаковано папки `dist/*/`.
  - Успішно виконано перевірку цілісності та розмірів (`python -m src.main check`): усі бінарники значно перевищують поріг 330 KB.
- **Тестування**:
  - Усі **141 тест** завершилися на 100% успішно у паралельному режимі (`pytest tests -n auto`: 141 passed, 0 failed).

# Walkthrough: Оптимізація запуску Shadok (пропуск готових перекладів), форсований режим -f та CLI-аргументи в run.bat (v0.0.99)

## Результати
- **Збереження готових перекладів байок Шадоків**:
  - Реалізовано функцію `is_shadok_block_complete(ws, col_idx, resolved)` у [`src/main.py`](file:///d:/git/dev/dbi_patcher/src/main.py):
    1. Перевіряє, що всі 33 слоти мають значення (не `None` і не порожній рядок `""`, враховуючи `SHADOK_BLANK_CELL = " "` для відступів та хвостових слотів).
    2. Перевіряє відсутність витоків вихідного російського тексту у клітинках перекладу.
    3. Перевіряє наявність принаймні 5 унікальних рядків контенту (захист від заповнення однаковими фіктивними плейсхолдерами).
  - Оновлено `cmd_shadok()`: якщо переклад для певної мови вже повний, він автоматично пропускається з повідомленням `[SKIP][<lc>] Shadok block already complete. Use -f / --force to re-translate.`.
  - Якщо всі мови завершені, сесія AI (`init_session_shadok()`) взагалі не ініціалізується, що суттєво пришвидшує загальний запуск `all` або `shadok` (з хвилин очікування до часток секунди).
  - Для мов з відсутніми або неповними перекладами перекладається весь блок з 33 слотів цілком (відповідно до вимоги, що Шадок є єдиним цільним екраном-байкою).
- **Підтримка форсованого перекладу (`-f` / `--force`)**:
  - Додано прапорці `-f` / `--force` та змінну оточення `DBI_SHADOK_FORCE=1` для примусового перезапису перекладів Шадоків через AI.
  - Оновлено `cmd_help()` та `main()` у [`src/main.py`](file:///d:/git/dev/dbi_patcher/src/main.py).
- **Оновлення [`run.bat`](file:///d:/git/dev/dbi_patcher/run.bat)**:
  - Додано детальну довідку з прикладами використання прямо у коментарях файлу.
  - Додано прокидання параметрів командного рядка: при виклику з аргументами (наприклад, `run.bat shadok -f`, `run.bat all`, `run.bat test`) вони автоматично передаються у `python -m src.main %*`. При подвійному кліку або запуску без аргументів відкривається інтерактивне меню [`menu.py`](file:///d:/git/dev/dbi_patcher/menu.py).
- **Оновлення меню [`menu.py`](file:///d:/git/dev/dbi_patcher/menu.py)**:
  - У пункті `shadok` уточнено опис: `Localize Shadok satirical fables via AI (skips complete)`.
- **Перевірка логіки PR #26**:
  - Підтверджено збереження всіх 6 доданих рядків від `@aldokeita` (включно з пробілом у `" Новый DLC "`), їхніх перекладів у 24 мовах та подяк у релізних шаблонах.
- **Нові юніт-тести**:
  - Додано тести `test_is_shadok_block_complete_rules`, `test_cmd_shadok_skips_complete_unless_force` та `test_cmd_shadok_translates_only_incomplete_languages` у [`tests/test_shadok_localization.py`](file:///d:/git/dev/dbi_patcher/tests/test_shadok_localization.py).
- **Версіонування та тестування**:
  - Ітеровано версію словника до **`0.0.99`** у [`data/dictionary.xlsx`](file:///d:/git/dev/dbi_patcher/data/dictionary.xlsx).
  - Оновлено [`tests/test_temperature_aliases_and_sync.py`](file:///d:/git/dev/dbi_patcher/tests/test_temperature_aliases_and_sync.py).
  - Повний набір тестів виконано паралельно (`pytest tests -n auto`): **141 passed, 0 failed (100% green)**.
- **Оновлення документації**:
  - Оновлено [`README.md`](file:///d:/git/dev/dbi_patcher/README.md) та [`README_ES.md`](file:///d:/git/dev/dbi_patcher/README_ES.md).

# Walkthrough: Виправлення локалізації ES-419 та 100% успішне проходження всіх 138 тестів (v0.0.98)

## Результати
- **Діагностика та усунення 3 падінь у тестах [`tests/test_es419_translation.py`](file:///d:/git/dev/dbi_patcher/tests/test_es419_translation.py)**:
  - **Причина проблеми**: При злитті PR #16 колонка `es419` у словнику була частково перезаписана європейською іспанською термінологією (`lanzar` замість `Iniciar`, `ajustes` замість `Configuración`, `sticks` замість `Palancas`, `copias de seguridad` замість `Respaldo`, `partidas guardadas` замість `Datos de guardado`, `borrando` замість `Eliminando`). Також рядки не мали спеціальної токенізації (`[[ESC]]`, `[[LF]]`), через що 3 тести (`test_preferred_es419_terminology`, `test_all_rows_pass_structural_validation`, `test_csv_schema_and_completeness`) стабільно падали.
  - **Відновлення автентичних перекладів**:
    - Витягнуто оригінальні переклади автора PR #16 (`e01d8a2`) та оновлено 142 клітинки у [`data/dictionary.xlsx`](file:///d:/git/dev/dbi_patcher/data/dictionary.xlsx).
    - Переклади токенізовано згідно з правилами проекту. Усі нові рядки (температурні аліаси, ключі DBI 905 та рядки PR #26) повністю збережено.
    - Експортовано оновлений [`translations/es419.csv`](file:///d:/git/dev/dbi_patcher/translations/es419.csv) (1294 записи, 0 пропущених).
- **Перезбірка бінарників**:
  - Скомпільовано [`output/translation_es419.bin`](file:///d:/git/dev/dbi_patcher/output/translation_es419.bin) розміром 744,752 байти (727.3 KB).
  - Оновлено файл [`dist/es419/translation.bin`](file:///d:/git/dev/dbi_patcher/dist/es419/translation.bin).
- **Версіонування та 100% проходження тестів**:
  - Ітеровано версію словника до **`0.0.98`**.
  - Оновлено тест [`tests/test_temperature_aliases_and_sync.py`](file:///d:/git/dev/dbi_patcher/tests/test_temperature_aliases_and_sync.py) на версію `0.0.98`.
  - Запущено повний набір тестів паралельно (`pytest tests -n auto`): **усі 138 тестів завершилися успішно (138 passed, 0 failed, 100% green)**.

# Walkthrough: Вкладення дій під All з таб-відступами та ізоляція Deploy/Clear (v0.0.97)

## Результати
- **Оновлення складу `all` та ієрархія в [`menu.py`](file:///d:/git/dev/dbi_patcher/menu.py)**:
  - До списку `ALL_SUB_ACTIONS` включено всі етапи побудови, локалізації та тестів:
    `sync`, `translate`, `shadok`, `align`, `validate`, `export`, `build`, `dist`, `check`, `test`.
  - Пункти `deploy` та `clear` відокремлені як незалежні операції верхнього рівня.
  - При обранні `all` автоматично виставляються прапорці на всі 10 підпорядкованих дій; при знятті будь-якої з них з `all` галочка автоматично скидається. Якщо вибрати всі 10 вручну — `all` автоматично стає відміченим.
- **Візуальне виділення табом (відступом у 4 пробіли)**:
  - Усі 10 дій всередині `all` виводяться з відступом у 4 символи (таб) від лівого краю пункту `all`:
    ```text
    >> [ ] all        - Complete build pipeline (all steps except deploy & clear)
           [ ] sync       - Synchronize dictionary with source CSV files
           [ ] translate  - Translate missing strings using AI (Web2API / Gemini)
           [ ] shadok     - Localize Shadok satirical fables via AI
           [ ] align      - Align colon positions in structured UI blocks
           [ ] validate   - Validate dictionary structure and translation rules
           [ ] export     - Export CSV files and compile translation.bin files
           [ ] build      - Compile translation.bin binaries (with size check & auto-regen)
           [ ] dist       - Pack NRO and translation.bin into per-language dist/ folders
           [ ] check      - Check source integrity and verify binary file sizes
           [ ] test       - Run parallel test suite (pytest -n auto)
       [ ] deploy     - Deploy release to GitHub (with size verification)
       [ ] clear      - Clear translations for a specific language
    ```
  - Курсор навігації `>>` та прапорець `[ ]` налаштовано так, що вони ніколи не зміщуються по горизонталі під час переміщення вгору-вниз (без візуального «тремтіння»).
- **Справжній запуск pytest у кроці `test`**:
  - У TUI меню дія `test` запускає паралельний набір тестів проекту (`pytest tests -n auto`) через `subprocess`, що відповідає підпису пункту.
- **CRLF нормалізація [`run.bat`](file:///d:/git/dev/dbi_patcher/run.bat)**:
  - Батник перекодовано у суворий Windows CRLF-формат, що усуває зайвий вивід команд під час запуску в середовищі Windows `cmd.exe`.
- **Тестування та версіонування**:
  - Оновлено та розширено набір юніт-тестів [`tests/test_menu.py`](file:///d:/git/dev/dbi_patcher/tests/test_menu.py) (9 тестів: перемикання `all`, авто-зняття/постановка прапорця, перевірка прапорця `indent=True` для всіх 10 дочірніх дій, ізоляція `deploy`/`clear` та канонічний порядок).
  - Ітеровано версію словника `data/dictionary.xlsx` до `0.0.97`.
  - Оновлено тест `tests/test_temperature_aliases_and_sync.py` для очікування `0.0.97`.
  - Оновлено документацію в `README.md` та `README_ES.md`.
  - Усі 135 тестів успішно виконано в паралельному режимі (`pytest tests -n auto`).

# Walkthrough: Python TUI-інтерфейс на базі Kefirosphere/build.py та спрощення run.bat (v0.0.96)

## Результати
- **Розробка Python TUI-інтерфейсу ([`menu.py`](file:///d:/git/dev/dbi_patcher/menu.py))**:
  - Створено повноцінний інтерактивний консольний інтерфейс у терміналі, за зразком механізму `interactive_select` з `Kefirosphere/build.py`.
  - Підтримує швидку навігацію клавішами `UP`/`DOWN` (або `k`/`j`), перемикання чекбоксів клавішею `SPACE`, запуск обраного ланцюжка через `ENTER` та вихід через `Q`/`ESC`.
  - Реалізовано кольорове ANSI-оформлення з підтримкою VT100 на Windows (`os.system("")`), активним підсвічуванням курсора та відмічених пунктів `[x]`.
- **Логіка зв'язку мета-опції `all` та окремого `dist`**:
  - Мета-пункт `all` контролює основні етапи побудови: `sync`, `translate`, `align`, `validate`, `export`, `build`.
  - При виборі `all` автоматично встановлюються галочки на всі ці 6 кроків.
  - При ручному знятті/зміні будь-якого з цих 6 кроків з `all` автоматично знімається вибір, а всі інші обрані користувачем дії залишаються відміченими для виконання.
  - При повному ручному виборі всіх 6 кроків `all` автоматично стає відміченим.
  - Дія `dist` є окремою та незалежною опцією і не перемикається разом з `all`, але може бути обрана окремо або разом з іншими діями.
- **Фіксований канонічний порядок виконання**:
  - Незалежно від того, в якому порядку користувач клацав чекбокси у списку, обрані операції завжди виконуються у суворо визначеному порядку:
    `clear` -> `sync` -> `translate` -> `shadok` -> `align` -> `validate` -> `export` -> `build` -> `dist` -> `check` -> `test` -> `deploy`.
  - У нижній частині меню динамічно відображається сформований ланцюжок дій (`Execution plan:`).
- **Спрощення `run.bat`**:
  - Батник скорочено до перевірки наявності Python у PATH та виклику `python "%~dp0menu.py"`, що забезпечує стабільний запуск TUI по дабл-кліку без сирого виводу команд `echo`.
- **Тестування та версіонування**:
  - Додано юніт-тести логіки меню в [`tests/test_menu.py`](file:///d:/git/dev/dbi_patcher/tests/test_menu.py) (8 тестів на перемикання `all`, авто-зняття прапорця, незалежність `dist` та канонічний порядок).
  - Ітеровано версію словника `data/dictionary.xlsx` до `0.0.96`.
  - Оновлено тест `tests/test_temperature_aliases_and_sync.py` для очікування `0.0.96`.
  - Оновлено документацію в `README.md` та `README_ES.md`.
  - Всі 134 тести успішно виконано в паралельному режимі (`pytest tests -n auto`).

# Walkthrough: Інтерактивний run.bat, контроль розміру файлів перекладу та авто-перегенерація (v0.0.95)


## Результати
- **Інтерактивний батнік (`run.bat`)**:
  - Створено Windows-батнік `run.bat` у корені репозиторію з підтримкою кодування UTF-8 (`chcp 65001`) для запуску через подвійний клік.
  - Меню надає зручний доступ до всіх функцій пайплайну: `sync`, `translate`, `validate`, `align`, `shadok`, `export`, `build`, `dist`, `check`, `test` (паралельний запуск pytest), `all`, `clear` (із запитом коду мови) та `deploy` (із підтвердженням `y/N`).
  - Після кожної дії передбачено паузу (`pause`) та циклічне повернення в головне меню, що виключає закриття вікна терміналу при запуску з Провідника Windows.
- **Аналіз та розв'язання проблеми заниженого розміру бінарників**:
  - Виявлено аномальний файл `dist/en/translation.bin` розміром 2,672 байти (2.61 KB при нормі ~671 KB).
  - Знайдено корінь проблеми: у тесті `tests/test_shadok_localization.py` виклик `cmd_export()` не мокував `cmd_build()`, через що 33 тестових рядки Шадоків перекомпілювалися в реальну директорію `output/translation_en.bin`. Тест ізольовано шляхом мокування `cmd_build`.
  - Реалізовано динамічний розрахунок порогу `get_translation_size_threshold()`: відкидаються пошкоджені файли (< 100 KB), знаходиться мінімальний валідний розмір (661,544 байти, ~646 KB для `zhcn`) та ділиться на два -> поріг складає 330,772 байти (~323 KB).
  - Створено механізм авто-перегенерації `verify_and_regenerate_translation()`: якщо бінарник відсутній або менший за поріг, автоматично виконується експорт мовного CSV зі словника `dictionary.xlsx` та перезбірка.
  - Інтегровано перевірку розміру в `cmd_build`, `cmd_dist` (перевірка перед і після копіювання), `cmd_deploy` (перевірка локальних копій Kefir/Switch та всіх ассетів перед завантаженням) і `cmd_check` (вивід таблиці розмірів у KB з валідацією).
  - Реалізовано `verify_remote_release_assets()` у `cmd_deploy`: після завантаження релізу на GitHub скрипт звертається до `gh release view {dbi_ver} --json assets`, перевіряє точний розмір у кілобайтах кожного завантаженого файлу, звіряє з локальним розміром та гарантує, що жоден переклад не є заниженим.
  - Виправлено файли: `dist/en/translation.bin` та `output/translation_en.bin` тепер мають повноцінний розмір 687,184 байти (671.08 KB).
- **Тестування та версіонування**:
  - Додано набір юніт-тестів `tests/test_translation_size_check.py` (7 тестів на поріг, фолбек, авто-перегенерацію, детекцію помилок та перевірку GitHub ассетів).
  - Оновлено версію робочої книги `data/dictionary.xlsx` до `0.0.95`.
  - Оновлено `tests/test_temperature_aliases_and_sync.py` для очікування версії `0.0.95`.
  - Оновлено документацію в `README.md` та `README_ES.md`.
  - Усі 126 тестів успішно виконано в паралельному режимі (`pytest tests -n auto`).

# Walkthrough: Оновлення релізного опису, плашки деплою під PR #26 та структура dist (v0.0.94)


## Результати
- Оновлено `cmd_deploy` у `src/main.py`:
  - Додано розділ `### 🧩 Missing DBI 905 Strings Added (All Languages)` з описом 6 нових вихідних рядків (інсталяція, майстер-ключ, MTP, перевірка оновлень) та подякою `@aldokeita` за внесок у PR #26 на базі дослідження в Issue #25.
  - Оновлено `update_notice`: сповіщення користувачів про оновлення всіх 24 мов новими рядками DBI 905 та рекомендація повторно завантажити `DBI.nro` і `translation_<lang>.bin`.
  - Додано `@aldokeita` до блоку `Credits` у `release_body`, `README.md` та `README_ES.md`.
- Запущено команду `python -m src.main dist`: сформовано повну структуру папок `dist/<lang>/` (для всіх 24 мов) із відповідними `DBI.nro` та `translation.bin`.
- Ітеровано версію метаданих словника до `0.0.94` та оновлено тест `tests/test_temperature_aliases_and_sync.py`.
- Проведено паралельне тестування (`pytest -n auto`): всі 112 тестів пройдено успішно (100%).
- Виконано деплой (`python -m src.main deploy`): файли скопійовано у робочі каталоги (`_kefir` та `Switch`), оновлено всі активи та релізні нотатки на GitHub Release 905, зміни запушено у гілку `master`.

# Walkthrough: Інтеграція вихідних рядків DBI 905 (PR #26), синхронізація, мультиязичний AI-переклад та збірка (v0.0.93)

## Результати
- Прийнято (merged) та підтягнуто PR #26 від @aldokeita з 6 вихідними рядками у `data/ua.csv`:
  1. ` Новый DLC ` (зберігає провідний пробіл для точного зіставлення в `make_pfxsfx`)
  2. `Записано: `
  3. `Игра использует мастер-ключ `
  4. `Android extensions: `
  5. ` в чёрном списке.`
  6. `МБ/сек)`
- Виконано синхронізацію словника `python -m src.main sync`: додано 6 рядків у `data/dictionary.xlsx` (загальна кількість рядків зросла з 1288 до 1294). Український стовпець `ua` автоматично підтягнув значення з `data/ua.csv`.
- Виконано AI-переклад через паралельний Web2API пайплайн (`python -m src.main translate`): перекладено 138 мовних клітинок (для всіх 24 мов).
- Виконано валідацію `python -m src.main validate`: 30264 перевірок перекладу успішні, 0 помилок у загальній таблиці.
- Виконано експорт `python -m src.main export`: оновлено всі 24 CSV-файли у папці `translations/` та автоматично перезібрано бінарні файли `translation_*.bin` в `output/`.
- Оновлено очікувані значення кількості рядків (1294) та версії (`0.0.93`) у тестах `tests/test_temperature_aliases_and_sync.py` та `tests/test_indonesian_translation.py`.
- Всі 112 тестів успішно пройдено при паралельному запуску (`pytest -n auto`).

# Walkthrough: Інтеграція індонезійського перекладу (PR #24), оновлення релізного повідомлення та деплой (v0.0.91)

## Результати
- Успішно підтягнуто та зафіксовано PR #24 від @aldokeita: файл `translations/id.csv` та конфігурацію мови в `data/languages.json`.
- Всі 1288 рядків індонезійського перекладу інтегровано в `data/dictionary.xlsx` у нову колонку `id`.
- Метадані версії робочої книги оновлено з `0.0.90` до `0.0.91`.
- Оновлено `cmd_deploy` у `src/main.py`:
  - Додано `ID — Indonesian` до списку мов.
  - Додано розділ `### 🌐 Indonesian Localization` та подяку `@aldokeita` у `Credits`.
  - Оновлено плашку `update_notice` для інформування користувачів про додавання індонезійської локалізації.
  - Закреслено пункти `Shadok Fables` та `Launcher Compatibility` у розділі `Known Issues` як вирішені.
- Оновлено таблиці мов та розділ відомих проблем у `README.md` та `README_ES.md`.
- Створено `tests/test_indonesian_translation.py` та оновлено `tests/test_temperature_aliases_and_sync.py`.
- Згенеровано `output/translation_id.bin` розміром 680,992 байти.
- Сформовано структуру папок `dist/` для всіх підтримуваних мов (`python -m src.main dist`).
- Виконано деплой (`python -m src.main deploy`): оновлено активи релізу 905 на GitHub (включаючи `translation_id.bin`) та замінено опис релізу.

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
