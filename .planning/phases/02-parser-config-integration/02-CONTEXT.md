# Phase 2: Parser + Config Integration - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire SpreadsheetParser (built in Phase 1) into MineruParser with a `parse_spreadsheet()` method, config flags to enable/disable direct parsing, and fallback to LibreOffice PDF path on failure. No new parsing capabilities — this is integration plumbing.

</domain>

<decisions>
## Implementation Decisions

### Fallback behavior
- Auto fallback: if SpreadsheetParser throws any exception, fall back to LibreOffice PDF path automatically
- Log at WARNING level with filename + exception type (e.g. "Direct parse failed for report.xlsx (MergeError), falling back to LibreOffice")
- No fallback on empty result — zero content items is valid (workbook genuinely had no data)
- No formula-None threshold — trust data_only=True results as-is, don't second-guess

### Config flag design
- `enable_direct_spreadsheet_parsing` lives in RAGAnything constructor (not env var)
- Default: True (direct parsing on by default)
- `max_rows_per_chunk` exposed at RAGAnything level, not just internal SpreadsheetConfig
- Env var prefix: `RAG_ANYTHING_` (e.g. `RAG_ANYTHING_DIRECT_SPREADSHEET`, `RAG_ANYTHING_SPREADSHEET_MAX_ROWS`)

### Error handling strategy
- Missing openpyxl/xlrd = hard error (ImportError with helpful install message) — don't silently degrade
- Corrupted/password-protected files trigger fallback to LibreOffice (it might handle what openpyxl can't)
- Partial sheet failure: skip the bad sheet with WARNING, continue processing remaining sheets
- Content_list contract validation: assert in debug mode only (trust SpreadsheetParser in production)

### xlrd adapter approach
- Single entry point: `parse_spreadsheet()` handles both .xls and .xlsx — SpreadsheetParser already dispatches by extension
- Missing xlrd for .xls file = hard error (ImportError), not fallback
- .xls testing deferred to Phase 3 E2E — Phase 2 tests focus on xlsx integration path
- xlrd date tuple conversion: normalize to Python datetime before passing to format_cell_value (same pipeline as xlsx)

### Claude's Discretion
- xlrd date tuple → datetime conversion implementation details
- Debug assertion implementation (assert vs logging)
- Exact env var parsing logic
- How config flows from RAGAnything constructor down to SpreadsheetParser

</decisions>

<specifics>
## Specific Ideas

- Fallback pattern should match existing error handling in the codebase (audio module uses similar guarded imports)
- The WARNING log on fallback must include both the filename and exception type — not just "fallback triggered"
- Hard error on missing deps is deliberate: users who enable the feature should install the deps, not silently get worse results via LibreOffice

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-parser-config-integration*
*Context gathered: 2026-02-21*
