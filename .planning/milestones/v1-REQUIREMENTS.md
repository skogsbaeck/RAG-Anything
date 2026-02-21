# Requirements Archive: v1 Direct Spreadsheet Parsing

**Archived:** 2026-02-21
**Status:** SHIPPED

This is the archived requirements specification for v1.
For current requirements, see `.planning/REQUIREMENTS.md` (created for next milestone).

---

## v1 Requirements

### Core Parsing

- [x] **PARSE-01**: Parser reads all sheets in an xlsx/xls workbook independently
- [x] **PARSE-02**: Cell values coerced to clean strings (datetime, float, bool, None handled)
- [x] **PARSE-03**: Formula cells resolved to cached computed values via `data_only=True`
- [x] **PARSE-04**: Empty rows/columns stripped from each sheet before rendering
- [x] **PARSE-05**: Merged cells annotated with `[merged NxM]` on anchor cell, siblings marked empty
- [x] **PARSE-06**: Each sheet rendered as a GFM markdown table with all rows as data (no header inference — LLM interprets structure)
- [x] **PARSE-07**: Empty and hidden sheets skipped automatically
- [x] **PARSE-08**: Markdown special characters (pipes, newlines) sanitized in cell values
- [x] **PARSE-09**: Large sheets chunked at configurable row limit to prevent token explosion

### Integration

- [x] **INTG-01**: `SpreadsheetParser` module created following `audio.py` pattern
- [x] **INTG-02**: `parse_spreadsheet` method added to `MineruParser` with guarded import
- [x] **INTG-03**: ProcessorMixin routes `.xls`/`.xlsx` to direct parser before Office branch
- [x] **INTG-04**: Fallback to LibreOffice PDF path on direct parse failure with explicit logging
- [x] **INTG-05**: `xlrd` adapter for legacy `.xls` files with unified interface
- [x] **INTG-06**: content_list items match existing contract (type, table_body, table_caption, page_idx)

### Configuration

- [x] **CONF-01**: `enable_direct_spreadsheet_parsing` config flag (default: True)
- [x] **CONF-02**: `spreadsheet_max_rows_per_sheet` config option with env var support
- [x] **CONF-03**: `spreadsheet` optional dependency group in pyproject.toml

### Metadata

- [x] **META-01**: Table caption includes workbook filename and sheet name
- [x] **META-02**: Sheet index mapped to `page_idx` for multi-sheet context

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PARSE-01 | Phase 1 | Complete |
| PARSE-02 | Phase 1 | Complete |
| PARSE-03 | Phase 1 | Complete |
| PARSE-04 | Phase 1 | Complete |
| PARSE-05 | Phase 1 | Complete |
| PARSE-06 | Phase 1 | Complete |
| PARSE-07 | Phase 1 | Complete |
| PARSE-08 | Phase 1 | Complete |
| PARSE-09 | Phase 1 | Complete |
| META-01 | Phase 1 | Complete |
| META-02 | Phase 1 | Complete |
| CONF-03 | Phase 1 | Complete |
| INTG-01 | Phase 2 | Complete |
| INTG-02 | Phase 2 | Complete |
| INTG-05 | Phase 2 | Complete |
| CONF-01 | Phase 2 | Complete |
| CONF-02 | Phase 2 | Complete |
| INTG-03 | Phase 3 | Complete |
| INTG-04 | Phase 3 | Complete |
| INTG-06 | Phase 3 | Complete |

---

## Milestone Summary

**Shipped:** 20 of 20 v1 requirements
**Adjusted:** None — all requirements shipped as originally specified
**Dropped:** None

---
*Archived: 2026-02-21 as part of v1 milestone completion*
