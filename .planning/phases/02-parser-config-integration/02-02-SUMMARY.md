---
phase: 02-parser-config-integration
plan: "02"
subsystem: parser
tags: [spreadsheet, routing, asyncio, processor, config, testing]

# Dependency graph
requires:
  - phase: 02-01-parser-config-integration
    provides: parse_spreadsheet() on MineruParser + RAGAnythingConfig spreadsheet fields
provides:
  - Spreadsheet routing branch in ProcessorMixin.parse_document()
  - Zero-content guard conditioned on direct spreadsheet path
  - Processor routing test suite (8 tests)
affects: [03-validation-and-testing, future phases using parse_document]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Direct spreadsheet routing: config flag gates which parser path is called in ProcessorMixin"
    - "Zero-content guard exemption: is_direct_spreadsheet bool bypasses guard for empty workbook case"

key-files:
  created:
    - tests/test_processor_spreadsheet.py
  modified:
    - raganything/processor.py

key-decisions:
  - "is_direct_spreadsheet flag is True even when parse_spreadsheet() internally falls back to LibreOffice — the guard is bypassed in both internal paths because they share the same config flag"
  - "Spreadsheet branch placed BEFORE Office/HTML branch to prevent .xls/.xlsx ever reaching parse_office_doc when direct parsing is enabled"

patterns-established:
  - "Routing pattern: separate elif blocks per file format family, ordered most-specific first"
  - "Guard exemption pattern: compute bool from ext+config, test it alongside len()==0"

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 2 Plan 02: Processor Spreadsheet Routing Summary

**ProcessorMixin routes .xls/.xlsx to parse_spreadsheet() via config flag, with zero-content guard exemption for empty workbooks; 8 routing tests using asyncio.to_thread mocking.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-21T07:25:06Z
- **Completed:** 2026-02-21T07:26:46Z
- **Tasks:** 2
- **Files modified:** 2 (processor.py modified, test_processor_spreadsheet.py created)

## Accomplishments
- Split .xls/.xlsx out of the Office/HTML elif into a dedicated spreadsheet elif branch
- Config flag `enable_direct_spreadsheet_parsing` gates routing: True → `parse_spreadsheet()`, False → `parse_office_doc()`
- `spreadsheet_max_rows_per_chunk` flows from config into the `parse_spreadsheet()` call
- Zero-content guard updated: `is_direct_spreadsheet` bool allows empty content_list from direct spreadsheet path (empty workbook is valid, not a parse failure)
- 8 processor routing tests cover all routing conditions using `_StubProcessor` duck-typing and `asyncio.to_thread` mocking

## Task Commits

Each task was committed atomically:

1. **Task 1: Split spreadsheet routing and fix zero-content guard** - `cb67a77` (feat)
2. **Task 2: Processor routing tests for spreadsheet dispatch** - `3c8fe74` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `raganything/processor.py` - New spreadsheet elif branch before Office/HTML branch; updated zero-content guard with `is_direct_spreadsheet` condition
- `tests/test_processor_spreadsheet.py` - 8 routing tests for ProcessorMixin spreadsheet dispatch

## Decisions Made
- `is_direct_spreadsheet` is True whenever the config enables direct parsing, regardless of what `parse_spreadsheet()` does internally (including its own LibreOffice fallback). This means even when `parse_spreadsheet()` internally falls back to LibreOffice and returns empty, the guard is still bypassed. Design rationale: if both SpreadsheetParser AND the internal LibreOffice fallback find no content, the workbook is genuinely unparseable — raising ValueError would not help.
- `_StubProcessor` approach chosen for tests: binds the real `ProcessorMixin` methods via class body assignment, duck-typing required attributes (config, logger, parse_cache). Avoids instantiating the full RAGAnything/LightRAG stack while testing real production code.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 2 (Parser-Config Integration) is now complete: parse_spreadsheet() exists on MineruParser, config fields added, ProcessorMixin routing in place, and all tests pass.
- Phase 3 (Validation and Testing) can proceed: formula-None threshold heuristic validation against real samples, xlrd .xls fixture coverage, and broader integration testing.
- Known concern carried forward: formula-None threshold (>10% triggers LibreOffice fallback) is a heuristic — validate against real samples in Phase 3.

---
*Phase: 02-parser-config-integration*
*Completed: 2026-02-21*

## Self-Check: PASSED
