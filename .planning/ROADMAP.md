# Roadmap: Direct Spreadsheet Parsing for RAG-Anything

## Overview

This milestone adds a direct xlsx/xls parsing path to RAG-Anything, replacing the lossy LibreOffice-to-PDF conversion with structured markdown table output. Three phases build from the isolated core parser module outward to full pipeline integration, following the same pattern established by the audio transcription feature.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: SpreadsheetParser Core** - Isolated parser module with full xlsx/xls cell handling and markdown output
- [ ] **Phase 2: Parser + Config Integration** - Wire SpreadsheetParser into MineruParser with config flags and xlrd adapter
- [ ] **Phase 3: Routing + End-to-End** - Activate feature in ProcessorMixin routing and verify full pipeline

## Phase Details

### Phase 1: SpreadsheetParser Core
**Goal**: A standalone, fully-tested SpreadsheetParser module produces correct markdown tables from any xlsx/xls workbook
**Depends on**: Nothing (first phase)
**Requirements**: PARSE-01, PARSE-02, PARSE-03, PARSE-04, PARSE-05, PARSE-06, PARSE-07, PARSE-08, PARSE-09, META-01, META-02, CONF-03
**Success Criteria** (what must be TRUE):
  1. Calling `SpreadsheetParser.parse("workbook.xlsx")` returns one content_list item per non-empty, non-hidden sheet
  2. Each returned item contains a valid GFM markdown table with pipe-escaped cell values, merged cell annotations, and a caption prefixed with the workbook filename and sheet name
  3. Formula cells show their computed values; datetime, float, bool, and None cells render as clean strings with no Python repr artifacts
  4. Sheets exceeding `spreadsheet_max_rows_per_sheet` are chunked into multiple items rather than producing a single oversized table
  5. The `spreadsheet` optional dependency group in pyproject.toml installs openpyxl and xlrd with no other required changes
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — TDD: helper functions (cell formatting, sanitization, merge map, empty stripping)
- [ ] 01-02-PLAN.md — TDD: SpreadsheetParser class (sheet parsing, markdown rendering, chunking)
- [ ] 01-03-PLAN.md — Package wiring (pyproject.toml extras, __init__.py exports)

### Phase 2: Parser + Config Integration
**Goal**: MineruParser gains a `parse_spreadsheet()` method that calls SpreadsheetParser, falls back to LibreOffice on failure, and reads configuration flags
**Depends on**: Phase 1
**Requirements**: INTG-01, INTG-02, INTG-05, CONF-01, CONF-02
**Success Criteria** (what must be TRUE):
  1. Calling `MineruParser.parse_spreadsheet("workbook.xlsx")` returns a content_list without requiring openpyxl to be importable at module load time (guarded import)
  2. Passing an `.xls` file routes through the xlrd adapter and returns the same content_list structure as an xlsx file
  3. When SpreadsheetParser raises an exception, `parse_spreadsheet()` logs a WARNING with the filename and exception, then returns the LibreOffice PDF path result
  4. `enable_direct_spreadsheet_parsing=False` in config causes `parse_spreadsheet()` to skip direct parsing entirely and go straight to LibreOffice
**Plans**: TBD

Plans:
- [ ] 02-01: TBD

### Phase 3: Routing + End-to-End
**Goal**: ProcessorMixin routes xlsx/xls through the direct parser, the content_list contract is verified, and a real workbook flows through to the LightRAG knowledge graph
**Depends on**: Phase 2
**Requirements**: INTG-03, INTG-04, INTG-06
**Success Criteria** (what must be TRUE):
  1. Calling `process_document_complete("workbook.xlsx")` on a RAGAnything instance invokes the direct parser (not LibreOffice) and does not raise an error
  2. A workbook with multiple sheets produces multiple table content items, each correctly received by TableModalProcessor (verified by asserting `type`, `table_body`, `table_caption`, and `page_idx` field types match the contract)
  3. When direct parsing fails mid-pipeline, the fallback to LibreOffice is logged at WARNING level and processing completes without a crash
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. SpreadsheetParser Core | 0/3 | Planned | - |
| 2. Parser + Config Integration | 0/? | Not started | - |
| 3. Routing + End-to-End | 0/? | Not started | - |
