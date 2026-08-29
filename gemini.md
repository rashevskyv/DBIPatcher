# Gemini Activity Log

## [2026-08-29] Safe Shadok localization command

### Виконані дії:
1. Додано `cmd_shadok` + helpers у `src/main.py` (resolve by orig, validate block, serial per-lang writes).
2. Оновлено `translate_shadok_block` / `data/prompts.json` під контракт `expected_lines` + `max_line_length`.
3. `cmd_translate` / `cmd_align` виключають Shadok через `build_shadok_exclusion_rows` (strict resolve з fallback по `orig`); `cmd_validate` має integrity phase зі strict resolve.
4. Прибрано застарілий `translated_langs` з `data/shadok.json`; ціль = усі коди `languages.json` крім `ru`.
5. Документація README/README_ES/Known Issues; offline тести `tests/test_shadok_localization.py`.
6. Live `shadok`/translate/export/build НЕ запускались; workbook/CSV користувача не чіпались.

## [2026-08-29] Shadok screen reflow contract

### Виконані дії:
1. Уточнено `data/prompts.json` shadok: це один екранний текстовий блок — літературна локалізація + word-wrap/reflow у рівно N рядків ≤ max_line_length (слова можуть переходити між рядками).
2. Прибрано суперечливе «Do NOT merge or split lines»; валідація лишається: рівно N непорожніх рядків, кожен ≤ ліміту, без автообрізання.

## [2026-08-29] Shadok retries with escalating strictness

### Виконані дії:
1. До 3 спроб на мову: кожен retry додає строгіший system prompt (LEVEL 1 / LEVEL 2 FINAL) з previous_error + previous_text.
2. Harden JSON fallback: unescape `\\n` після ручного витягу значення (фікс «got 1 line»).
3. Offline тести на escalation і успіх на 3-й спробі.

## [2026-08-29] Shadok: fewer lines OK, overflow only is bad

### Виконані дії:
1. Контракт екрана розділено: висота `max_lines=35`, ширина `max_line_length=39`.
2. Менше 35 рядків — OK; більше 35 — overflow. 34 більше не заворачується «бо не 33».
3. У словнику 33 orig-слоти: коротший блок падиться `" "`; 34–35 пакуються в останній слот через `[[LF]]`.
4. Shadok Web2API модель: `gemini-3.7-flash` (окремо від general translate 3.6).
5. Промпт: явний контекст алегорії РФ–Україна (болотні постаті = росіяни); не sanitizити.

## [2026-04-23] Початкова ініціалізація

### Виконані дії:
1.  **Реорганізація**: Створено папки `scripts/` та `src/core/`.
2.  **Переміщення**: `build_translation_bin.py` перенесено в `scripts/`.
3.  **Документація**: Створено `implementation_plan.md` та `task.md`.
4.  **Інсталяція**: Встановлено `openpyxl` та `requests`.

### Комміти:
- `Init`: Початковий стан проекту та нова структура.

## [2026-04-23] Розробка Core та Pipeline

### Виконані дії:
1.  **text_utils.py**: Реалізовано токенізацію (`tokenize`, `detokenize`, `normalize_tokens_out`).
2.  **validator.py**: Реалізовано 4 правила валідації (NotEmpty, RuPlaceholder, EnglishPreservation, TokenPreservation).
3.  **ai_client.py**: Клієнт для Gemini Proxy (`http://127.0.0.1:2048`), модель `gemini-flash-lite-latest`. Системний промпт з усіма правилами перекладу.
4.  **main.py**: Головний пайплайн з командами `sync`, `translate`, `validate`, `export`, `build`, `all`.
5.  **.gitignore**: Оновлено — виключено `*.nro`, `*.bin`, `output/`, `dictionary.xlsx`.
6.  **Видалено** `DBI.892.ru_patched.nro` з репозиторію (бінарник, не повинен бути в Git).

### Комміти:
- `feat: core modules (text_utils, validator, ai_client) and main pipeline`

### Фінальна структура:
```
dbi_patcher/
├── .gitignore
├── gemini.md
├── implementation_plan.md
├── task.md
├── languages.json
├── ua.csv
├── scripts/
│   └── build_translation_bin.py
└── src/
    ├── __init__.py
    ├── main.py
    └── core/
        ├── __init__.py
        ├── text_utils.py
        ├── validator.py
        └── ai_client.py
```

## [2026-04-23] Тестування та Синхронізація

### Виконані дії:
1.  **Синхронізація**: Успішно виконано `python -m src.main sync`. Додано 1205 записів у `data/dictionary.xlsx`.
2.  **Валідація структури**: Перевірено створення Excel-файлу з метаданими та версійністю.
3.  **Оновлення плану**: Крок `sync` помічено як виконаний.

### Комміти:
- `test: successful sync with real data (1205 entries)`

## [2026-04-23] Оновлення логіки Синхронізації

### Виконані дії:
1.  **Зміна cmd_sync**: Тепер `sync` додає лише оригінальні російські рядки. Колонки перекладів залишаються порожніми для заповнення через AI.
2.  **Нова команда cmd_clear**: Додано можливість очищення конкретної мови у словнику: `python -m src.main clear <lang>`.
3.  **Оновлення CLI**: Додано підтримку аргументу `lang` для команди `clear`.

### Комміти:
- `feat: sync only original strings and added clear command`

## [2026-04-23] Оптимізація сесій AI

### Виконані дії:
1.  **Context Management**: Реалізовано збереження контексту чату. Системний промпт тепер передається лише один раз на початку сесії.
2.  **Session Reset**: Додано виклик `new-chat` перед початком кожного циклу перекладу для автоматичного очищення інтерфейсу AI Studio.
3.  **JSON Robustness**: Покращено парсинг JSON відповідей (обробка Markdown блоків) та додано вивід сирого тексту при помилках декодування.

### Комміти:
- `fix: implement stateful sessions and correct system instructions for proxy`

## [2026-04-25] Перехід на OmniRoad (Sonnet 4.5)

### Виконані дії:
1.  **Діагностика**: Виявлено, що модель Sonnet 4.5 доступна через OmniRoad під назвою `kr/claude-sonnet-4.5` на `http://localhost:20128/v1`.
2.  **ai_client.py**: Реалізовано підтримку декількох провайдерів (`GEMINI_PROXY` та `OMNIROAD`).
3.  **OpenAI Compatibility**: Додано логіку формування `messages` з системним промптом для OmniRoad, оскільки він не підтримує кастомні ендпоінти Gemini Proxy.
4.  **Валідація**: Підтверджено роботу нового провайдера через успішні запити в логах.
5.  **Фікс багів**: Виправлено помилки конкатенації та відступів, що виникли під час рефакторингу.

### Комміти:
- `feat: support OmniRoad (Sonnet 4.5) with OpenAI-compatible API`

## [2026-04-25] Оптимізація логіки вибору рядків та Валідації

### Виконані дії:
1.  **Cyrillic Threshold**: В `main.py` змінено поріг перекладу. Тепер рядки з 3 або менше кириличними символами вважаються технічними і копіюються as-is.
2.  **Validator Correction**: Логіку перевірки дужок змінено з "балансу/вкладеності" на "відповідність кількості". Тепер валідатор просто порівнює кількість символів `(`, `)`, `[` , `]`, які мають співпадати з оригіналом. Це вирішує проблему з ANSI-кодами (типу `[31m`) та іншими технічними символами.
3.  **Логування**: Додано вивід кількості знайдених кириличних символів при пропуску рядка.

### Комміти:
- `refactor: translate only strings with >3 cyrillic chars and fix bracket validation`

## [2026-04-30] Автоматизація деплою та релізів

### Виконані дії:
1.  **Команда deploy**: Реалізовано повний цикл деплою:
    - Перевірка повноти перекладу.
    - Копіювання файлів у цільові директорії (Kefir/Switch).
    - Автоматичний комміт та пуш змін у Git.
    - Автоматичне створення/оновлення релізу на GitHub через `gh` CLI.
    - **Покращення релізів**: Тепер `DBI.*_patched.nro` автоматично копіюється та перейменовується в `DBI.nro` для завантаження в активи релізу.
    - **Реліз-ноти**: Додано чітке попередження про те, що переклад сумісний лише з версією NRO з релізу.
2.  **README.md**: Повністю оновлено дизайн, додано інструкції та попередження про сумісність.
3.  **Версіонування**: Реалізовано автоматичне ітерування версії при кожному деплої.

### Комміти:
- `chore: deploy DBI 894 localization (v0.0.79)`

## [2026-05-02] Оновлення документації та версіонування
### Виконані дії:
1.  **README.md**: Відновлено інформацію про неперекладені елементи (байки Шадоків та назви мов у налаштуваннях), які були втрачені при редизайні.
2.  **src/main.py**: Аналогічні зміни внесено у шаблон опису релізів GitHub.
3.  **Версіонування**: Виконано ітерацію версії до `v0.0.79` перед комітом.
4.  **Уточнення**: Прямо вказано значення російських кнопок "Да/Нет" для іноземних користувачів.

### Комміти:
- `docs: clarify hardcoded strings (Yes/No, Shadoks, LangNames) and bump version to v0.0.79`

## [2026-07-07] Інтеграція нових мов та налаштування Gemini 3.5 Flash

### Виконані дії:
1.  **Інтеграція PR #14 (Turkish)**:
    - Витягнуто файл `translations/tr.csv`.
    - Додано турецьку мову `"tr": "Turkish"` в конфігурацію `data/languages.json` з виправленням JSON-синтаксису (пропущена кома).
2.  **Інтеграція PR #16 (Spanish LA)**:
    - Витягнуто файли `translations/es419.csv`, `README_ES.md` та `docs/es419-style-guide.md`.
    - Збережено стабільність коду — зміни коду з PR #16 не імпортувалися, оскільки вони конфліктували з поточною логікою blocks та містили невикористовуваний код.
3.  **Оновлення blocks.json**:
    - Вилучено застарілі рядки `"NAND"` та `" SD "` з блоку `NSP_INSTALL_ANSWERS` у `data/blocks.json`, що усунуло помилки валідації.
4.  **ai_client.py**:
    - Додано підтримку провайдера `WEB2API` (модель `gemini-3.5-flash` на порті `8081`).
    - Провайдер `WEB2API` встановлено за замовчуванням.
5.  **Запуск Pipeline**:
    - Запущено `sync`, `translate`, `validate`, `export`, `build`.
    - Усі 26620 перекладів для 23 мов успішно провалідовано з 0 помилок.
    - Успішно згенеровано бінарні файли `.bin` для всіх мов, включаючи `translation_tr.bin` та `translation_es419.bin`.

### Комміти:
- `feat: integrate Turkish and Latin American Spanish localizations, configure Gemini 3.5 Flash support (v0.0.83)`

## [2026-08-14] Оновлення тексту сповіщення про оновлення релізу

### Виконані дії:
1.  **src/main.py (`cmd_deploy`)**: Змінено логіку генерації плашки оновлення релізу (`update_notice`). Тепер вона завжди вказує користувачам повторно завантажувати обидва файли: `DBI.nro` та файли перекладу (`translation files`).
2.  **Очищення застарілої логіки**: Вилучено ненадійну перевірку розміру віддаленого NRO (`nro_changed`), оскільки при оновленні релізу завжди обов'язково оновлювати як бінарник, так і переклади.
3.  **Версіонування**: Ітеровано версію до `v0.0.85`.

### Комміти:
- `fix: always prompt to redownload both DBI.nro and translation files on release update (v0.0.85)`

## [2026-08-29] DBI 905, durable aliases та Web2API concurrency

### Виконані дії:
1. Додано durable union 45 temperature alias-ів з PR #22 і PR #23 до workbook,
   усіх CSV та Turkish-колонки; видалено дубльовану `cmd_sync`.
2. `scripts/patch_dbi.py` перенесено з DBI 898 `dbi-i18n` на pinned DBI 905
   `0xroast/dbi-translate`, додано SHA-256 перевірку pristine NRO та нові
   Keystone/Capstone залежності.
3. Web2API перекладає незалежні рядки обмеженим пулом потоків. Workbook
   змінюється тільки головним потоком; retry/refine, logging і model preflight
   адаптовані для stateless concurrent requests.
4. Додано focused regression tests. Gemini перевірив 80 тестів та live
   `/v1/models` preflight; application workbook version — `v0.0.86`.

### Комміти:
- `feat: migrate DBI 905 patcher and parallelize Web2API translations (v0.0.86)`

## [2026-08-29] Data-loss remediation in cmd_translate and cmd_sync (v0.0.87)

### Виконані дії:
1. **cmd_translate**: Виправлено дефект передчасного стирання невалідних перекладів під час попереднього сканування рядків. Старі значення тепер зберігаються в пам'яті та у чекпоінтах, якщо AI-переклад або валідація зазнали невдачі.
2. **cmd_sync**: Виправлено дефект видалення рядків зі застарілими індексами при наявності кількох груп дублікатів. Реалізовано попереднє злиття непорожніх клітинок у перший збережений рядок та єдиний спадний прохід видалення дублікатів.
3. **Регресійні тести**: Додано тести для збереження значень при збоях перекладу в `test_web2api_concurrency.py` та тест злиття/видалення дублікатів у `test_temperature_aliases_and_sync.py`.
4. **Версіонування**: Ітеровано версію метаданих `data/dictionary.xlsx` до `0.0.87`.

## [2026-08-29] Release Hardening & Documentation Parity

### Виконані дії:
1. **scripts/patch_dbi.py**: Додано перевірку на ідентичність вхідного та вихідного шляхів NRO (`resolved_nro == resolved_output`), що викидає `ValueError` до клонування чи виклику інструментів. Додано регресійний тест у `tests/test_patch_dbi.py`.
2. **src/core/ai_client.py**: Усунено подвійний виклик `_log_interaction` при невдалих HTTP-запитах. Додано регресійний тест у `tests/test_web2api_concurrency.py`.
3. **src/main.py**: Переведено розрахунок київського часу на `ZoneInfo("Europe/Kyiv")`.
4. **Документація**: Оновлено назву моделі Web2API до `gemini-3.6-flash` у `README.md`, виправлено опис валідації у воркерах у `plan.md` та актуалізовано `task.md`.

