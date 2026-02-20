# Phase 1 Research: SpreadsheetParser Core

## 1. Exact content_list Contract

### Source files examined
- `raganything/modalprocessors.py` — `TableModalProcessor`
- `raganything/processor.py` — `insert_content_list` docstring, `_generate_content_based_doc_id`, `_apply_chunk_template`
- `raganything/utils.py` — `separate_content`

### Table item dict structure (exact fields consumed)

```python
{
    "type": "table",                    # REQUIRED — routes to TableModalProcessor
    "table_body": str,                  # REQUIRED — GFM markdown table string
    "table_caption": list[str],         # optional, defaults to []
    "table_footnote": list[str],        # optional, defaults to []
    "img_path": str | None,             # optional, image of table if available
    "page_idx": int,                    # REQUIRED for context extraction (0-based)
}
```

### How routing works (`separate_content` in utils.py, lines 28-38)

```python
if content_type == "text":
    # collected into text_parts, joined with "\n\n"
else:
    # appended to multimodal_items — this includes "table"
```

Everything with `type != "text"` goes into `multimodal_items`. Tables are never merged into the text stream; they always go through `TableModalProcessor`.

### How `TableModalProcessor` consumes the item (modalprocessors.py, lines 1065-1068)

```python
table_img_path = content_data.get("img_path")
table_caption  = content_data.get("table_caption", [])
table_body     = content_data.get("table_body", "")
table_footnote = content_data.get("table_footnote", [])
```

`table_body` is the GFM markdown string. It is passed directly into the LLM prompt and stored as the chunk content (via `PROMPTS["table_chunk"]`).

### `_generate_content_based_doc_id` (processor.py, lines 116-118)

```python
elif item.get("type") == "table" and item.get("table_body"):
    content_hash_data.append(f"table:{item['table_body']}")
```

`table_body` is used for document identity hashing — must be deterministic.

### Minimum valid item for a sheet chunk

```python
{
    "type": "table",
    "table_body": "| Col A | Col B |\n|---|---|\n| val | val |",
    "table_caption": ["Sheet: Sheet1 — rows 1-50"],
    "page_idx": 0,
}
```

---

## 2. openpyxl Merged Cell API

### Key findings (verified via live testing)

**`ws.merged_cells`** returns a `MultiCellRange` object. Iterate `.ranges` to get individual `MergedCellRange` objects.

```python
for merged_range in ws.merged_cells.ranges:
    merged_range.min_row   # int, 1-based
    merged_range.max_row   # int, 1-based
    merged_range.min_col   # int, 1-based
    merged_range.max_col   # int, 1-based
    merged_range.coord     # str, e.g. "A1:C3"
    merged_range.size      # dict: {'columns': int, 'rows': int}
```

**Sibling cell access:** Reading `ws["B1"]` where B1 is part of a merge (not the anchor) returns `value=None`. The value lives exclusively on the anchor cell.

**Standard mode required:** `read_only=True` does not expose `merged_cells`. Must use standard (default) mode.

### Building the merge map (O(total merged cells), done once per sheet)

```python
def build_merge_map(ws) -> dict[tuple[int, int], dict]:
    merge_map = {}
    for merged_range in ws.merged_cells.ranges:
        anchor = (merged_range.min_row, merged_range.min_col)
        span_rows = merged_range.max_row - merged_range.min_row + 1
        span_cols = merged_range.max_col - merged_range.min_col + 1
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for col in range(merged_range.min_col, merged_range.max_col + 1):
                merge_map[(row, col)] = {
                    "is_anchor": (row, col) == anchor,
                    "span_rows": span_rows,
                    "span_cols": span_cols,
                }
    return merge_map
```

### Annotation format (locked by CONTEXT.md)

- **Anchor cell** — suffix the cell text with ` [merged {span_rows}×{span_cols}]`
  - Example: `Revenue [merged 3×1]` for a horizontal 3-column merge
  - Only add suffix if `span_rows > 1 or span_cols > 1` (skip 1×1 degenerate merges)
  - When `span_rows == 1`: suffix shows column span only implicitly via `3×1`
- **Sibling cells** — render as empty string `""`

### Row-span annotation (Claude's Discretion area)

For row spans (vertical merges), the anchor appears only in the first row. Downstream rows show `""`. This is sufficient because the annotation `[merged 3×1]` on the anchor communicates the vertical extent. No additional row-level annotation is needed.

### Empty merged region (Claude's Discretion area)

A merged region where the anchor cell value is `None` (intentionally empty): render all cells in the region as empty strings. No annotation is added for empty anchors.

---

## 3. Cell Value Handling

### Types returned by openpyxl (verified)

| Python type | openpyxl source | Required rendering |
|---|---|---|
| `int` | integer cell | `str(value)` — raw value |
| `float` | decimal cell | `str(value)` — raw value |
| `bool` | boolean cell | `"TRUE"` / `"FALSE"` (see note) |
| `datetime.date` | date cell | `value.isoformat()` → `"2024-01-15"` |
| `datetime.datetime` | datetime cell | `value.isoformat()` → `"2024-01-15T10:30:45"` |
| `str` | text cell | as-is (after markdown sanitization) |
| `None` | empty cell | `""` |

**Boolean rendering (Claude's Discretion):** Use `"TRUE"` / `"FALSE"` (uppercase). This matches Excel's own display convention and is unambiguous in markdown tables. Lowercase `true`/`false` risks confusion with string values.

**Formula cells:** When using `data_only=True`, formula cells return the last cached result (or `None` if never evaluated). Use `data_only=True` when loading workbooks. If the value is `None` due to formula, treat as empty string.

**Important:** Load workbooks with `data_only=True` to get cached formula values rather than formula strings. Example: `openpyxl.load_workbook(path, data_only=True)`.

### Markdown sanitization (locked)

All string cell values must be sanitized before insertion into a markdown table:

```python
def sanitize_cell(value: str) -> str:
    value = value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    value = value.replace("|", r"\|")
    return value.strip()
```

Order matters: replace newlines before pipe characters.

---

## 4. audio.py Pattern — Module Architecture

### File: `raganything/audio.py`

The audio module is the established pattern for new standalone parser modules. Key characteristics:

**Guarded imports:** Dependencies are imported inside methods, not at module level.

```python
def _load_model(self):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
        raise
```

This means the module can be imported safely even if optional dependencies are absent. ImportError is only raised at call time.

**Config dataclass at module level:**

```python
@dataclass
class AudioConfig:
    whisper_model: str = "base"
    device: str = "cpu"
    language: str = "de"
    compute_type: str = "int8"
```

A frozen `@dataclass` with all defaults. Callers pass `None` and the class provides defaults.

**Result dataclasses:**

```python
@dataclass
class AudioTranscription:
    text: str
    duration_seconds: float
    language: str
    word_count: int
    confidence: Optional[float] = None
```

Rich return types that callers can inspect.

**Processor class:** `AudioProcessor` initializes with config, lazily loads heavy resources in `_load_model()`. Public methods: `transcribe()`, `transcribe_batch()`, `extract_metadata()`, `export_to_text()`.

**Module-level utility functions:** `get_supported_formats()`, `is_supported_format()`, `estimate_processing_time()`. These are importable without instantiation.

**Error handling pattern:** Guard clauses at top of public methods (early returns / raises), not nested try/except everywhere. `FileNotFoundError` raised directly, `ImportError` re-raised after logging.

**The SpreadsheetParser should follow the same pattern:**

```python
# raganything/spreadsheet.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class SpreadsheetConfig:
    chunk_row_size: int = 200
    chunk_overlap_rows: int = 0  # see section 5

class SpreadsheetParser:
    def __init__(self, config: Optional[SpreadsheetConfig] = None):
        self.config = config or SpreadsheetConfig()

    def parse(self, file_path: Path) -> list[dict]:
        # guarded imports inside
        try:
            import openpyxl
        except ImportError:
            raise ImportError("openpyxl is required. Install with: pip install raganything[spreadsheet]")
        ...

def get_supported_formats() -> list[str]:
    return [".xlsx", ".xls"]

def is_supported_format(file_path: Path) -> bool:
    return file_path.suffix.lower() in get_supported_formats()
```

---

## 5. Chunking Recommendation

### How LightRAG processes table content_list items

From `processor.py` and `modalprocessors.py`:

1. Each item in `multimodal_items` becomes **one chunk** — one call to `TableModalProcessor.process_multimodal_content`.
2. The processor sends `table_body` to an LLM for description generation, then stores it as a vector chunk.
3. There is no further chunking of `table_body` inside `TableModalProcessor` — it is treated as atomic.
4. Token budget for chunk content: LightRAG default chunk size is typically 1200 tokens. The `table_body` markdown goes into a prompt alongside captions and footnotes.

### Implication for large sheets

A 500-row sheet can produce a markdown table with thousands of tokens. Passing this directly to an LLM as `table_body` will exceed context limits or degrade quality. **Each `content_list` item must stay within LLM-processable size.**

### Recommendation: Row-based chunking

**Threshold:** 150 rows per chunk. This is a practical ceiling — a 150-row table with 10 columns produces roughly 1500-2000 characters (well under typical 4096-token limits when combined with prompts and captions).

**Overlap:** 0 rows overlap. Tables are structured data; overlap creates duplicate rows that confuse the LLM and inflate storage. The caption communicates continuity instead.

**Caption format for chunks** (Claude's Discretion):

```
Sheet: {sheet_name}
Rows: {start_row}–{end_row} of {total_rows}
```

Example:
```
Sheet: Revenue Summary
Rows: 1–150 of 487
```

For single-chunk sheets (no chunking needed), caption is simply:
```
Sheet: {sheet_name}
```

**Header row repetition:** Do NOT repeat the header row in continuation chunks. The caption already names the sheet and row range. The markdown table is self-describing as data. Repeating headers increases token cost and creates inconsistency when the first row is not actually a header (locked: no header inference).

**`page_idx` assignment:** Use sheet index (0-based position in workbook) as `page_idx`. For chunked sheets, all chunks of the same sheet share the same `page_idx`. This allows context extraction by `ContextExtractor` to find surrounding sheets.

---

## 6. pyproject.toml Extras Pattern

### Existing structure

```toml
[project.optional-dependencies]
image    = ["Pillow>=10.0.0"]
text     = ["reportlab>=4.0.0"]
office   = []   # external program, no pip deps
audio    = ["faster-whisper>=0.10.0", "librosa>=0.10.0", "soundfile>=0.12.0"]
all      = [
    "Pillow>=10.0.0",
    ...all audio deps...,
]
```

### Pattern for `spreadsheet` group

```toml
[project.optional-dependencies]
spreadsheet = [
    "openpyxl>=3.1.2",
    "xlrd>=2.0.1",
]
```

`xlrd` handles `.xls` (old Excel format). `openpyxl` handles `.xlsx`. Both should be in the same extra group since a spreadsheet parser is expected to handle both formats.

**`all` group update:** Add `"openpyxl>=3.1.2"` and `"xlrd>=2.0.1"` to the `all` group list.

**Note on xlrd:** `xlrd>=2.0.0` dropped `.xlsx` support — it handles only `.xls`. This is correct and expected. The parser must branch on file extension.

---

## 7. Additional Implementation Notes

### xls vs xlsx dispatch

```python
ext = file_path.suffix.lower()
if ext == ".xlsx":
    return self._parse_xlsx(file_path)
elif ext == ".xls":
    return self._parse_xls(file_path)
else:
    raise ValueError(f"Unsupported format: {ext}")
```

For `.xls`, xlrd's API differs from openpyxl. Key differences:
- `xlrd.open_workbook(path)` returns a `Book`
- Sheets: `book.sheet_by_index(i)`, `book.sheet_names()`
- Hidden sheets: `book.sheet_visibility(i)` — 0=visible, 1=hidden, 2=veryHidden
- Merged cells: `sheet.merged_cells` returns list of `(rlo, rhi, clo, chi)` tuples (0-based, rhi/chi exclusive)
- Cell values: `sheet.cell(row, col).value` — returns Python types
- No `data_only` needed — xlrd always returns values

### Empty sheet detection

```python
def _is_empty_sheet(ws) -> bool:
    for row in ws.iter_rows(values_only=True):
        if any(cell is not None for cell in row):
            return False
    return True
```

`max_row == 1` and `max_column == 1` with `ws["A1"].value is None` is a common empty sheet pattern, but iterating is more reliable and handles edge cases (a sheet with a single empty merged region, etc.).

### Merge annotation suffix format

Format string: ` [merged {span_rows}×{span_cols}]`

Examples:
- Horizontal 3-wide: `Revenue [merged 1×3]` — communicates 1 row spans 3 columns
- Vertical 3-tall: `Q1 [merged 3×1]` — communicates 3 rows span 1 column
- 2D merge: `Header [merged 2×3]`

Only annotate when `span_rows > 1 or span_cols > 1`. A 1×1 cell that happens to be "merged" (degenerate) is treated as normal.
