# Requirements: Direct Spreadsheet Parsing

**Defined:** 2026-02-20
**Core Value:** Preserve structural integrity of tabular spreadsheet data for RAG knowledge graph ingestion

## v1 Requirements

### Core Parsing

- [ ] **PARSE-01**: Parser reads all sheets in an xlsx/xls workbook independently
- [ ] **PARSE-02**: Cell values coerced to clean strings (datetime, float, bool, None handled)
- [ ] **PARSE-03**: Formula cells resolved to cached computed values via `data_only=True`
- [ ] **PARSE-04**: Empty rows/columns stripped from each sheet before rendering
- [ ] **PARSE-05**: Merged cells annotated with `[merged NxM]` on anchor cell, siblings marked empty
- [ ] **PARSE-06**: Each sheet rendered as a GFM markdown table with all rows as data (no header inference — LLM interprets structure)
- [ ] **PARSE-07**: Empty and hidden sheets skipped automatically
- [ ] **PARSE-08**: Markdown special characters (pipes, newlines) sanitized in cell values
- [ ] **PARSE-09**: Large sheets chunked at configurable row limit to prevent token explosion

### Integration

- [ ] **INTG-01**: `SpreadsheetParser` module created following `audio.py` pattern
- [ ] **INTG-02**: `parse_spreadsheet` method added to `MineruParser` with guarded import
- [ ] **INTG-03**: ProcessorMixin routes `.xls`/`.xlsx` to direct parser before Office branch
- [ ] **INTG-04**: Fallback to LibreOffice PDF path on direct parse failure with explicit logging
- [ ] **INTG-05**: `xlrd` adapter for legacy `.xls` files with unified interface
- [ ] **INTG-06**: content_list items match existing contract (type, table_body, table_caption, page_idx)

### Configuration

- [ ] **CONF-01**: `enable_direct_spreadsheet_parsing` config flag (default: True)
- [ ] **CONF-02**: `spreadsheet_max_rows_per_sheet` config option with env var support
- [ ] **CONF-03**: `spreadsheet` optional dependency group in pyproject.toml

### Metadata

- [ ] **META-01**: Table caption includes workbook filename and sheet name
- [ ] **META-02**: Sheet index mapped to `page_idx` for multi-sheet context

## v2 Requirements

### Extended Formats

- **CSV-01**: CSV/TSV file direct parsing
- **NAMED-01**: Named range extraction as separate content items
- **CHART-01**: Chart/graph extraction from spreadsheets

## Out of Scope

| Feature | Reason |
|---------|--------|
| Google Sheets API | Only handling exported files, not live connections |
| Cell styling/colors | Not useful for text-based RAG content |
| Formula string preservation | Computed values sufficient, formulas confuse LLM |
| Pivot table reconstruction | High complexity, low RAG value |
| Cross-sheet dependency tracing | High complexity, deferred |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PARSE-01 | Phase 1 | Pending |
| PARSE-02 | Phase 1 | Pending |
| PARSE-03 | Phase 1 | Pending |
| PARSE-04 | Phase 1 | Pending |
| PARSE-05 | Phase 1 | Pending |
| PARSE-06 | Phase 1 | Pending |
| PARSE-07 | Phase 1 | Pending |
| PARSE-08 | Phase 1 | Pending |
| PARSE-09 | Phase 1 | Pending |
| META-01 | Phase 1 | Pending |
| META-02 | Phase 1 | Pending |
| CONF-03 | Phase 1 | Pending |
| INTG-01 | Phase 2 | Pending |
| INTG-02 | Phase 2 | Pending |
| INTG-05 | Phase 2 | Pending |
| CONF-01 | Phase 2 | Pending |
| CONF-02 | Phase 2 | Pending |
| INTG-03 | Phase 3 | Pending |
| INTG-04 | Phase 3 | Pending |
| INTG-06 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-02-20*
*Last updated: 2026-02-20 after roadmap creation*
