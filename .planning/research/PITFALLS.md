# Pitfalls: Direct Spreadsheet Parsing for RAG Ingestion

**Scope:** xlsx/xls → markdown → LightRAG knowledge graph
**Tools:** openpyxl (xlsx), xlrd (legacy xls)
**Date:** 2026-02-20

---

## P1 — Merged Cell Data Loss

**What goes wrong:**
openpyxl returns `None` for every cell in a merged region except the top-left anchor. If you iterate rows naively, merged cells appear as empty cells. Silently dropping them destroys table structure — a header spanning three columns becomes a single header with two empty siblings.

**Warning signs:**
- Markdown output shows `|  |  |` gaps adjacent to meaningful headers
- Row counts do not match the visual spreadsheet layout
- Data that "should" appear in a column is missing from the RAG output

**Prevention strategy:**
Use `ws.merged_cells.ranges` to enumerate all merge regions before rendering. For each merged range, annotate the anchor cell with `[merged NxM]` (rows × cols) and leave sibling cells explicitly empty rather than `None`. Never iterate cells without first resolving the merge map.

```python
# Build merge map before iterating
merge_map: dict[tuple[int, int], str] = {}
for merged_range in ws.merged_cells.ranges:
    r_min, c_min = merged_range.min_row, merged_range.min_col
    rows = merged_range.max_row - r_min + 1
    cols = merged_range.max_col - c_min + 1
    merge_map[(r_min, c_min)] = f"[merged {rows}x{cols}]"
    for r in range(r_min, merged_range.max_row + 1):
        for c in range(c_min, merged_range.max_col + 1):
            if (r, c) != (r_min, c_min):
                merge_map[(r, c)] = ""  # sibling: render as empty
```

**Phase:** Implementation (spreadsheet module core logic)

---

## P2 — Formula Cells Returning None or Literal Formula Text

**What goes wrong:**
openpyxl has two load modes. In the default mode (`data_only=False`), formula cells return the formula string (`=SUM(A1:A10)`). In `data_only=True` mode, it returns the cached value from the last time Excel saved the file — but only if Excel actually computed and stored the cache. If the file was saved by LibreOffice, Google Sheets, or a script that never computed formulas, cached values are `None`. The RAG index then ingests `None` instead of the actual number.

**Warning signs:**
- Cells that look like they should have numbers instead contain `=FORMULA(...)` text in the markdown
- Cells that are clearly numeric in the spreadsheet appear as empty in the output
- Files exported from non-Excel tools (Google Sheets export, LibreOffice save) produce more `None` values than files saved by Microsoft Excel

**Prevention strategy:**
Always load with `data_only=True`. Treat `None` as a distinct case from an empty string — log a warning when a formula cell has no cached value, and annotate it as `[formula: no cached value]` rather than silently dropping it. Document clearly that files must have been computed by Excel at least once before export for full fidelity.

For the fallback case: if a sheet has many formula cells with no cached values (>10% of non-empty cells), trigger the LibreOffice PDF fallback automatically, as PDF rendering forces formula computation.

**Phase:** Implementation (openpyxl load configuration) + Fallback trigger logic

---

## P3 — Ragged Tables Breaking Markdown Alignment

**What goes wrong:**
Spreadsheets frequently have rows of different effective lengths — trailing empty cells are just absent from the file format. A "table" might have 10 columns in row 1, 8 in row 2, and 12 in row 3. Standard markdown table rendering requires all rows to have the same number of columns. A naive renderer either crashes, silently truncates, or produces malformed markdown that breaks the chunker.

Worse: headers and data rows may have different column counts if a spreadsheet uses the top rows for a title block before the actual data starts.

**Warning signs:**
- Markdown tables with misaligned pipes (`|`) in the output
- LightRAG entity extraction producing garbled table content
- Rows with more cells than the header produces `IndexError` or silent truncation

**Prevention strategy:**
Before rendering, compute `max_col = max(len(row) for row in all_rows)` across the entire sheet. Pad every row to `max_col` with empty cells. Apply the same normalization to the separator row in markdown. Always write the separator row as `| --- |` repeated for each column.

Also: detect if the first N rows are a "title block" (merged cells spanning the full width, no column headers) and emit them as plain text before the markdown table rather than trying to force them into tabular format.

**Phase:** Implementation (markdown rendering)

---

## P4 — Chunker Fragmentation of Wide Tables

**What goes wrong:**
LightRAG's chunker splits text by token count, not by table boundaries. A large table (50 rows × 10 columns) becomes 2,000+ tokens of markdown. The chunker splits it mid-table, and the embedding is of a fragment — headers appear in one chunk, data rows in another, the LLM never sees the relationship between header and data during retrieval.

This is the most common RAG quality failure for tabular data: the embedder/retriever returns half a table, the LLM answers with structural confusion.

**Warning signs:**
- Queries about specific column values return answers mixing up different columns
- Retrieved context shows `| --- | --- |` in the middle of content (chopped separator row)
- Recall is lower than expected for data questions, despite data being in the index

**Prevention strategy:**
Each sheet (or logical sub-table within a sheet) should be its own `content_list` item. Do not concatenate multiple sheets into one text block. Each item is processed by `TableModalProcessor` independently — that processor has LLM-based analysis that can reason about complete table structure.

For large single sheets: split at natural data boundaries (blank rows, section headers detected by merged-cell spanning rows) rather than by token count. Emit multiple `content_list` items per sheet if the sheet is logically partitioned.

This maps directly to the existing `table_body` field in the `content_list` contract:
```python
{
    "type": "table",
    "table_body": "<markdown table for this sheet/section>",
    "table_caption": ["Sheet: SheetName"],
    "table_footnote": [],
    "page_idx": sheet_index,
}
```

**Phase:** Design (before implementation — affects the content_list schema per sheet)

---

## P5 — Multi-Sheet Workbooks Losing Cross-Sheet Context

**What goes wrong:**
Workbooks routinely use cross-sheet references: a "Summary" sheet references "Q1 Data", "Q2 Data", "Q3 Data". When each sheet is parsed independently, the RAG index has no knowledge graph edge connecting them. A query about "the summary figures" returns the Summary sheet chunk; a follow-up about "where the Q1 number comes from" returns nothing useful because the connection is implicit in the spreadsheet, not in the content.

**Warning signs:**
- Workbooks with a clear "Summary" or "Dashboard" sheet plus underlying data sheets
- Users report that follow-up questions about spreadsheet provenance return empty results
- The summary sheet has cells like `=Q1!B5` that, when formula-resolved, show only numbers with no attribution

**Prevention strategy:**
Emit a sheet-level preamble for each sheet:
```
Sheet: "Summary" (sheet 1 of 4)
Workbook: budget_2025.xlsx
Other sheets in this workbook: Q1 Data, Q2 Data, Q3 Data, Assumptions
```
Include this preamble in the `table_caption` or as a dedicated text block immediately before each table item in the `content_list`. The LLM context extraction in `ContextExtractor` will then have cross-sheet names available when processing each sheet's table.

**Phase:** Implementation (sheet metadata generation)

---

## P6 — Empty Sheets and Invisible Data Causing Failures

**What goes wrong:**
Workbooks commonly contain: (1) entirely empty sheets used as spacers, (2) sheets with only a chart and no cell data, (3) sheets with data starting at row 100 column 20 because a user manually entered data far from the origin, (4) sheets hidden by the workbook author. Processing any of these naively produces either empty markdown tables (which break the `ValueError: Parsing failed: No content was extracted` check in `processor.py` line 441) or massive tables of empty cells.

**Warning signs:**
- `ws.max_row` returns a very large number (>1000) for a sheet that looks empty
- The markdown output is almost entirely `| | | |` empty-cell rows
- The entire workbook ingestion fails because one empty sheet crashes the parser

**Prevention strategy:**
Before rendering any sheet:
1. Check `ws.max_row` and `ws.max_column` — if both are 1 or `ws.calculate_dimension()` returns `"A1:A1"`, skip the sheet.
2. Scan for the actual data bounding box using openpyxl's `min_row`, `min_col`, `max_row`, `max_column` properties on the used range.
3. Skip hidden sheets (`ws.sheet_state == 'hidden'` or `ws.sheet_state == 'veryHidden'`) unless an explicit option is set to include them.
4. If a sheet produces zero non-empty cells, skip it silently and log at DEBUG level.
5. Never raise an exception on an empty sheet — emit a warning and continue to the next sheet.

**Phase:** Implementation (sheet preprocessing / guard clauses)

---

## P7 — Data Type Coercion Destroying Meaning

**What goes wrong:**
openpyxl returns typed Python values — `datetime.datetime`, `float`, `bool`, `int`. Naively calling `str()` on them produces:
- `2025-01-15 00:00:00` for a date cell that should read `2025-01-15`
- `True`/`False` for boolean cells that should read `Yes`/`No` (user-facing labels)
- `100000.0` for an integer that should read `100,000`
- `3.141592653589793` for a cell that the user formatted as `3.14`

The LLM ingests these raw Python repr strings and can fail to match them to natural language queries ("find all records from January 2025" doesn't match `2025-01-15 00:00:00`).

**Warning signs:**
- Date cells appear with time component `00:00:00` in the markdown
- Float cells show excessive decimal places
- Boolean cells show Python `True`/`False` instead of meaningful text
- Queries using natural date formats return no matches

**Prevention strategy:**
Implement a typed cell formatter:
```python
def format_cell_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")  # Drop time component for date-only cells
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.4g}"  # Significant figures, not fixed decimal
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)
```

Also: read the cell's `number_format` attribute via openpyxl to understand the intended display format, then use it to guide rendering rather than raw Python type defaults.

**Phase:** Implementation (cell value rendering)

---

## P8 — Markdown Table Special Characters Breaking Rendering

**What goes wrong:**
Spreadsheet cell content routinely contains pipe characters (`|`), newlines, and backticks — all of which are meaningful in markdown tables. A cell containing `Revenue | Cost` becomes a malformed markdown row with an extra column. A cell with an embedded newline splits a single cell across two markdown rows. The resulting markdown breaks the LightRAG parser and produces corrupt knowledge graph nodes.

**Warning signs:**
- Markdown output has rows with inconsistent column counts despite padding
- Content that was in one cell appears as a new row in the markdown
- Markdown rendered in preview shows broken table formatting

**Prevention strategy:**
Before inserting any cell value into a markdown table:
1. Replace `|` with `\|` (escaped pipe)
2. Replace newlines (`\n`, `\r\n`, `\r`) with a space or ` <br> ` depending on the downstream renderer
3. Replace backtick sequences that could be mistaken for code fences
4. Strip leading and trailing whitespace from cell values

Apply these transformations in a single `sanitize_cell()` function called consistently from the rendering loop — never inline.

**Phase:** Implementation (cell value rendering / markdown generation)

---

## P9 — xls Legacy Format Compatibility Gaps

**What goes wrong:**
`xlrd` (required for `.xls` files) behaves differently from openpyxl in several ways that are not obvious:
- xlrd returns cell values already typed but with different type codes (0=empty, 1=text, 2=number, 3=date, 4=boolean, 5=error)
- Date handling requires `xlrd.xldate_as_datetime(cell.value, workbook.datemode)` — failing to account for `datemode` produces dates off by about 4 years (the 1900 vs 1904 date system difference)
- xlrd 2.x+ removed support for `.xls` files with macros and some older format variants — it raises `xlrd.biffh.XLRDError` rather than returning partial data

**Warning signs:**
- Dates in `.xls` files appear 4 years off from expected values
- Certain `.xls` files from legacy systems (pre-2000) fail entirely
- xlrd raises `XLRDError` on files that can be opened by Excel

**Prevention strategy:**
Use a unified cell-reading abstraction that handles both openpyxl and xlrd backends. For xlrd date cells, always pass `workbook.datemode` to `xlrd.xldate_as_datetime()`. Wrap xlrd loading in a try/except for `XLRDError` and fall back to the LibreOffice PDF path with a warning rather than crashing. Test explicitly against files from different Excel versions (Excel 97, 2003, 2007-era).

**Phase:** Implementation (xlrd adapter) + Testing (legacy format fixtures)

---

## P10 — Content List Contract Mismatch with TableModalProcessor

**What goes wrong:**
The existing `TableModalProcessor` in `modalprocessors.py` expects a specific dict structure. If the spreadsheet parser emits items with slightly different field names or types, the modal processor silently gets empty values or crashes at `processor.py:979` where `table_body` is accessed:
```python
table_body = original_item.get("table_body", "")
```
A common mistake: emitting `"body"` instead of `"table_body"`, or emitting a list instead of a string for `table_caption`. The error manifests not as a crash but as a silent empty-table entity in the knowledge graph — the RAG ingestion "succeeds" but the content is invisible to queries.

**Warning signs:**
- No errors during ingestion, but queries about spreadsheet content return empty results
- Knowledge graph contains entities with empty or template-only descriptions
- `table_body` field in the content item is a list or None instead of a markdown string

**Prevention strategy:**
The spreadsheet parser must emit items matching this exact contract (from `processor.py` lines 978-990 and `prompt.py`):
```python
{
    "type": "table",
    "table_body": str,            # markdown table string — REQUIRED
    "table_caption": list[str],   # ["Sheet: SheetName"] — list, not string
    "table_footnote": list[str],  # [] — list, not string
    "page_idx": int,              # sheet index (0-based)
}
```
Write a contract validation function and call it in tests — assert field types, not just field names. Reference `processor.py` lines 976-990 and `modalprocessors.py` `generate_description_only()` signature as the ground truth.

**Phase:** Design (contract validation) — before any implementation

---

## P11 — Sheet Name Collisions in Multi-Document Batches

**What goes wrong:**
When multiple workbooks are processed in a batch, each can have a sheet named "Summary", "Data", or "Sheet1". The `TableModalProcessor` generates entity names based on sheet names. Two entities named "Summary (table)" from different files get merged in the LightRAG knowledge graph — their descriptions and relations are combined, producing a corrupted entity that mixes data from different spreadsheets.

**Warning signs:**
- Queries about "the summary" return blended data from multiple spreadsheets
- Entity descriptions mention column names from multiple different domains (e.g., "Revenue" and "Patient Count" in the same entity)
- Running the same batch twice produces different knowledge graph results

**Prevention strategy:**
Prefix every `table_caption` with the workbook filename:
```python
table_caption = [f"{workbook_filename} — {sheet_name}"]
```
This becomes part of the entity name generated by `TableModalProcessor`, ensuring uniqueness across workbooks. Never use bare sheet names as captions. Test by ingesting two different workbooks both containing a "Summary" sheet and verifying the resulting entities are distinct.

**Phase:** Implementation (caption/metadata generation)

---

## P12 — Silent Fallback Masking Parse Quality Issues

**What goes wrong:**
The project plan calls for "try direct parse first, fall back to LibreOffice PDF path on failure." If the fallback is triggered silently, production ingestion may silently use PDF conversion for all spreadsheets (because some edge case in the direct parser always raises an exception). The direct parser appears to "work" in CI, but in production it never actually runs — LibreOffice runs instead. The whole point of the feature is defeated, and no one notices.

**Warning signs:**
- Processing logs always show LibreOffice conversion for `.xlsx` files
- Files that trigger fallback never appear in warnings
- No metric differentiating "direct parse" vs "fallback" processing

**Prevention strategy:**
Make fallback logging explicit and unmissable:
```python
logger.warning(
    "Direct spreadsheet parsing failed for %s, falling back to LibreOffice PDF: %s",
    file_path.name,
    exc
)
```
Add a counter metric or summary log at batch completion: `"N files used direct parse, M files used LibreOffice fallback"`. In tests, assert that a valid `.xlsx` fixture uses the direct parser (mock LibreOffice and assert it was NOT called). The fallback must be auditable, not invisible.

**Phase:** Implementation (error handling + logging) + Testing

---

*Research date: 2026-02-20*
