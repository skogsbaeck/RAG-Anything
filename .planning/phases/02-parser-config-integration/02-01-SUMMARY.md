---
phase: 02-parser-config-integration
plan: 01
subsystem: parser
tags: [spreadsheet, openpyxl, xlrd, config, parser, raganything]

# Dependency graph
requires:
  - phase: 01-spreadsheet-parser-core
    provides: SpreadsheetParser and SpreadsheetConfig in raganything/spreadsheet.py
provides:
  - parse_spreadsheet() method on MineruParser with guarded import, ImportError re-raise, LibreOffice fallback
  - enable_direct_spreadsheet_parsing and spreadsheet_max_rows_per_chunk config fields in RAGAnythingConfig
  - SPREADSHEET_FORMATS class constant on Parser base class
  - .xls/.xlsx routing through parse_spreadsheet() in parse_document()
affects:
  - Phase 3 (E2E and validation)
  - Any future parsers inheriting from Parser base class

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Guarded import inside method body (not module-level) for optional dependencies"
    - "ImportError re-raise before general except to distinguish hard errors from soft fallbacks"
    - "LibreOffice fallback pattern for non-ImportError exceptions in direct parsers"

key-files:
  created:
    - tests/test_parse_spreadsheet.py
  modified:
    - raganything/config.py
    - raganything/parser.py

key-decisions:
  - "env var prefix RAG_ANYTHING_ for new spreadsheet config fields (intentional divergence from existing unprefixed fields)"
  - "ImportError is a hard error (re-raised) — missing deps should not silently fall back to LibreOffice"
  - ".xls and .xlsx removed from OFFICE_FORMATS, added to new SPREADSHEET_FORMATS constant"
  - "parse_spreadsheet() stores nothing on self (MineruParser has __slots__ = ())"

patterns-established:
  - "Optional parser module: guarded import inside method + ImportError re-raise + non-ImportError fallback"

# Metrics
duration: 1min
completed: 2026-02-21
---

# Phase 2 Plan 01: Parser-Config Integration Summary

**parse_spreadsheet() method wired into MineruParser with guarded import, ImportError hard-error, LibreOffice fallback, and two RAGAnythingConfig spreadsheet fields**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-21T07:21:07Z
- **Completed:** 2026-02-21T07:22:36Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `enable_direct_spreadsheet_parsing` (default True) and `spreadsheet_max_rows_per_chunk` (default 150) to RAGAnythingConfig
- Added `SPREADSHEET_FORMATS = {".xls", ".xlsx"}` to Parser base class; removed from OFFICE_FORMATS
- Implemented `parse_spreadsheet()` on MineruParser following the exact parse_audio() pattern
- `parse_document()` now routes .xls/.xlsx through `parse_spreadsheet()` instead of `parse_office_doc()`
- 7 integration tests covering: happy path, fallback, ImportError propagation, FileNotFoundError, config flow, .xls routing, config defaults

## Task Commits

Each task was committed atomically:

1. **Task 1: Add spreadsheet config fields and parse_spreadsheet method** - `82cdaf7` (feat)
2. **Task 2: Integration tests for parse_spreadsheet** - `5e8183d` (feat)

**Plan metadata:** `(docs commit follows)`

## Files Created/Modified

- `raganything/config.py` - Added enable_direct_spreadsheet_parsing and spreadsheet_max_rows_per_chunk fields
- `raganything/parser.py` - Added SPREADSHEET_FORMATS, parse_spreadsheet(), updated parse_document() routing
- `tests/test_parse_spreadsheet.py` - 7 integration tests (created; requires git add -f due to gitignore pattern)

## Decisions Made

- **env var prefix:** New spreadsheet config fields use `RAG_ANYTHING_` prefix per user decision; intentionally diverges from existing unprefixed fields
- **ImportError is a hard error:** Re-raised before the general except — missing openpyxl/xlrd should not silently fall back to LibreOffice
- **SPREADSHEET_FORMATS separate from OFFICE_FORMATS:** Enables clean routing distinction in parse_document()
- **No env var override test:** get_env_value evaluates at class definition time; monkeypatch.setenv after import cannot affect field defaults

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- parse_spreadsheet() is fully wired and tested
- SpreadsheetParser integration path is operational end-to-end for xlsx
- Phase 3 (E2E validation) can proceed: xlrd .xls E2E, formula-None heuristic validation against real samples
- Concern carried forward: .gitignore `test_*` pattern still requires `git add -f` for test files

---
*Phase: 02-parser-config-integration*
*Completed: 2026-02-21*

## Self-Check: PASSED
