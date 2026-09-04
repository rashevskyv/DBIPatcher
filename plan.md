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
