# Виконаний план: Вичерпний набір 99 варіантів суфіксів статусу інсталяції та усунення витоку «ПЕРЕДАЧА» (v0.0.104)

## Мета та обсяг робіт
- **Першопричина витоку «ПЕРЕДАЧА OK» при успішному перекладі «ПОДПИСЬ»**:
  - На реальній консолі рядок інсталяції має вигляд: `filename.nca     : [ПЕРЕДАЧА OK] [ПОДПИСЬ: OK]`.
  - Префікс з унікальним ім'ям файлу не збігається.
  - Алгоритм суфіксного пошуку `make_pfxsfx` сканує рядок від кінця до початку (від повної довжини до 2 байтів) і зупиняється на першому збігу.
  - Рядок у кінці містить код скидання кольору `\x1b[37;1m`.
  - Усі раніше додані комбіновані ключі у v0.0.103 починалися з коду кольору `\x1b[32;1m` безпосередньо перед `[ПЕРЕДАЧА OK]`. Проте в DBI `[ПЕРЕДАЧА OK]` виводиться безпосередньо як чистий текст (або після пробілів після двокрапки), без коду кольору перед дужкою `[`.
  - Ключі чистого тексту (`[ПЕРЕДАЧА OK] [ПОДПИСЬ: OK]`) у v0.0.103 не мали на кінці `\x1b[37;1m`, тому не могли зіставитися як суфікс.
  - В результаті суфіксний пошук пропускав усі довгі комбіновані ключі і зупинявся на короткому суфіксі `[ПОДПИСЬ: OK]\x1b[37;1m`, а блок `[ПЕРЕДАЧА OK]` потрапляв у середину рядка (`mid`), яка копіюється без змін російською мовою!
- **Завдання на версію v0.0.104**:
  1. Додати всі 99 відсутніх варіацій комбінованих та автономних статус-рядків для всіх 24 мов (чистий текст перед `[ПЕРЕДАЧА OK]`, скидання кольору, варіанти з 1 та 2 пробілами, жовтий колір для DBI).
  2. Виправити рядок 1298 (`[32;1m[ПЕРЕДАЧА OK]\x1b[37;1m`), щоб усунути подвійний ESC і відображення literal `[32;1m` на екрані.
  3. Оновити `data/dictionary.xlsx` до 1430 рядків (версія `0.0.104`), оновити `data/ua.csv` до 1382 рядків.
  4. Виконати валідацію, експорт усіх CSV та компіляцію всіх 24 бінарників `translation_*.bin`.
  5. Оновити файли в `dist/*/` та `_kefir/kefir/switch/DBI/`.
  6. Оновити тести (`tests/test_issue25_colored_lines_and_gate.py`, `tests/test_temperature_aliases_and_sync.py`, `tests/test_indonesian_translation.py`).
  7. Запустити повний набір тестів паралельно (`pytest tests -n auto`).

# Виконаний план: Повний набір варіацій статус-рядків інсталяції (пробіли, скидання кольору, чистий текст) (v0.0.103)

## Мета та обсяг робіт
- **Виявлення першопричини відсутності перекладу передачі та підпису на консолі**:
  - На реальній консолі DBI формує статус-рядок інсталяції з роздільником між передачею та підписом:
    - або з пробілом: `\x1b[32;1m[ПЕРЕДАЧА OK] \x1b[32;1m[ПОДПИСЬ: OK]\x1b[37;1m`
    - або зі скиданням кольору та пробілом: `\x1b[32;1m[ПЕРЕДАЧА OK]\x1b[37;1m \x1b[32;1m[ПОДПИСЬ: OK]\x1b[37;1m`
    - або без ANSI-кольору в текстовому режимі: `[ПЕРЕДАЧА OK] [ПОДПИСЬ: OK]`
  - У версії v0.0.102 було додано лише компактний варіант без пробілу (`\x1b[32;1m[ПЕРЕДАЧА OK]\x1b[32;1m[ПОДПИСЬ: OK]\x1b[37;1m`). Через наявність пробілу або `\x1b[37;1m` цей суфікс не співпадав.
  - Оскільки суфіксний пошук у патчері замінює лише **один суфікс у кінці рядка**, відсутність точного комбінованого суфікса призводила до того, що підпис відрізався суфіксом (або теж не збігався), а передача разом із пробілом опинялася в середині `cmid` і виводилася російською мовою на консолі.
- **Додавання 26 вичерпних варіацій статус-рядків для всіх 24 мов**:
  - Комбіновані рядки з пробілом (`[ПЕРЕДАЧА OK] [ПОДПИСЬ: ...]`).
  - Комбіновані рядки зі скиданням кольору та пробілом (`\x1b[32;1m[ПЕРЕДАЧА OK]\x1b[37;1m \x1b...`).
  - Комбіновані рядки зі скиданням кольору без пробілу (`\x1b[32;1m[ПЕРЕДАЧА OK]\x1b[37;1m\x1b...`).
  - Текстові комбіновані рядки без ANSI-кодів (як з пробілом, так і без).
  - Усі 4 типи підписів: `OK`, `Поддельная` (`Fake`), `XCI➡NSP`, `DBI`.
  - Автономні кольорові рядки підписів (`\x1b[32;1m[ПОДПИСЬ: OK]\x1b[37;1m` тощо).
- **Синхронізація, валідація, бінарники та дистрибутиви**:
  - Оновлено `data/dictionary.xlsx` (1331 запис, версія 0.0.103).
  - Оновлено `data/ua.csv` (1283 рядки).
  - Провалідовано всі 31,152 перевірок без помилок (`python -m src.main validate`).
  - Експортовано всі 24 CSV та скомпільовано бінарники `translation_*.bin` (`cmd_export`, `cmd_build`).
  - Оновлено всі теки `dist/*/` та скопійовано актуальні файли у `_kefir/kefir/switch/DBI/`.
- **Тестування**:
  - Додано регресійні перевірки симуляції розпізнавання суфіксів з пробілами та скиданням кольору в `tests/test_issue25_colored_lines_and_gate.py`.
  - Оновлено версію та кількість рядків у `tests/test_temperature_aliases_and_sync.py` та `tests/test_indonesian_translation.py`.
  - Всі 148 тестів виконано паралельно (`pytest tests -n auto`: 148 passed).

# Виконаний план: Реальний ByteGate 256 байтів, комбіновані суфікси передачі+підпису та усунення MagicMock (v0.0.102)

## Мета та обсяг робіт
- **Виправлення та складання реального NRO з 256-байтним ByteGate**:
  - `scripts/patch_dbi.py` з підміною `cmp x20, #0x80` -> `cmp x20, #0x100` (256 байтів) виконано для створення діючого `DBI.905.ru_patched.nro`.
  - Верифіковано в бінарнику: інструкція `cmp x20, #0x100` знаходиться за адресою `0xb90dbc`.
  - Скопійовано оновлений `DBI.nro` у `D:/git/dev/_kefir/kefir/switch/DBI/DBI.nro` та у всі теки `dist/*/DBI.nro`.
- **Розв'язання проблеми витоку російських «ПЕРЕДАЧА» та «ПОДПИСЬ» (комбіновані статуси)**:
  - Досліджено виконання `make_pfxsfx`: під час встановлення файлів DBI формує єдиний лог-рядок: `filename.nca : \x1b[32;1m[ПЕРЕДАЧА OK]\x1b[32;1m[ПОДПИСЬ: OK]\x1b[37;1m`.
  - Оскільки суфіксний пошук брав лише `[ПОДПИСЬ: OK]`, статус передачі опинявся у неперекладеній середині (`cmid`), яку DBI копіює дослівно без змін.
  - Додано комбіновані суфікси для всіх 24 мов у `data/ua.csv` та `data/dictionary.xlsx` (1305 рядків):
    - `\x1b[32;1m[ПЕРЕДАЧА OK]\x1b[32;1m[ПОДПИСЬ: OK]\x1b[37;1m` -> `\x1b[32;1m[TRANSFER OK]\x1b[32;1m[SIGNATURE: OK]\x1b[37;1m`
    - `\x1b[32;1m[ПЕРЕДАЧА OK]\x1b[38;2;255;128;0m[ПОДПИСЬ: Поддельная]\x1b[37;1m` -> `\x1b[32;1m[TRANSFER OK]\x1b[38;2;255;128;0m[SIGNATURE: Fake]\x1b[37;1m`
    - `\x1b[32;1m[ПЕРЕДАЧА OK]\x1b[32;1m[ПОДПИСЬ: XCI➡NSP]\x1b[37;1m` -> `\x1b[32;1m[TRANSFER OK]\x1b[32;1m[SIGNATURE: XCI➡NSP]\x1b[37;1m`
  - Виправлено суфікс `\x1b[31;1m[ПЕРЕДАЧА ПРЕРВАНА]\x1b[37;1m` для усунення дублювання `\x1b\x1b`.
  - Збережено точні відступи у `data/ua.csv`.
- **Очищення та стабілізація тестів**:
  - Усунено появу залишкової теки `MagicMock/` у тестах `tests/test_patch_dbi.py` шляхом заміни `with tempfile.TemporaryDirectory()` на `tempfile.mkdtemp()`.
  - Оновлено тести `tests/test_issue25_colored_lines_and_gate.py`, `tests/test_temperature_aliases_and_sync.py`, `tests/test_indonesian_translation.py`.
  - Всі 148 тестів успішно виконано паралельно (`pytest tests -n auto`: 148 passed).
  - Скомпільовано бінарники перекладу та оновлено пакети `dist/`.
  - Скопійовано актуальні файли в Kefir (`D:/git/dev/_kefir/kefir/switch/DBI/`).
  - Версію словника підвищено до `0.0.102`.

# Виконаний план: Виправлення кольорових статус-рядків та розширення ліміту довжини рядка (Issue #25, v0.0.101)

## Мета та обсяг робіт
- Реалізація та верифікація Кроку 1 та Кроку 2 з Issue #25:
  - **Крок 1: Точні кольорові рядки у словнику**:
    - Оновити `Validator.check_tokens()` у `src/core/validator.py`: дозволити легітимну асиметрію, коли в оригіналі відсутній початковий `\x1b` через skip у `make_pfxsfx` (починається з `[\d+;...m`), а в перекладі він компенсується на початку (`[[ESC]][\d+;...m`).
    - Додати точні кольорові статус-рядки у `data/ua.csv`:
      - `[32;1mУстановка игры завершена\x1b[37;1m` -> `\x1b[32;1mВстановлення гри завершено\x1b[37;1m`
      - `[32;1mТикет исправлен\x1b[37;1m` -> `\x1b[32;1mТикет виправлено\x1b[37;1m`
      - `[32;1m[ПЕРЕДАЧА OK]\x1b[37;1m` -> `\x1b[32;1m[ПЕРЕДАЧА OK]\x1b[37;1m`
      - `[31;1m[ПЕРЕДАЧА ПРЕРВАНА]\x1b[37;1m` -> `\x1b[31;1m[ПЕРЕДАЧУ ПЕРЕРВАНО]\x1b[37;1m`
      - `[ПОДПИСЬ: Поддельная]\x1b[37;1m` -> `[ПІДПИС: Підроблений]\x1b[37;1m`
      - `[ПОДПИСЬ: OK]\x1b[37;1m` -> `[ПІДПИС: OK]\x1b[37;1m`
      - `[ПОДПИСЬ: XCI➡NSP]\x1b[37;1m` -> `[ПІДПИС: XCI➡NSP]\x1b[37;1m`
    - Синхронізувати рядки у `data/dictionary.xlsx` (збільшення кількості рядків з 1294 до 1301) та згенерувати переклади для всіх 24 мов на основі відповідних базових рядків.
    - Експортувати переклади в `translations/*.csv` та зібрати оновлені бінарники `translation_*.bin`.
  - **Крок 2: Розширення гейту довжини в `make_pfxsfx` (патчер бінарника)**:
    - У `scripts/patch_dbi.py` після клонування та верифікації commit hash `0xroast/dbi-translate` замінювати гейт довжини у `src/dbi_translate/runtime.py`:
      `("I", "cmp x20, #0x80"), ("I", "b.hi {miss}"),` -> `("I", "cmp x20, #0x100"), ("I", "b.hi {miss}"),` (256 байтів замість 128).
    - Це дозволяє довгим рядкам логу (наприклад, 133-байтним рядкам перевірки підписів з 24-бітним RGB-кольором) досягати блоку prefix/suffix matcher.
  - **Тестування та версіонування**:
    - Додати тести симуляції матчера та перевірки гейту в `tests/test_issue25_colored_lines_and_gate.py`.
    - Оновити тести версійності та кількості рядків у `tests/test_temperature_aliases_and_sync.py` (версія `0.0.101`, 1301 рядків).
    - Перевірити проходження всіх тестів паралельно (`pytest -n auto`).
    - Оновити версію метаданих словника до `0.0.101`.

# Виконаний план: Вирівнювання колонок блоків для id та es419, сумісність аліасів температури та версія v0.0.100

## Мета та обсяг робіт
- Забезпечити безпомилкове виконання повного циклу пайплайну при виборі `all`:
  - `cmd_align()` автоматично вирівнює двокрапки в структурованих блоках інтерфейсу (зокрема `id` та `es419`).
  - Оновити тест `tests/test_temperature_aliases_and_sync.py`: канонічні рядки температури в `id` отримали інтерфейсні пробіли вирівнювання згідно з `blocks.json`, тоді як аліаси зберігають вихідні токени (повна аналогія з турецькою мовою `tr`, додано `if lc in ("tr", "id"): self.assertEqual(str(actual_val).split(), str(expected_val).split())`).
  - Оновити очікувану версію словника до `0.0.100` у `tests/test_temperature_aliases_and_sync.py`.
  - Перекомпілювати бінарники та перевірити структуру `dist/`.
  - Перевірити розміри файлів перекладу (`python -m src.main check`).
  - Прогнати всі тести паралельно (`pytest tests -n auto`: 141 passed).
  - Оновити документацію та версіонування.

# Виконаний план: Оптимізація запуску Shadok (пропуск готових перекладів), форсований режим -f та CLI-аргументи в run.bat (v0.0.99)

## Мета та обсяг робіт
- Забезпечити збереження вже готових перекладів байок Шадоків при виборі `all` або запуску `cmd_shadok`:
  - Реалізувати функцію `is_shadok_block_complete` для перевірки наявності всіх 33 заповнених слотів (включаючи `SHADOK_BLANK_CELL`), відсутності витоків вихідного російського тексту та наявності принаймні 5 унікальних рядків контенту.
  - Якщо блок мови вже повністю перекладений, пропускати його без ініціалізації сесії AI та без повторних запитів.
  - Якщо в блоці мови є пропуски або невиправлені помилки, перекладати весь блок цілком (построковий переклад не має сенсу для єдиного екрана-байки).
- Додати підтримку форсованого перекладу:
  - Прапорець `-f` / `--force` або змінна середовища `DBI_SHADOK_FORCE=1` примусово перекладає всі запитані мови з нуля.
- Оновити `run.bat`:
  - Додати детальну документацію у шапку батніка про способи запуску та параметри форсованого перекладу (`run.bat shadok -f`, `--langs`).
  - Реалізувати прокидання CLI-аргументів: якщо передано параметри, вони напряму передаються у `python -m src.main %*`; якщо без параметрів — запускається інтерактивне TUI-меню `menu.py`.
- Оновити опис кроку `shadok` у меню `menu.py`.
- Перевірити збереження логіки PR #26 (всі 6 доданих рядків від @aldokeita та релізні подяки повністю збережені).
- Додати нові юніт-тести в `tests/test_shadok_localization.py` на перевірку правил повноти, пропуск без `-f`, форсування з `-f` та вибірковий переклад лише незавершених мов.
- Ітерувати версію словника до `0.0.99` та оновити тести `tests/test_temperature_aliases_and_sync.py`.
- Оновити документацію в `README.md`, `README_ES.md`, `plan.md`, `task.md`, `walkthrough.md`.
- Запустити всі тести паралельно (`pytest tests -n auto`: 141 passed).

# Виконаний план: Виправлення локалізації ES-419 та 100% успішне проходження всіх 138 тестів (v0.0.98)

## Мета та обсяг робіт
- Усунути розбіжності термінології та форматування в іспанській локалізації Латинської Америки (`es419`):
  - Відновити оригінальні автентичні переклади з PR #16 (`e01d8a2`) для 142 клітинок у `data/dictionary.xlsx` та `translations/es419.csv`.
  - Замінити європейські терміни (`ajustes`, `lanzar`, `sticks`, `copias de seguridad`, `partidas guardadas`, `borrando`) на латиноамериканські (`Configuración`, `Iniciar`, `Palancas`, `Respaldo`, `Datos de guardado`, `Eliminando`).
  - Привести рядки до актуального формату токенізації (`[[ESC]]`, `[[LF]]`).
- Перезібрати бінарні файли `output/translation_es419.bin` та `dist/es419/translation.bin`.
- Ітерувати версію словника до `0.0.98` та оновити тести `tests/test_temperature_aliases_and_sync.py`.
- Досягти 100% успішного проходження повного набору тестів (`pytest tests -n auto`: 138 passed, 0 failed).
- Оновити документацію в `plan.md`, `task.md`, `walkthrough.md`.

# Виконаний план: Вкладення дій під All з таб-відступами та ізоляція Deploy/Clear (v0.0.97)

## Мета та обсяг робіт
- Переробити ієрархію `menu.py`: до `all` входять усі кроки побудови, локалізації, перевірки та тестів (`sync`, `translate`, `shadok`, `align`, `validate`, `export`, `build`, `dist`, `check`, `test`), окрім `deploy` та `clear`.
- Візуально відділити всі підпорядковані дії табом (відступом у 4 пробіли) під пунктом `all`.
- `deploy` та `clear` зробити повністю відокремленими операціями верхнього рівня без відступу.
- Забезпечити стабільну CRLF-розмітку для `run.bat` для запобігання зайвого ехо команд у Windows cmd.
- Ітерувати версію словника до `0.0.97` та оновити відповідні регресійні тести.
- Оновити юніт-тести меню у `tests/test_menu.py`.
- Оновити документацію в `README.md`, `README_ES.md`, `plan.md`, `task.md`, `walkthrough.md`.
- Прогнати всі тести паралельно (`pytest -n auto`).

# Виконаний план: Python TUI-інтерфейс на базі Kefirosphere/build.py та спрощення run.bat (v0.0.96)

## Мета та обсяг робіт
- Створити `menu.py` з інтерактивним вибором чекбоксами у стилі `Kefirosphere/build.py` (msvcrt / ANSI, навігація стрілками, SPACE для перемикання, ENTER для запуску, Q/ESC для виходу).
- Реалізувати взаємозв'язок мета-опції `all` з її кроками (`sync`, `translate`, `align`, `validate`, `export`, `build`):
  - При обранні `all`自動чно обираються всі ці кроки.
  - При знятті/зміні будь-якого з цих кроків з `all` знімається галочка, а обрані дії залишаються на виконання.
  - `dist` є окремою самостійною дією.
- Забезпечити фіксований канонічний порядок виконання пайплайну незалежно від порядку навігації чи вибору користувачем.
- Спростити `run.bat` для швидкого запуску `menu.py`.
- Ітерувати версію словника до `0.0.96` та скоригувати тести.
- Додати юніт-тести логіки меню в `tests/test_menu.py`.
- Оновити документацію в `README.md`, `README_ES.md`, `plan.md`, `task.md`, `walkthrough.md`.
- Прогнати всі тести паралельно (`pytest -n auto`).

# Виконаний план: Інтерактивний run.bat та контроль розміру файлів перекладу (v0.0.95)


## Мета та обсяг робіт
- Створити інтерактивний Windows batch-файл `run.bat` для запуску меню з усіма опціями подвійним кліком.
- Проаналізувати поточні розміри бінарних файлів перекладу у `dist/` (виявлено аномальний `en`: 2.61 KB при нормі 646–878 KB).
- Реалізувати розрахунок мінімального порогу розміру валідних файлів (`min(valid_sizes) // 2`, понад 330 KB) з відсіканням файлів < 100 KB як безумовно помилкових.
- Додати автоматичну перегенерацію бінарника (ре-експорт CSV зі словника та повторна збірка), якщо розмір файлу менший за поріг.
- Інтегрувати перевірку розміру в `cmd_build`, `cmd_dist` та `cmd_deploy` (включаючи верифікацію завантажених ассетів на GitHub Release через `gh release view --json assets`).
- Додати перевірку розмірів файлів у `cmd_check`.
- Оновити версію словника до `0.0.95`, оновити тести `tests/test_temperature_aliases_and_sync.py` та додати нові тести перевірки розмірів у `tests/test_translation_size_check.py`.
- Оновити документацію в `README.md` та `README_ES.md`.
- Прогнати всі тести паралельно (`pytest -n auto`).

# Виконаний план: Оновлення релізного опису, плашки деплою під PR #26 та підготовка бінарників (v0.0.94)


## Мета та обсяг робіт
- Оновити шаблон релізу та `update_notice` у `cmd_deploy` (`src/main.py`), додавши детальний опис нових 6 рядків DBI 905, посилання на PR #26 та Issue #25, і подяку автору @aldokeita.
- Оновити розділи подяк (Credits) у `README.md` та `README_ES.md`.
- Виконати структурування `cmd_dist` для підготовки повноцінних папок `dist/<lang>/` з `DBI.nro` та `translation.bin`.
- Ітерувати версію словника до `0.0.94` та оновити відповідні регресійні тести.
- Переконатися у проходженні тестів паралельно (`pytest -n auto`).
- Виконати деплой на GitHub Release 905 (`python -m src.main deploy`) та пуш у репозиторій.

# Виконаний план: Інтеграція вихідних рядків DBI 905 (PR #26), синхронізація, мультиязичний переклад та збірка (v0.0.93)

## Мета та обсяг робіт
- Прийняти та підтягнути Pull Request #26 від @aldokeita з 6 новими вихідними рядками у `data/ua.csv`.
- Запустити синхронізацію `cmd_sync`, щоб додати нові рядки у `data/dictionary.xlsx` (збільшення до 1294 рядків).
- Перекласти додані рядки для всіх 24 підтримуваних мов за допомогою AI-пайплайну Web2API (`cmd_translate`).
- Провалідувати всі переклади через `cmd_validate` (перевірено 30264 записів, 0 помилок у загальних перекладах).
- Експортувати переклади у `translations/*.csv` та перезібрати бінарники `translation_*.bin` через `cmd_export` / `cmd_build`.
- Оновити регресійні тести на кількість рядків (1294) та версію словника (`0.0.93`).
- Переконатися у проходженні тестового набору паралельно через `pytest -n auto`.

# Виконаний план: Інтеграція індонезійського перекладу (PR #24), оновлення релізного шаблону та деплой (v0.0.91)

## Мета та обсяг робіт
- Підтягнути та повністю інтегрувати пулреквест #24 від @aldokeita, який містить переклад на індонезійську мову (`id`).
- Перенести переклади з `translations/id.csv` (1288 рядків) у робочу книгу `data/dictionary.xlsx` у нову колонку `id`.
- Оновити версію словника до `0.0.91`.
- Оновити шаблон релізу в `src/main.py` (`cmd_deploy`): додати `ID — Indonesian` до переліку підтримуваних мов, створити розділ про індонезійську локалізацію, вказати подяку автору в Credits та актуалізувати плашку оновлення релізу.
- Оновити документацію в `README.md` та `README_ES.md`, закреслити вирішені проблеми (Shadok Fables та Launcher Compatibility).
- Додати окремі юніт-тести для індонезійської мови та перевірити збірку `translation_id.bin`.
- Зібрати всі переклади через `build`, згрупувати структури в `dist` та задеплоїти реліз на GitHub через команду `deploy`.

# Completed plan: DBI 905 Cyrillic glyph repair

## Scope

- Extend the existing pinned `scripts/patch_dbi.py` workflow so its one shared
  DBI 905 output repairs the embedded bitmap glyphs used by Ukrainian,
  Belarusian, and Kazakh translations.
- Reuse the established glyph derivation: mirror `Э/э` into `Є/є`; copy Latin
  `I/i` into Cyrillic `І/і`; copy `Ï/ï` into `Ї/ї`.
- Discover the unique 65,536 × 32-byte font from its Zstandard frame and preserve
  the frame checksum/slot. Do not hardcode the old DBI 810 font offset and do not
  commit a font binary.
- Apply the font repair after the pinned `dbi-translate` CLI writes its output,
  so pristine DBI 905 digest validation remains the trust boundary.

## Safety and acceptance criteria

- Missing or multiple supported font frames, oversized recompression, and failed
  round-trip verification abort without writing a partially modified output.
- Exactly `U+0404`, `U+0406`, `U+0407`, `U+0454`, `U+0456`, and `U+0457` change
  inside the decompressed font; the final NRO length stays unchanged.
- Focused offline tests cover glyph derivation and wrapper ordering. An isolated
  WSL smoke test uses the official DBI 905 binary, validates its pinned SHA-256,
  runs both patch stages, and retains no downloaded/generated NRO in the repo.
- Restore only the required `zstandard` dependency, update concise patching docs
  and attribution, bump workbook metadata once from `0.0.89` to `0.0.90`, and
  commit locally. Do not run `deploy`, push, or regenerate translation CSVs.

## Verification outcome

- Gemini's WSL verification passed all 13 focused patch-wrapper/font tests and all
  5 workbook/alias tests; `compileall` and `git diff --check` also passed.
- The full existing suite ran 118 tests: 115 passed and the same 3 unrelated
  ES-419/Shadok baseline assertions failed.
- An isolated official DBI 905 smoke test verified the pristine SHA-256, applied
  both patch stages, found one font frame at `0xBBDC80`, changed exactly the six
  intended glyph slots, preserved the checksum, and kept the NRO at 16,158,253
  bytes. The 593,503-byte repaired frame fits its 594,283-byte slot.
- Workbook comparison against `HEAD` found only `Metadata!B1` changed from
  `0.0.89` to `0.0.90`; translation cells and `translations/*.csv` are unchanged.

# Completed plan: safe Shadok localization command

## Scope

- Dedicated `python -m src.main shadok` path that localizes `mapping[*].new` into
  workbook rows identified by `mapping[*].orig`. Never rewrite Original to `new`.
- Serial, validated full-block writes only; reject malformed AI output (no truncation).
- Screen contract: one narrative block reflowed into exactly N lines, each
  `visual_length <= max_line_length` (word wrap across lines allowed).
- Exclude Shadok from general `translate` / `align`; add integrity checks in `validate`.
- Target languages = all `languages.json` keys except `ru` (includes `frca`, `tr`).
- Offline mocked tests only; do not run live AI / export / build / deploy.

## Non-goals

- No new dependencies or worker pools.
- No edits to `dictionary.xlsx` / `translations/*.csv` in this patch.
- Do not add `shadok` to `cmd_all` / `cmd_test` chains.

## Completed remediation: workbook data integrity

### Scope

- Fix only the two confirmed data-loss paths in `cmd_translate` and `cmd_sync`.
- Preserve the existing `ThreadPoolExecutor` design: workers remain workbook-free and
  the main thread remains the only workbook mutator/checkpointer.
- Do not run data-mutating pipeline commands. Tests must use in-memory workbooks or
  temporary paths.

### Implementation and verification

1. When an existing translation fails validation during scan, schedule it for
   replacement without clearing its worksheet cell. Apply an accepted replacement
   only in the main-thread result path. Add a regression test where one row fails
   and another checkpoints; the failed row must retain its old value.
2. In `cmd_sync`, merge non-empty cells from duplicate rows into the first row, then
   delete every duplicate index in one global descending pass. Add a regression test
   for `A, B, A, B, C` that retains `A, B, C` and complementary translations.
3. Follow the established workbook-version convention: bump `data/dictionary.xlsx`
   once from `0.0.86` to `0.0.87`; run focused tests in WSL and report actual output.

### Acceptance criteria

- A failed translation never erases a pre-existing cell, including after a later
  successful row checkpoint and final version save.
- Sync removes every duplicate deterministically, preserves unrelated rows and
  retains non-empty translations from duplicate rows.
- No translation CSV/workbook data is regenerated or otherwise changed except the
  workbook metadata version bump.

## Active implementation plan: DBI 905 / durable aliases / Web2API concurrency

### Scope and non-goals

- Target exactly official DBI `905ru`; pin `0xroast/dbi-translate` to the tested
  commit rather than chasing an unsupported future DBI release.
- Preserve the current workbook as the source of truth. `cmd_export` regenerates
  `translations/*.csv`, so no alias may live only in a generated CSV.
- Resolve PR #23 by semantic union, not a blind merge: retain PR #22's 24 literal
  `$°$` aliases, PR #23's 21 clean-degree aliases, and the 3 canonical temperature
  strings. Copy translations from their canonical row; do not call AI for aliases.
- Use Python's standard-library `ThreadPoolExecutor`; do not add a queue library,
  database, service, or generic worker framework. Concurrency is Web2API-only and
  applies to independent source rows, never to individual language values.
- Do not run `deploy`, push, create GitHub releases, or update to Gemini 3.7 in
  this task.

### Execution order

1. **Data compatibility and PR #23.** Inspect base, PR #22 and PR #23 exact keys;
   add the complete union to `dictionary.xlsx` and fill every language from the
   matching canonical row. Reconcile the existing Turkish CSV before new rows are
   created. Remove the duplicate `cmd_sync` definition so source synchronization
   and language-column handling have one durable path. Export CSV files and assert
   exact key-set equality with the workbook.
   **Completed:** 1,288 unique workbook keys; 24 literal and 21 clean-degree
   aliases; `tr` is seeded and exported; one `cmd_sync` remains; regression test
   covers key parity and canonical-value copying.
2. **DBI 905 wrapper.** Replace the DBI 898 `dbi-i18n` wrapper with a minimal,
   pinned `dbi-translate` invocation. Download only release `905ru`, verify its
   SHA-256, fetch the exact pin through the temporary clone, then run
   `python -m dbi_translate.cli patch`,
   and add only Keystone/Capstone dependencies required by upstream. Update the
   focused wrapper test and DBI-facing documentation.
   **Completed:** wrapper is pinned to `1320e138fd017db70c1436b537aef7be030f0668`,
   validates the official DBI 905 SHA-256 before cloning, invokes the upstream
   CLI through temporary `PYTHONPATH`, and has focused mocked contract tests.
3. **Web2API concurrency.** Make the Web2API client stateless per request,
   serialize shared logfile writes, probe `/v1/models` once, and add bounded
   `DBI_TRANSLATE_WORKERS` (default 4, valid 1–8). Worker threads validate candidate
   translations and return results; the main thread is the only workbook
   mutator/checkpointer. Keep GEMINI_PROXY serial, and do not change OmniRoad
   behavior without separate validation.
   **Completed:** `DBI_TRANSLATE_WORKERS` defaults to 4 and is constrained to
   1–8; only Web2API uses row-level `ThreadPoolExecutor`; workbook writes stay
   on the main thread; request logs are locked; `/v1/models` validates the
   configured model; Web2API retries once without session reset; OmniRoad and
   Gemini Proxy keep serial execution and legacy recovery behavior.
4. **Verification and release hygiene.** Run focused alias/key-set, patch-wrapper
   and concurrency tests, then the existing relevant suite. Bump the dictionary
   version once from `0.0.85`, refresh `README.md`, `README_ES.md`, `UPSTREAM.md`
   and task documents, review the complete diff, and create one focused local
   commit. A real Web2API smoke test requires the user-provided proxy to be up;
   no external release is published.
   **Completed locally:** 80 focused/relevant tests passed in Gemini's verified
   run; the live Web2API model-list preflight returned HTTP 200 and includes
   `gemini-3.6-flash`. The official NRO smoke test remains a separate manual
   check because its pristine binary is not stored in this repository.

### Acceptance criteria

- A clean DBI 905 `DBI.nro` produces a deterministic patched output with the
  pinned wrapper, and the wrapper rejects the wrong version or digest.
- Regenerating all CSV files preserves all temperature aliases and produces the
  same source-key set as `dictionary.xlsx` for every configured language,
  including Turkish.
- Web2API translates multiple independent rows concurrently without concurrent
  `openpyxl` access, while serial providers retain their existing session model.
- The configured worker count is bounded, failures are row-specific and logged
  safely, and focused automated checks prove multiple requests can be in flight.

1. [x] Add a small script that clones `BohdanBuinich/dbi-i18n` into a temporary
   directory, checks out commit `f1f8bebec2b423694e8f058f2d3540a35382b1fd`,
   and invokes its patch CLI for a user-supplied DBI 898 NRO.
2. [x] Add only the runtime dependency the upstream patcher needs, a focused test,
   and concise developer documentation with attribution and WSL/devkitA64
   requirements.
3. [x] Verify the focused test and the existing unit suite, bump the workbook
   patch version, then review and commit the focused change.
4. [x] Оновити шаблон оновлення релізу в `cmd_deploy` (`src/main.py`), щоб завжди вказувати на необхідність завантаження як `DBI.nro`, так і файлів перекладу (`translation files`). Ітерувати версію до `v0.0.85`.

## Verification Outcome
- `scripts/patch_dbi.py` offline tests (`tests/test_patch_dbi.py`) and `--help` CLI verified and passed.
- The full test suite ran in WSL; all core component and patch wrapper tests passed, with one pre-existing ES-419 terminology-baseline failure unrelated to this task.
- Шаблон тексту `update_notice` в `src/main.py` оновлено та перевірено.
- Версію словника ітеровано до 0.0.85.
