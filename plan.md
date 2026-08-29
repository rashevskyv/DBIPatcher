# Active plan: upstream DBI patcher & release updates

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
