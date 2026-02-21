---
phase: 03-routing-end-to-end
plan: "02"
subsystem: testing
tags: [spreadsheet, openpyxl, pytest, e2e, mocking, caplog, threshold]

# Dependency graph
requires:
  - phase: 03-routing-end-to-end/03-01
    provides: _none_ratio_exceeds_threshold() helper and threshold wired into parse_spreadsheet()
  - phase: 02-parser-config-integration
    provides: parse_spreadsheet() in MineruParser, SpreadsheetParser integration
provides:
  - E2E test suite covering full spreadsheet pipeline (routing, contract, fallback, threshold)
  - Provable Phase 3 success criteria via test assertions
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sys.modules[module] = None pattern for simulating ImportError from local imports"
    - "patch raganything.spreadsheet.SpreadsheetParser.parse (not raganything.parser) because import is local"
    - "caplog.at_level scoped to 'raganything.parser' logger for WARNING capture"

key-files:
  created:
    - tests/test_e2e_spreadsheet.py
  modified: []

key-decisions:
  - "Patch SpreadsheetParser.parse at raganything.spreadsheet (not raganything.parser) — local import pattern means parser module has no direct attribute"
  - "sys.modules trick for ImportError simulation: set module to None temporarily, restore in finally block"
  - "Slow integration test (test_real_lightrag_integration) uses only parse_spreadsheet() — no LightRAG init needed, simplification per plan option"

patterns-established:
  - "Local import patching: always patch the module that owns the class (raganything.spreadsheet.SpreadsheetParser), not the module that does the local import"
  - "_create_workbook helper: builds xlsx from dict[sheet_name, 2D_rows] via openpyxl — reusable across all spreadsheet test modules"

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 3 Plan 2: E2E Spreadsheet Pipeline Tests Summary

**Mock-based E2E test suite with 10 fast CI tests + 1 slow integration test proving direct parser, content contract, fallback, WARNING logs, and formula-None threshold**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-21T08:46:16Z
- **Completed:** 2026-02-21T08:48:23Z
- **Tasks:** 2 (both implemented in single file, committed atomically)
- **Files created:** 1

## Accomplishments

- Created `tests/test_e2e_spreadsheet.py` with 11 tests (10 fast, 1 slow) covering the full spreadsheet pipeline
- Proved Phase 3 success criteria: direct parser invoked, content contract correct (`type=="table"`), fallback works, threshold triggers LibreOffice path
- `_none_ratio_exceeds_threshold()` validated with edge cases (empty list, non-table items, boundary conditions)
- All 72 fast tests pass; full test suite regression-clean

## Task Commits

Each task was committed atomically:

1. **Tasks 1+2: Create E2E spreadsheet tests (fast + slow combined)** - `5609fbc` (test)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `tests/test_e2e_spreadsheet.py` - 11-test E2E suite: routing, contract, multi-sheet, fallback, WARNING logging, threshold unit tests, threshold-triggered fallback, ImportError propagation, slow integration test

## Decisions Made

- Patching at `raganything.spreadsheet.SpreadsheetParser.parse` (not `raganything.parser`): `parse_spreadsheet()` uses a local import, so `SpreadsheetParser` is never bound at parser module level. Attempting to patch `raganything.parser.SpreadsheetParser` raises `AttributeError`.
- `sys.modules["raganything.spreadsheet"] = None` for ImportError simulation: cleanly intercepts the `from raganything.spreadsheet import ...` inside `parse_spreadsheet()` without permanently affecting the module cache (restored in `finally`).
- Slow test simplified to `parse_spreadsheet()` only: full LightRAG init requires API keys and infrastructure; plan explicitly permitted this simplification. Test still proves data survives the parsing pipeline end-to-end.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong patch target for SpreadsheetParser.parse**

- **Found during:** Task 1 verification (`TestFallbackOnParseFailure` test)
- **Issue:** Initial patch used `raganything.parser.SpreadsheetParser.parse` — but `SpreadsheetParser` is imported locally inside `parse_spreadsheet()`, not at module level, so `AttributeError: module 'raganything.parser' has no attribute 'SpreadsheetParser'` was raised.
- **Fix:** Changed patch target to `raganything.spreadsheet.SpreadsheetParser.parse` — the module that owns the class.
- **Files modified:** `tests/test_e2e_spreadsheet.py`
- **Verification:** Test passes; fallback sentinel returned; WARNING log captured.
- **Committed in:** `5609fbc` (same task commit, fixed before committing)

**2. [Rule 1 - Bug] Wrong patch strategy for ImportError test**

- **Found during:** Task 1 verification (`TestImportErrorPropagates` test)
- **Issue:** Initial approach `patch("raganything.parser.SpreadsheetParser", side_effect=ImportError(...))` failed with same `AttributeError` — module-level attribute doesn't exist.
- **Fix:** Used `sys.modules["raganything.spreadsheet"] = None` which causes Python to raise `ImportError` on `from raganything.spreadsheet import ...`. Module restored in `finally` block.
- **Files modified:** `tests/test_e2e_spreadsheet.py`
- **Verification:** `pytest.raises(ImportError)` passes; `parse_office_doc` not called.
- **Committed in:** `5609fbc` (same task commit, fixed before committing)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes necessary for correct mock targets — Python's local import pattern requires patching at the owning module. No scope creep.

## Issues Encountered

Two test failures during initial run due to local import patching mechanics (documented as deviations above). Fixed iteratively before committing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 fully complete: all success criteria provably met by test assertions
- `tests/test_e2e_spreadsheet.py` is the canonical Phase 3 verification artifact
- The `.gitignore test_*` pattern requires `git add -f` for all test file commits — this should be narrowed in future infra work

---
*Phase: 03-routing-end-to-end*
*Completed: 2026-02-21*

## Self-Check: PASSED
