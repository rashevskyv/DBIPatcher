# Active plan: upstream DBI patcher

1. [x] Add a small script that clones `BohdanBuinich/dbi-i18n` into a temporary
   directory, checks out commit `f1f8bebec2b423694e8f058f2d3540a35382b1fd`,
   and invokes its patch CLI for a user-supplied DBI 898 NRO.
2. [x] Add only the runtime dependency the upstream patcher needs, a focused test,
   and concise developer documentation with attribution and WSL/devkitA64
   requirements.
3. [x] Verify the focused test and the existing unit suite, bump the workbook
   patch version, then review and commit the focused change.

## Verification Outcome
- `scripts/patch_dbi.py` offline tests (`tests/test_patch_dbi.py`) and `--help` CLI verified and passed.
- The full test suite ran in WSL; all core component and patch wrapper tests passed, with one pre-existing ES-419 terminology-baseline failure unrelated to this task.
