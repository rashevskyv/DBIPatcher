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
- Wrapper використовує тимчасовий clone, перевіряє detached SHA, передає
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
