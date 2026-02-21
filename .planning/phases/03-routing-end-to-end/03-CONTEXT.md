# Phase 3: Routing + End-to-End - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Activate the direct spreadsheet parser in the live ProcessorMixin pipeline. Route xlsx/xls through SpreadsheetParser, verify the content_list contract with TableModalProcessor, confirm fallback to LibreOffice works gracefully, and run a real workbook through to the LightRAG knowledge graph. Parser core (Phase 1) and integration wiring (Phase 2) are already complete.

</domain>

<decisions>
## Implementation Decisions

### Content contract
- Minimal metadata only — table_body, table_caption, type, page_idx. Caption already carries sheet name context; no extra fields needed
- Field reshaping approach and content type naming: Claude's discretion based on existing codebase patterns
- Content length guard vs Phase 1 chunking: Claude's discretion based on LightRAG constraints

### Fallback behavior
- Fallback to LibreOffice is always available — no strict mode flag
- Tests must be designed so direct parsing is exercised (not accidentally falling through to fallback)
- Formula-None threshold (>10% triggers fallback) must be validated in Phase 3 with a test fixture using simulated None values
- Double-failure handling (direct + LibreOffice both fail) and degraded-result marking: Claude's discretion based on existing pipeline error patterns

### E2E test strategy
- Two test layers: mock LightRAG tests for CI (fast), plus one real integration test marked slow/optional
- Real integration test should query LightRAG for known cell values to prove data reaches the knowledge graph
- All fixtures created programmatically with openpyxl — no committed binary files in git
- Formula-None threshold tested by injecting None values (simulating uncached formulas), not real Excel formulas

### Multi-sheet handling
- All non-empty, non-hidden sheets are processed — no max_sheets limit
- Sheet ordering in content_list preserves workbook tab order (author's intended arrangement)
- page_idx assignment and chunk caption formatting: Claude's discretion based on existing multi-part content patterns

### Claude's Discretion
- Content item field reshaping (in routing vs in parser)
- Content type value ("table" vs "spreadsheet_table")
- Whether Phase 1 chunking is sufficient or needs a content length guard
- Double-failure error handling approach
- Whether fallback results get marked as degraded
- page_idx assignment strategy for multi-sheet workbooks
- Chunk caption formatting (row ranges vs repeated sheet name)

</decisions>

<specifics>
## Specific Ideas

- "Fallback always available, create tests in a way that parsing happens direct" — tests should assert the direct path is taken, not just that results appear
- Query verification for real integration test — insert workbook, query back for known values

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-routing-end-to-end*
*Context gathered: 2026-02-21*
