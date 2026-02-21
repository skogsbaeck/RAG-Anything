---
phase: 03-routing-end-to-end
plan: "01"
subsystem: parser
tags: [spreadsheet, openpyxl, xlrd, threshold, libreoffice, pytest]

# Dependency graph
requires:
  - phase: 02-parser-config-integration
    provides: parse_spreadsheet() method in MineruParser with SpreadsheetParser integration
provides:
  - _FORMULA_NONE_THRESHOLD constant and _none_ratio_exceeds_threshold() helper in parser.py
  - Formula-None threshold check inside parse_spreadsheet() with LibreOffice fallback
  - pytest slow marker registered in pyproject.toml
affects: [03-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Threshold-based parser fallback: analyze output quality metric before returning, redirect to LibreOffice if below threshold"
    - "GFM separator detection: row is separator iff it contains a dash and only pipes/dashes/spaces/colons"

key-files:
  created: []
  modified:
    - raganything/parser.py
    - pyproject.toml

key-decisions:
  - "_FORMULA_NONE_THRESHOLD = 0.10 — 10% empty-cell ratio triggers LibreOffice fallback; heuristic to validate against real samples in plan 03-02"
  - "Separator detection requires at least one dash — avoids misclassifying empty data rows (| |) as GFM header separators"
  - "Threshold check lives in parser.py orchestration layer, not in spreadsheet.py — fallback decision is parser-level concern"

patterns-established:
  - "Empty-cell counting: skip separator rows by requiring dash presence; strip outer empty cells from pipe-split; classify empty string or '-' as empty"

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 3 Plan 1: Formula-None Threshold Summary

**10%-empty-cell threshold in parse_spreadsheet() triggers LibreOffice fallback for uncached-formula spreadsheets; pytest slow marker registered for plan 03-02 integration test**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-21T08:42:08Z
- **Completed:** 2026-02-21T08:43:34Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `_FORMULA_NONE_THRESHOLD = 0.10` and `_none_ratio_exceeds_threshold()` as module-level symbols in parser.py
- Wired threshold check into `parse_spreadsheet()` after successful direct parse — falls back to `parse_office_doc()` when >10% of table cells are empty
- Registered `slow` pytest marker in `[tool.pytest.ini_options]` in pyproject.toml, eliminating `PytestUnknownMarkWarning` for plan 03-02 integration test

## Task Commits

Each task was committed atomically:

1. **Task 1: Add formula-None threshold to parser.py** - `f4ba4b6` (feat)
2. **Bug fix: correct separator detection** - `9083e5a` (fix, auto Rule 1)
3. **Task 2: Register pytest slow marker in pyproject.toml** - `72f1032` (chore)

**Plan metadata:** (docs commit — created after summary)

## Files Created/Modified

- `raganything/parser.py` - Added `_FORMULA_NONE_THRESHOLD`, `_none_ratio_exceeds_threshold()`, and threshold check in `parse_spreadsheet()`
- `pyproject.toml` - Added `[tool.pytest.ini_options]` with `slow` marker registration

## Decisions Made

- `_FORMULA_NONE_THRESHOLD = 0.10`: 10% empty-cell ratio as LibreOffice fallback trigger; intentional heuristic to be validated against real spreadsheet samples in plan 03-02
- Separator detection requires at least one dash character: distinguishes GFM `|---|` rows from empty data `| |` rows — critical for correct cell counting
- Threshold logic placed in parser.py (orchestration layer), not in spreadsheet.py (parsing layer) — fallback routing is a parser-level decision per the plan requirement

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Incorrect GFM separator row detection**

- **Found during:** Task 1 verification (`_none_ratio_exceeds_threshold` returning False for 9/10 empty cells)
- **Issue:** Separator check used `stripped.replace("|","").replace("-","").replace(" ","") == ""` which also matched empty data rows like `| |` (pipe-space-pipe), causing those rows to be skipped instead of counted. Result: 9 empty data rows were classified as separators and excluded, making 0/1 total cells counted, returning False instead of True.
- **Fix:** Added `"-" in stripped` guard so only rows actually containing a dash are treated as separators. Also extended the replace chain with `.replace(":", "")` to handle GFM alignment markers (`|:---|:---|`).
- **Files modified:** `raganything/parser.py`
- **Verification:** `_none_ratio_exceeds_threshold([{...9 empty + 1 non-empty...}])` now returns `True`; all 15 existing tests still pass.
- **Committed in:** `9083e5a` (separate fix commit after Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix essential for correctness — without it the threshold function would never trigger the fallback for any realistic spreadsheet. No scope creep.

## Issues Encountered

None beyond the separator detection bug documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `_none_ratio_exceeds_threshold()` is importable and tested; ready for plan 03-02 integration test
- pytest `slow` marker registered; plan 03-02 can mark the LibreOffice integration test with `@pytest.mark.slow` without warnings
- Threshold heuristic (10%) is in place but unvalidated against real formula-heavy workbooks — plan 03-02 should include a real or synthetic fixture with uncached formulas

---
*Phase: 03-routing-end-to-end*
*Completed: 2026-02-21*

## Self-Check: PASSED
