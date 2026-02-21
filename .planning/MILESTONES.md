# Project Milestones: RAG-Anything — Direct Spreadsheet Parsing

## v1 Direct Spreadsheet Parsing (Shipped: 2026-02-21)

**Delivered:** Direct xlsx/xls parsing path that preserves tabular structure as GFM markdown tables, bypassing lossy LibreOffice-to-PDF conversion for RAG knowledge graph ingestion.

**Phases completed:** 1-3 (7 plans total)

**Key accomplishments:**
- Standalone SpreadsheetParser module with xlsx (openpyxl) and xls (xlrd) parsing producing GFM markdown tables
- Merged cell annotation (`[merged NxM]`), hidden/empty sheet filtering, and configurable row chunking
- MineruParser integration with guarded imports, ImportError hard-error, and LibreOffice fallback on parse failure
- ProcessorMixin routing with `enable_direct_spreadsheet_parsing` config flag and zero-content guard exemption
- Formula-None threshold (10% empty cells) triggers automatic LibreOffice fallback for uncached-formula workbooks
- 73-test suite: helpers (28), parser (19), integration (7), routing (8), E2E (11)

**Stats:**
- 52 files created/modified
- 1,892 lines of Python (production + tests)
- 3 phases, 7 plans
- 2 days (2026-02-20 → 2026-02-21)

**Git range:** `feat(01-01)` → `docs(03)`

**What's next:** TBD — next milestone to be defined

---
