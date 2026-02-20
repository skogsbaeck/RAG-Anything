# Architecture: Direct Spreadsheet Parser Integration

**Research Date:** 2026-02-20
**Scope:** How a direct xlsx/xls parser integrates with existing RAG-Anything architecture
**Pattern Reference:** Audio parser addition (commits a8e2e02 – 4e51e1e on `feature/audio-transcription-support`)

---

## Component Boundaries

### New Component: `SpreadsheetParser`

**Location:** `raganything/spreadsheet.py`
**Boundary:** Pure parsing concern — reads xlsx/xls files via openpyxl and produces `content_list` items. No RAG knowledge, no LightRAG dependency, no LLM calls.

**Responsibilities:**
- Open workbook with openpyxl (or xlrd for .xls fallback)
- Iterate sheets and rows
- Convert each sheet/range to a GitHub-flavoured markdown table string
- Return `List[Dict[str, Any]]` conforming to the `content_list` contract

**Does not own:**
- Fallback to LibreOffice path (caller decides)
- LightRAG insertion (ProcessorMixin owns that)
- Table analysis/LLM description (TableModalProcessor owns that)

**Content list items produced:**

```python
{
    "type": "table",
    "table_body": "<markdown table string>",
    "table_caption": "<sheet name>",
    "table_footnote": "",
    "img_path": "",          # no image; TableModalProcessor handles text-only tables
    "page_idx": <sheet_index>,
    "metadata": {
        "source_type": "spreadsheet_direct",
        "sheet_name": "<name>",
        "row_count": <int>,
        "col_count": <int>,
        "file_name": "<basename>"
    }
}
```

The `"type": "table"` value is the critical contract — it causes `separate_content()` in `utils.py` to route items to `TableModalProcessor`, exactly as MinerU-extracted tables do.

---

### Modified Component: `MineruParser.parse_spreadsheet` (in `raganything/parser.py`)

A new method added to `MineruParser`, mirroring the `parse_audio` pattern:

```python
def parse_spreadsheet(
    self,
    file_path: Union[str, Path],
    output_dir: Optional[str] = None,
    lang: Optional[str] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    ...
```

**Boundary:** Imports `SpreadsheetParser` from `raganything/spreadsheet.py` (guarded by `try/except ImportError`), delegates parsing, and returns the `content_list`. Catches errors and optionally falls back to `parse_office_doc` (LibreOffice path) if the flag is set in kwargs.

`MineruParser.parse_document()` already routes `.xls`/`.xlsx` through `parse_office_doc` via the `OFFICE_FORMATS` branch. That branch will be updated to call `parse_spreadsheet` instead.

---

### Modified Component: `ProcessorMixin` (in `raganything/processor.py`)

**Change location:** The `elif ext in [".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ...]` branch, currently at lines 380–399.

Split `.xls`/`.xlsx` out of the generic Office branch into their own branch:

```python
elif ext in [".xls", ".xlsx"]:
    self.logger.info("Detected spreadsheet, using direct parser...")
    content_list = await asyncio.to_thread(
        doc_parser.parse_spreadsheet,
        file_path=file_path,
        output_dir=output_dir,
        **kwargs,
    )
```

**Boundary:** Routing only. No parsing logic lives here. Fallback is delegated into `parse_spreadsheet` itself so the processor stays ignorant of the fallback mechanism.

---

### Unchanged Component: `TableModalProcessor` (in `raganything/modalprocessors.py`)

No changes required. It already accepts table items from the `content_list` and works from `table_body` text. The markdown table string produced by `SpreadsheetParser` is valid input to the existing LLM prompts in `PROMPTS["table_prompt"]`.

---

### Modified Component: `RAGAnythingConfig` (in `raganything/config.py`)

Two new fields following existing env-var patterns:

```python
enable_direct_spreadsheet_parsing: bool = field(
    default=get_env_value("ENABLE_DIRECT_SPREADSHEET_PARSING", True, bool)
)
"""Use openpyxl direct parsing for xlsx/xls instead of LibreOffice → PDF path."""

spreadsheet_max_rows_per_sheet: int = field(
    default=get_env_value("SPREADSHEET_MAX_ROWS_PER_SHEET", 1000, int)
)
"""Maximum rows per sheet before truncation to avoid oversized content blocks."""
```

Config is read in `ProcessorMixin` when routing and passed as kwargs into `parse_spreadsheet`.

---

## Data Flow

```
User: process_document_complete("report.xlsx")
         │
         ▼
ProcessorMixin._parse_document()          [processor.py ~line 332]
  ext = ".xlsx"
  if ENABLE_DIRECT_SPREADSHEET_PARSING:
    → doc_parser.parse_spreadsheet(file_path)
  else:
    → doc_parser.parse_office_doc(file_path)   ← existing LibreOffice path
         │
         ▼  (direct path)
MineruParser.parse_spreadsheet()          [parser.py]
  try:
    → SpreadsheetParser.parse(file_path)  [spreadsheet.py]
         │
         ▼
    openpyxl opens workbook
    for each sheet:
      rows → markdown table string
      append {"type": "table", "table_body": md_table, ...}
    return content_list
  except (ImportError, Exception):
    fallback → self.parse_office_doc(file_path)  ← graceful degradation
         │
         ▼
content_list returned to ProcessorMixin
         │
         ▼
separate_content(content_list)            [utils.py]
  text items  → inserted into LightRAG text pipeline
  table items → routed to TableModalProcessor
         │
         ▼
TableModalProcessor.process_modal_item()  [modalprocessors.py]
  table_body = item["table_body"]         ← markdown table string works here
  LLM call via PROMPTS["table_prompt"]
  entities/relations inserted into LightRAG KG
```

**Key data contracts at each boundary:**

| Boundary | Format |
|---|---|
| `SpreadsheetParser` → caller | `List[Dict]` with `"type": "table"`, `"table_body"` as markdown string |
| `parse_spreadsheet` → `ProcessorMixin` | Same `List[Dict]` (pass-through) |
| `separate_content()` → `TableModalProcessor` | `content_data["table_body"]` — string or list accepted |
| `TableModalProcessor` → LightRAG | Entity/relation tuples via `extract_entities()` |

---

## Suggested Build Order

Dependencies flow upward — each phase must be complete before the next.

### Phase 1 — `SpreadsheetParser` in isolation

**File:** `raganything/spreadsheet.py`

Create `SpreadsheetParser` with a single `parse(file_path, max_rows_per_sheet) -> List[Dict]` method. No external dependencies except openpyxl.

Write unit tests (pytest) covering:
- Single sheet, multi-sheet workbooks
- Empty sheets (skip or emit empty table)
- Row truncation at `max_rows_per_sheet`
- Unicode cell values
- Non-numeric/mixed types
- Missing file raises `FileNotFoundError`

This phase has zero coupling to the rest of RAG-Anything and can be validated entirely standalone.

### Phase 2 — `MineruParser.parse_spreadsheet` in `parser.py`

Wire `SpreadsheetParser` into `MineruParser` following the `parse_audio` pattern:
- Guarded import with `ImportError` hint
- Fallback call to `self.parse_office_doc` on failure
- Update `parse_document()` to route `.xls`/`.xlsx` to the new method

Tests: mock `SpreadsheetParser` to verify routing; mock `parse_office_doc` to verify fallback fires on `ImportError`.

### Phase 3 — Config additions in `config.py`

Add `enable_direct_spreadsheet_parsing` and `spreadsheet_max_rows_per_sheet` fields with env var support. No code elsewhere changes yet — pure config expansion.

Tests: verify env vars parse correctly; verify defaults.

### Phase 4 — `ProcessorMixin` routing in `processor.py`

Split `.xls`/`.xlsx` out of the shared Office branch. Read `config.enable_direct_spreadsheet_parsing` to decide which parser method to call.

Tests: integration-level, mock `parse_spreadsheet` and `parse_office_doc`; verify the right branch executes based on extension and config flag.

### Phase 5 — End-to-end validation

Create `examples/spreadsheet_test.py` following the `office_document_test.py` pattern. Run against a real xlsx file with multiple sheets, numeric values, and unicode content. Confirm `TableModalProcessor` receives and processes the table items.

---

## Architecture Rationale

**Why a separate `spreadsheet.py` module (not inline in `parser.py`)?**
The audio feature followed the same split — `audio.py` holds `AudioProcessor` with its own config dataclasses, and `parser.py` calls into it with a guarded import. This isolates optional-dependency code from the core parser module and keeps the `parser.py` file under 300 lines per convention.

**Why `"type": "table"` and not a new type like `"spreadsheet"`?**
`TableModalProcessor` is already wired to handle `"table"` items. Introducing a new type would require changes to `separate_content()` in `utils.py`, `modalprocessors.py`, and potentially `processor.py`. Reusing `"table"` with a `metadata.source_type = "spreadsheet_direct"` discriminator gives full downstream compatibility at zero additional cost.

**Why does the fallback live in `parse_spreadsheet` rather than `ProcessorMixin`?**
`ProcessorMixin` is a routing layer — it should not understand parsing failure modes. Keeping fallback logic inside the parser layer means the routing branch stays a single call, consistent with all other branches. It also means `DoclingParser` could later implement its own `parse_spreadsheet` with different fallback behaviour without touching `ProcessorMixin`.

**Why does `TableModalProcessor` require no changes?**
`TableModalProcessor.generate_description_only()` at line 1057 already accepts `table_body` as either a JSON-decoded dict or a raw string. Markdown table strings are valid input. The LLM prompts reference `table_body` directly, so a markdown-formatted table is semantically richer input than the sparse cell lists LibreOffice/MinerU sometimes produce.

---

*Research by: gsd-project-researcher · 2026-02-20*
