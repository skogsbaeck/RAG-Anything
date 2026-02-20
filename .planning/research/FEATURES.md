# Spreadsheet Parser Feature Research

**Scope:** Features for direct xlsx/xls parsing into the RAGAnything `content_list` format
**Target:** LightRAG knowledge graph ingestion via the existing `TableModalProcessor`
**Library:** openpyxl (xlsx native); xlrd as fallback for legacy .xls

---

## Table Stakes (must have or parsing is broken)

These features are required for any spreadsheet output to be usable at all in the pipeline.

### 1. Multi-sheet workbook traversal
**Complexity:** Low
**Why required:** Workbooks with a single sheet are the exception, not the rule. Without iterating all sheets, entire sections of data are silently dropped — no error, just missing knowledge.
**Implementation note:** openpyxl exposes `workbook.sheetnames` and `workbook[name]` with zero additional effort. Each sheet becomes one `content_list` item of type `table`, carrying a sheet-scoped caption.

### 2. Cell value extraction with type coercion
**Complexity:** Low
**Why required:** openpyxl returns raw Python objects (`int`, `float`, `datetime`, `bool`, `str`, `None`). Without explicit coercion to string, downstream markdown serialization will either raise or produce `None` literals that corrupt the table.
**Implementation note:** A single `_coerce_cell(cell) -> str` helper handles all cases. Dates need `isoformat()`, booleans need lowercase, `None` becomes empty string. This is a named constant table, not branching logic.

### 3. Computed formula value extraction
**Complexity:** Low (with `data_only=True`) / High (without)
**Why required:** Cells containing formulas (e.g. `=SUM(A1:A10)`) have no semantic meaning to a RAG system — the computed value does. openpyxl reads cached computed values when `data_only=True` is passed to `load_workbook`. Without this, formula cells appear as formula strings.
**Caveat:** Cached values are only present if the workbook was last saved by Excel or LibreOffice with calculation enabled. Files saved programmatically (e.g. by openpyxl itself) will have `None` cached values. This is an inherent limitation of the format, not a parser bug. The LibreOffice PDF fallback exists for exactly this edge case.

### 4. Empty row and column stripping
**Complexity:** Low
**Why required:** Spreadsheets routinely contain trailing empty rows and columns from prior editing. Including them produces wide, sparse markdown tables with many empty cells that consume embedding tokens without adding information and degrade retrieval quality.
**Implementation note:** Determine the actual data extent using `worksheet.max_row` and `worksheet.max_column` combined with a scan for the last non-empty row and column. openpyxl's `min_row`, `max_row`, `min_column`, `max_column` are unreliable for this — they reflect the declared worksheet dimensions, not the actual data extent.

### 5. Markdown table serialisation
**Complexity:** Low
**Why required:** The `TableModalProcessor` expects `table_body` as a markdown table string. This is the interface contract. Without this, the produced `content_list` items cannot be processed by the existing pipeline at all.
**Implementation note:** Standard GFM markdown table format: pipe-delimited header row, separator row with dashes, then data rows. First row of each sheet (or first non-empty row) is treated as header. Column widths need not be padded for RAG purposes — the LLM does not care about visual alignment.

### 6. content_list item structure compliance
**Complexity:** Low
**Why required:** The `insert_content_list` method and `separate_content` utility in `utils.py` dispatch on the `type` field. A `table` item must carry `type`, `table_body`, `table_caption`, `table_footnote`, and `page_idx` (used as sheet index here) to be routed correctly to `TableModalProcessor`. Missing fields cause silent fallback to `GenericModalProcessor` or key errors.

---

## Differentiators (competitive advantage for RAG quality)

These features are not strictly required for the pipeline to run, but they substantially improve the quality of knowledge graph entities and retrieval accuracy.

### 1. Merged cell annotation
**Complexity:** Medium
**Why it matters:** Merged cells are the primary structural signal in spreadsheets. A cell spanning columns B through F in a header row means those columns share a category. Losing this collapses hierarchical structure into a flat table that the LLM cannot reconstruct from values alone.
**Implementation:** openpyxl exposes `worksheet.merged_cells.ranges`. For each merge range, the top-left cell holds the value; all others are `None`. On read, propagate the top-left value to all cells in the range, then annotate in the caption: `"Note: cells [range] are merged"`. Alternatively, emit a cell value like `"[merged: CategoryName]"` inline.
**Dependency:** Requires cell value extraction (Table Stakes #2).

### 2. Named range extraction
**Complexity:** Medium
**Why it matters:** Named ranges (e.g. `RevenueQ1`, `EmployeeRoster`) are the spreadsheet author's own semantic labelling of data regions. They are far more informative than positional references and map directly to LightRAG entity names. A named range becomes a separate `content_list` item with its name as the caption.
**Implementation:** `workbook.defined_names` provides the mapping. Names scoped to a single sheet (local names) must be disambiguated with the sheet name. Names that span multiple sheets (rare) should be skipped or flagged.
**Dependency:** Requires multi-sheet traversal (Table Stakes #1) and cell value extraction (Table Stakes #2).

### 3. Sheet-level metadata as caption
**Complexity:** Low
**Why it matters:** The `TableModalProcessor` passes `table_caption` to the LLM prompt for semantic naming. A caption of `"Sheet: Revenue_2024_Q3"` gives the LLM strong signal for entity naming and relationship extraction, compared to an empty caption. Sheet tab names are already semantic labels assigned by the author.
**Implementation:** Use `worksheet.title` as the base caption. Optionally include workbook filename stem for disambiguation when the same sheet name appears in multiple workbooks during batch ingestion.

### 4. Data type hint preservation in output
**Complexity:** Low
**Why it matters:** A column containing dates formatted as `2024-01-15` is semantically different from one containing arbitrary strings. If the LLM sees ISO dates, it can extract temporal relationships. If it sees ambiguous strings, it cannot. Preserving type information in the markdown output (e.g. by consistent ISO formatting of dates) enables the LLM to infer entity types correctly.
**Implementation:** The `_coerce_cell` helper already handles this by using `datetime.isoformat()` for date/datetime cells. The key is consistency — all dates must use the same format, regardless of the cell's display format in Excel.
**Dependency:** Requires type coercion (Table Stakes #2).

### 5. Large sheet chunking
**Complexity:** Medium
**Why it matters:** A sheet with 5,000 rows produces a single `content_list` item that exceeds LightRAG's token window for entity extraction. The item is either truncated silently or causes an API error. Chunking large sheets into overlapping row-groups ensures all data reaches the knowledge graph.
**Implementation:** Configurable `MAX_ROWS_PER_CHUNK` constant (suggested default: 100). Each chunk carries the header row prepended, a caption that includes the row range (e.g. `"Revenue_2024_Q3 — rows 101-200"`), and the same `page_idx` as the parent sheet. Overlap of 1-2 rows at chunk boundaries prevents context loss at split points.
**Dependency:** Requires markdown serialisation (Table Stakes #5) and sheet metadata (Differentiator #3).

### 6. Empty sheet skipping with logging
**Complexity:** Low
**Why it matters:** Many workbooks contain template or placeholder sheets with no data. Processing them produces empty `content_list` items that waste embedding calls. Skipping them with a log message preserves observability without polluting the pipeline.
**Implementation:** After empty row/column stripping (Table Stakes #4), if the effective data region is 0 rows, skip the sheet and emit a `logger.debug` message.
**Dependency:** Requires empty row/column stripping (Table Stakes #4).

### 7. Hidden sheet handling (configurable)
**Complexity:** Low
**Why it matters:** Hidden sheets in workbooks are intentionally not shown to end users. They often contain intermediate calculation data, lookup tables, or raw data that underpins the visible sheets. Whether to include them is a configuration decision, not a parsing decision.
**Implementation:** openpyxl exposes `worksheet.sheet_state` which is `"visible"`, `"hidden"`, or `"veryHidden"`. A `SKIP_HIDDEN_SHEETS` boolean config option (default: `True`) controls this. When `False`, hidden sheets are processed identically to visible ones, with their state noted in the caption.

---

## Anti-Features (things to deliberately NOT build)

### 1. Cell styling extraction (colors, fonts, borders)
**Reasoning:** Styling data has no semantic value in a text-based RAG knowledge graph. Color-coded status cells (red = overdue, green = complete) require visual interpretation that the current `TableModalProcessor` LLM prompt is not designed for. The cost of reading and representing styles — both in implementation complexity and in token consumption — is entirely wasted. The LibreOffice PDF fallback handles cases where visual layout is genuinely meaningful.

### 2. Chart and embedded image extraction from xlsx
**Reasoning:** Charts in xlsx are stored as XML drawing objects. Extracting them requires rendering, which is exactly what the LibreOffice PDF fallback path does. Attempting to reconstruct chart semantics from the underlying data series XML is fragile, under-specified, and produces inferior results compared to what `ImageModalProcessor` already does with rendered images. Do not duplicate this.

### 3. Formula string preservation alongside computed values
**Reasoning:** A formula string like `=VLOOKUP(B2,Config!$A:$B,2,FALSE)` is not interpretable by the LLM in a RAG context. The formula is an implementation detail of the spreadsheet, not knowledge. Storing both the formula string and the computed value doubles token consumption for zero retrieval benefit. Always use computed values only (`data_only=True`).

### 4. Pivot table reconstruction
**Reasoning:** Pivot tables in xlsx are stored as cache XML that references source data. Reconstructing their display representation from scratch requires reimplementing Excel's pivot engine. The output would be a redundant view of data already captured by parsing the source sheet. If a user needs the pivot view, the LibreOffice PDF fallback produces a rendered version. This is not a parser feature to build.

### 5. Cross-sheet formula dependency tracing
**Reasoning:** Tracing which cells reference which other cells across sheets (e.g. building a dependency graph) is a separate analytical capability, not a parsing feature. It has no defined output format in the `content_list` schema and no consumer in the current pipeline. If needed, it belongs in a separate analysis layer.

### 6. Automatic header detection heuristics
**Reasoning:** Assuming the first non-empty row is the header row is sufficient for the overwhelming majority of spreadsheets. Building heuristics that attempt to detect multi-row headers, hierarchical headers, or header rows that appear mid-sheet introduces complexity that fails unpredictably. When it works, it provides marginal improvement. When it fails, it silently produces corrupt markdown tables. The merged cell annotation (Differentiator #1) covers the legitimate multi-row header case structurally.

---

## Feature Dependencies

```
Table Stakes #1 (multi-sheet traversal)
    └── Table Stakes #5 (markdown serialisation)
            └── Table Stakes #6 (content_list compliance)
                    └── [pipeline integration complete]

Table Stakes #2 (type coercion)
    ├── Table Stakes #5 (markdown serialisation)
    ├── Differentiator #1 (merged cell annotation)
    ├── Differentiator #2 (named ranges)
    └── Differentiator #4 (type hint preservation)

Table Stakes #3 (formula values via data_only)
    └── Table Stakes #2 (type coercion)

Table Stakes #4 (empty row/col stripping)
    └── Differentiator #6 (empty sheet skipping)

Differentiator #1 (merged cell annotation)
    └── Table Stakes #2 (type coercion)

Differentiator #2 (named ranges)
    ├── Table Stakes #1 (multi-sheet traversal)
    └── Table Stakes #2 (type coercion)

Differentiator #3 (sheet metadata as caption)
    └── Table Stakes #1 (multi-sheet traversal)

Differentiator #5 (large sheet chunking)
    ├── Table Stakes #4 (empty row/col stripping)
    ├── Table Stakes #5 (markdown serialisation)
    └── Differentiator #3 (sheet metadata as caption)

Differentiator #6 (empty sheet skipping)
    └── Table Stakes #4 (empty row/col stripping)

Differentiator #7 (hidden sheet handling)
    └── Table Stakes #1 (multi-sheet traversal)
```

---

## Complexity Summary

| Feature | Category | Effort |
|---|---|---|
| Multi-sheet traversal | Table Stakes | ~1h |
| Cell value type coercion | Table Stakes | ~1h |
| Formula value extraction (`data_only`) | Table Stakes | ~30min |
| Empty row/column stripping | Table Stakes | ~1h |
| Markdown table serialisation | Table Stakes | ~1h |
| content_list item compliance | Table Stakes | ~30min |
| Merged cell annotation | Differentiator | ~2h |
| Named range extraction | Differentiator | ~2h |
| Sheet metadata as caption | Differentiator | ~30min |
| Data type hint preservation | Differentiator | ~30min |
| Large sheet chunking | Differentiator | ~3h |
| Empty sheet skipping | Differentiator | ~30min |
| Hidden sheet handling | Differentiator | ~30min |

**Minimum viable parser (Table Stakes only):** ~5h
**Full-featured parser (all Differentiators):** ~14h total
**Recommended first milestone:** Table Stakes + sheet metadata + empty sheet skipping + hidden sheet config (~8h)
