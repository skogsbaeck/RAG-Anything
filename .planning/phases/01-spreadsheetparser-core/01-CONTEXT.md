# Phase 1: SpreadsheetParser Core - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Standalone SpreadsheetParser module that reads xlsx/xls workbooks and produces content_list items containing GFM markdown tables. No integration with MineruParser, ProcessorMixin, or config system — those are Phase 2 and 3. This phase delivers a self-contained, testable module with the `spreadsheet` pyproject.toml extras group.

</domain>

<decisions>
## Implementation Decisions

### Merged Cell Rendering
- Annotation goes **inline on the anchor cell** as a suffix: `Revenue [merged 3×1]`
- Sibling cells (non-anchor cells in a merged region) contain **empty strings**
- Empty merged regions and row span annotation format are Claude's discretion

### Large Sheet Chunking
- Claude's discretion on: default max rows threshold, whether to repeat first row in each chunk, chunk overlap strategy, and chunk caption format
- Optimize for RAG retrieval quality — chunks should be self-contained enough for meaningful embedding

### Data Formatting
- **Dates/datetimes**: ISO 8601 format (`2024-03-15` or `2024-03-15T14:30:00`)
- **Numbers**: Raw value as openpyxl returns it (preserve `.0` on floats)
- **Booleans**: Claude's discretion on capitalization
- **None/empty cells**: Empty string (blank cell in markdown table)
- **Markdown special characters**: Pipes and newlines must be sanitized (research flagged this as critical)

### Sheet-Level Behavior
- **Empty sheets**: Skip only if zero non-empty cells (no threshold heuristic)
- **Data offset**: Always start at A1, even if leading rows/columns are empty — preserves positional context
- **Sheet ordering**: Workbook tab order preserved in content_list output
- **Hidden sheets**: Always skip — if the author hid it, it's not primary content

### Header Detection
- **No header inference** — all rows rendered as data rows in the markdown table
- The LLM / TableModalProcessor interprets semantic structure from context

### Claude's Discretion
- Large sheet chunking strategy (threshold, overlap, repetition, caption format)
- Merged cell row span annotation format (NxM vs simplified)
- Empty merged region handling (annotate or skip)
- Boolean rendering format
- Markdown table generation approach (internal implementation, no external lib per research)

</decisions>

<specifics>
## Specific Ideas

- Follow the `audio.py` pattern: isolated module, guarded imports, clean public API
- Research identified that openpyxl's `read_only=True` mode doesn't expose merged cell metadata — must use standard mode
- Research flagged: openpyxl's `max_row`/`max_column` are unreliable for empty row detection — scan actual data
- content_list items must have: `type: "table"`, `table_body: str`, `table_caption: list[str]`, `page_idx: int`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-spreadsheetparser-core*
*Context gathered: 2026-02-20*
