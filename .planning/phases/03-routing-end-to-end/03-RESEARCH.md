# Phase 3: Routing + End-to-End - Research

**Researched:** 2026-02-21
**Domain:** ProcessorMixin routing, formula-None threshold, content_list contract, E2E test strategy
**Confidence:** HIGH (all findings from direct codebase inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Content contract**
- Minimal metadata only — table_body, table_caption, type, page_idx. Caption already carries sheet name context; no extra fields needed
- Field reshaping approach and content type naming: Claude's discretion based on existing codebase patterns
- Content length guard vs Phase 1 chunking: Claude's discretion based on LightRAG constraints

**Fallback behavior**
- Fallback to LibreOffice is always available — no strict mode flag
- Tests must be designed so direct parsing is exercised (not accidentally falling through to fallback)
- Formula-None threshold (>10% triggers fallback) must be validated in Phase 3 with a test fixture using simulated None values
- Double-failure handling (direct + LibreOffice both fail) and degraded-result marking: Claude's discretion based on existing pipeline error patterns

**E2E test strategy**
- Two test layers: mock LightRAG tests for CI (fast), plus one real integration test marked slow/optional
- Real integration test should query LightRAG for known cell values to prove data reaches the knowledge graph
- All fixtures created programmatically with openpyxl — no committed binary files in git
- Formula-None threshold tested by injecting None values (simulating uncached formulas), not real Excel formulas

**Multi-sheet handling**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 3 is entirely about activating and verifying the already-built pipeline: routing xlsx/xls through `SpreadsheetParser` in the live `ProcessorMixin` pipeline, confirming the content_list items produced satisfy the `TableModalProcessor` contract, implementing and validating the formula-None threshold fallback heuristic, and running an E2E test that proves data reaches the LightRAG knowledge graph.

The key finding is that Phase 2 already completed the production routing. `ProcessorMixin.parse_document()` (processor.py lines 380–398) already has a dedicated `.xls`/`.xlsx` branch that calls `doc_parser.parse_spreadsheet()` when `self.config.enable_direct_spreadsheet_parsing` is True. The routing tests in `tests/test_processor_spreadsheet.py` confirm this works at the dispatch level. Phase 3 now adds: (1) the formula-None threshold logic (currently absent from the codebase), (2) contract verification that `SpreadsheetParser` output fields satisfy `TableModalProcessor`, and (3) E2E tests that wire through to LightRAG.

The formula-None threshold is a new piece of logic to implement. It does NOT exist anywhere in the current codebase — it must be added to `MineruParser.parse_spreadsheet()` or to `SpreadsheetParser.parse()`. The threshold validates that `data_only=True` produced meaningful values (>10% None cells → suspicion that formulas were uncached → trigger LibreOffice fallback).

**Primary recommendation:** Add the formula-None threshold inside `MineruParser.parse_spreadsheet()` (after calling `SpreadsheetParser(...).parse()`) rather than inside `SpreadsheetParser` itself — it is a fallback decision, not a parsing concern.

---

## What Phase 2 Already Delivered (HIGH confidence)

These are DONE and must NOT be re-implemented:

| Component | Location | Status |
|-----------|----------|--------|
| `SpreadsheetParser.parse()` | `raganything/spreadsheet.py` | DONE - Phase 1 |
| `MineruParser.parse_spreadsheet()` with LibreOffice fallback | `raganything/parser.py` lines 1231–1267 | DONE - Phase 2 |
| `RAGAnythingConfig.enable_direct_spreadsheet_parsing` | `raganything/config.py` lines 52–59 | DONE - Phase 2 |
| `RAGAnythingConfig.spreadsheet_max_rows_per_chunk` | `raganything/config.py` lines 57–60 | DONE - Phase 2 |
| `ProcessorMixin.parse_document()` xlsx/xls branch | `raganything/processor.py` lines 380–398 | DONE - Phase 2 |
| Zero-content guard bypass for direct spreadsheet path | `raganything/processor.py` lines 458–462 | DONE - Phase 2 |
| Routing tests | `tests/test_processor_spreadsheet.py` | DONE - Phase 2 |
| parse_spreadsheet integration tests | `tests/test_parse_spreadsheet.py` | DONE - Phase 2 |

### Current processor.py xlsx branch (exact code):
```python
# processor.py lines 380–398
elif ext in [".xls", ".xlsx"]:
    self.logger.info("Detected spreadsheet file, using direct parser...")
    if self.config.enable_direct_spreadsheet_parsing:
        content_list = await asyncio.to_thread(
            doc_parser.parse_spreadsheet,
            file_path=file_path,
            output_dir=output_dir,
            max_rows_per_chunk=self.config.spreadsheet_max_rows_per_chunk,
            **kwargs,
        )
    else:
        self.logger.info(
            "Direct spreadsheet parsing disabled, using LibreOffice path..."
        )
        content_list = await asyncio.to_thread(
            doc_parser.parse_office_doc,
            doc_path=file_path,
            output_dir=output_dir,
            **kwargs,
        )
```

### Current parse_spreadsheet() (exact code):
```python
# parser.py lines 1231–1267
def parse_spreadsheet(self, file_path, output_dir=None, lang=None,
                      max_rows_per_chunk=150, **kwargs):
    try:
        from raganything.spreadsheet import SpreadsheetParser, SpreadsheetConfig
    except ImportError:
        raise ImportError(...)

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(...)

    config = SpreadsheetConfig(max_rows_per_chunk=max_rows_per_chunk)

    try:
        content_list = SpreadsheetParser(config).parse(file_path)
        self.logger.info(...)
        return content_list
    except ImportError:
        raise
    except Exception as exc:
        self.logger.warning(
            f"Spreadsheet direct parse failed for {file_path.name} "
            f"({type(exc).__name__}), falling back to LibreOffice"
        )
        return self.parse_office_doc(file_path, output_dir, lang, **kwargs)
```

### Zero-content guard bypass (exact code):
```python
# processor.py lines 458–462
is_direct_spreadsheet = (
    ext in [".xls", ".xlsx"]
    and self.config.enable_direct_spreadsheet_parsing
)
if len(content_list) == 0 and not is_direct_spreadsheet:
    raise ValueError("Parsing failed: No content was extracted")
```

---

## Architecture Patterns

### Content Contract: What TableModalProcessor Expects

`get_processor_for_type()` in `utils.py` (line 238) maps `content_type == "table"` to `modal_processors.get("table")` which is the registered `TableModalProcessor`. The `TableModalProcessor.generate_description_only()` reads these fields from `modal_content`:

```python
# modalprocessors.py lines 1065–1068
table_img_path = content_data.get("img_path")         # optional, can be None
table_caption  = content_data.get("table_caption", []) # list
table_body     = content_data.get("table_body", "")   # string (markdown table)
table_footnote = content_data.get("table_footnote", []) # list, optional
```

`SpreadsheetParser._chunk_rows()` already produces items in this shape:
```python
{"type": "table", "table_body": markdown, "table_caption": [caption], "page_idx": sheet_idx}
```

This matches exactly. The contract is already satisfied. `img_path` and `table_footnote` are optional (use `.get()` with defaults). `table_caption` is a list — the current SpreadsheetParser wraps the caption string in a list (`[caption]`), which is correct.

Additionally, `_apply_chunk_template()` in `processor.py` (line 998) uses `content_type == "table"` to select the `table_chunk` prompt — so `type: "table"` is the correct value. Do NOT use `"spreadsheet_table"` as it would fall through to the `generic_chunk` template instead.

`separate_content()` in `utils.py` (lines 13–56) treats anything that is NOT `type == "text"` as multimodal. So `type: "table"` items correctly route to `multimodal_items`, and are then picked up by `_process_multimodal_content_batch_type_aware()`.

### Formula-None Threshold: New Logic Required

This logic does NOT exist yet. It must be added. The requirement: if more than 10% of cells in the content_list are None (empty string in the rendered markdown), this suggests Excel formulas were not cached by `data_only=True` and the LibreOffice path should be tried instead.

The implementation choice (HIGH confidence recommendation based on codebase patterns):

Add the threshold check inside `MineruParser.parse_spreadsheet()`, after `SpreadsheetParser.parse()` succeeds but before returning:

```python
def parse_spreadsheet(self, file_path, output_dir=None, lang=None,
                      max_rows_per_chunk=150, **kwargs):
    from raganything.spreadsheet import SpreadsheetParser, SpreadsheetConfig
    ...
    try:
        content_list = SpreadsheetParser(config).parse(file_path)

        # Formula-None threshold: >10% None cells → LibreOffice fallback
        if _none_ratio_exceeds_threshold(content_list, threshold=0.10):
            self.logger.warning(
                f"High None-cell ratio in {file_path.name} "
                "(possible uncached formulas), falling back to LibreOffice"
            )
            return self.parse_office_doc(file_path, output_dir, lang, **kwargs)

        return content_list
    except ImportError:
        raise
    except Exception as exc:
        ...
```

**Helper function for None ratio calculation** — this belongs as a module-level or private function in `parser.py`, not in `spreadsheet.py` (it is a fallback decision, not a parsing concern):

```python
def _none_ratio_exceeds_threshold(content_list: list, threshold: float = 0.10) -> bool:
    """Return True if >threshold fraction of table cells are empty/None."""
    total_cells = 0
    none_cells = 0
    for item in content_list:
        if item.get("type") == "table":
            body = item.get("table_body", "")
            # Count pipe-delimited cells in markdown table rows
            for line in body.splitlines():
                if line.startswith("|") and "---" not in line:
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    total_cells += len(cells)
                    none_cells += sum(1 for c in cells if not c)
    if total_cells == 0:
        return False
    return (none_cells / total_cells) > threshold
```

**Testing the threshold** — per the locked decision, test by injecting None values directly into cell data (not real Excel formulas). A fixture built with openpyxl that sets many cells to `None` value will produce many empty cells after `data_only=True` parsing.

### E2E Test Architecture

Two layers as locked:

**Layer 1: Mock LightRAG (CI-safe, fast)**
Pattern: Use `_StubProcessor` duck-typing approach (established in Phase 2 tests) for the routing layer. For the E2E contract test, mock `_process_multimodal_content` and assert that multimodal items have `type`, `table_body`, `table_caption`, and `page_idx` fields with correct types.

```python
class TestContractVerification:
    def test_multi_sheet_content_list_contract(self, tmp_path):
        """Assert each item in content_list satisfies TableModalProcessor contract."""
        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "Sheet1"
        ws1["A1"] = "Revenue"
        ws1["B1"] = 1000
        ws2 = wb.create_sheet("Sheet2")
        ws2["A1"] = "Cost"
        ws2["B1"] = 500
        path = tmp_path / "multi.xlsx"
        wb.save(str(path))

        result = MineruParser().parse_spreadsheet(path)

        assert len(result) == 2  # two sheets
        for item in result:
            assert isinstance(item["type"], str)
            assert isinstance(item["table_body"], str)
            assert isinstance(item["table_caption"], list)
            assert isinstance(item["page_idx"], int)
            assert item["type"] == "table"
            assert len(item["table_body"]) > 0
```

**Layer 2: Real integration test (slow/optional)**
Mark with `@pytest.mark.slow` (need to register marker in `pyproject.toml`). The test must:
1. Initialize a real LightRAG instance in a temp directory
2. Create a RAGAnything instance wrapping it
3. Call `process_document_complete("workbook.xlsx")` on a known fixture
4. Query LightRAG for a known cell value and assert it appears in results

No `pytest.mark.slow` marker is registered in `pyproject.toml` yet — must add it.

```toml
# pyproject.toml — add to [tool.pytest.ini_options]
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m not slow')",
]
```

### page_idx Strategy for Multi-Sheet Workbooks

Looking at `SpreadsheetParser._chunk_rows()` (spreadsheet.py line 287):
```python
{"type": "table", "table_body": markdown, "table_caption": [caption], "page_idx": sheet_idx}
```

`sheet_idx` is the loop variable from `enumerate(wb.worksheets)` — it is already the 0-based sheet index. For chunked sheets, all chunks of the same sheet get the same `sheet_idx`. This is the correct behavior: `page_idx` maps to which "page" (sheet), not which row range within a sheet.

This is already implemented correctly in Phase 1. No change needed.

### Double-Failure Handling

When direct parsing fails AND LibreOffice fallback also fails:

Looking at the existing pattern in `_process_multimodal_content()` (processor.py line 574–583):
```python
except Exception as e:
    self.logger.error(f"Error in multimodal processing: {e}")
    self.logger.warning("Falling back to individual multimodal processing")
    await self._process_multimodal_content_individual(...)
```

The existing pipeline uses "try primary → catch → try fallback → mark complete regardless" pattern. For double-failure in parsing:
- `parse_spreadsheet()` already propagates exceptions from `parse_office_doc()` if LibreOffice also fails (it doesn't catch exceptions from the fallback call)
- `ProcessorMixin.parse_document()` re-raises via `except Exception as e: ... raise e` (lines 449–453)
- So double failure surfaces as an exception to the caller — the existing behavior is correct

Recommendation: Do NOT mark degraded results. The pipeline errors out explicitly, which is better than silently inserting partial content.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| spreadsheet dispatch | Custom .xlsx/.xls routing | Already done in processor.py lines 380–398 | Phase 2 complete |
| LibreOffice fallback | New subprocess caller | `self.parse_office_doc()` in parser.py | Already exists |
| table content processing | Custom LightRAG insertion | `TableModalProcessor` via `_process_multimodal_content_batch_type_aware()` | Already wired |
| test stub setup | Full RAGAnything init | `_StubProcessor` duck-typing pattern | Already established in test_processor_spreadsheet.py |
| openpyxl fixture creation | Binary .xlsx files | `openpyxl.Workbook()` + `wb.save(tmp_path / "file.xlsx")` | Established pattern in test_parse_spreadsheet.py |
| slow test registration | Custom skip logic | `@pytest.mark.slow` + `pyproject.toml` markers config | pytest standard |

---

## Common Pitfalls

### Pitfall 1: Formula-None Threshold on the Wrong End

**What goes wrong:** Implementing the threshold check inside `SpreadsheetParser._chunk_rows()` or `_parse_xlsx()`, causing it to raise an exception that triggers the existing exception fallback in `parse_spreadsheet()`.

**Why it happens:** It seems logical to detect the issue where parsing happens.

**How to avoid:** Keep the threshold check in `MineruParser.parse_spreadsheet()` after `SpreadsheetParser.parse()` returns successfully. The threshold is a business heuristic about whether to trust results, not a parsing error. Mixing it into SpreadsheetParser couples parsing concerns with fallback policy.

**Warning signs:** Any threshold check inside `spreadsheet.py`.

### Pitfall 2: Using type "spreadsheet_table" Instead of "table"

**What goes wrong:** Returning `type: "spreadsheet_table"` from SpreadsheetParser produces content items that don't match `TableModalProcessor` in `get_processor_for_type()`. The items would fall through to `GenericModalProcessor` instead, losing table-specific LLM prompts.

**Why it happens:** It seems natural to distinguish spreadsheet tables from PDF-extracted tables.

**How to avoid:** Use `type: "table"` — this is the value that `get_processor_for_type()` maps to `TableModalProcessor`. The caption string already distinguishes source context ("workbook.xlsx - Sheet: Inventory").

**Warning signs:** Any `content_type == "spreadsheet_table"` check anywhere in the codebase.

### Pitfall 3: Tests That Don't Assert the Direct Path Is Taken

**What goes wrong:** Writing tests that call `process_document_complete()` and only check that some output was produced, without asserting that `parse_spreadsheet()` (not `parse_office_doc()`) was called.

**Why it happens:** The fallback path might accidentally produce the expected output, making the test green while the direct path is never exercised.

**How to avoid:** Use `unittest.mock.patch.object(parser, "parse_office_doc")` and assert `mock_fallback.assert_not_called()`. Alternatively, spy on `SpreadsheetParser.parse` and assert it was called.

**Warning signs:** E2E tests that don't assert which parser method was invoked.

### Pitfall 4: pytest.mark.slow Not Registered

**What goes wrong:** Using `@pytest.mark.slow` without registering it in `pyproject.toml` produces a `PytestUnknownMarkWarning` and may cause CI to fail.

**Why it happens:** pytest requires markers to be registered when using strict mode.

**How to avoid:** Add `[tool.pytest.ini_options]` with `markers = ["slow: marks tests as slow (deselect with '-m not slow')"]` to `pyproject.toml` before using the mark.

### Pitfall 5: .gitignore test_* Pattern

**What goes wrong:** The `.gitignore` has a `test_*` pattern (documented in STATE.md pending todos). New test files require `git add -f` to commit.

**Why it happens:** The existing ignore pattern is too broad.

**How to avoid:** When creating new test files, use `git add -f tests/test_*.py`. The planner should note this in each task that creates a new test file.

### Pitfall 6: MineruParser __slots__ = ()

**What goes wrong:** Any attempt to store instance state on `MineruParser` (e.g., `self.formula_threshold = 0.10`) will raise `AttributeError` at runtime.

**Why it happens:** `MineruParser` has `__slots__ = ()` which prevents instance attributes.

**How to avoid:** The threshold constant should be a module-level constant or a function parameter default. Not a `self.` attribute.

---

## Code Examples

### Verified: SpreadsheetParser output item shape
```python
# Source: raganything/spreadsheet.py lines 287, 294-295
# Single-chunk sheet:
{"type": "table", "table_body": markdown, "table_caption": [caption], "page_idx": sheet_idx}

# Multi-chunk sheet (rows 1-150 of 300):
{"type": "table", "table_body": markdown, "table_caption": [f"{wbname} - Sheet: {name} (rows {start+1}-{end} of {total})"], "page_idx": sheet_idx}
```

### Verified: TableModalProcessor field reads
```python
# Source: raganything/modalprocessors.py lines 1065–1068
table_img_path = content_data.get("img_path")          # None is fine
table_caption  = content_data.get("table_caption", []) # list expected
table_body     = content_data.get("table_body", "")   # string expected
table_footnote = content_data.get("table_footnote", []) # list, optional
```

### Verified: get_processor_for_type "table" routing
```python
# Source: raganything/utils.py lines 238-239
elif content_type == "table":
    return modal_processors.get("table")  # returns TableModalProcessor
```

### Verified: separate_content puts "table" in multimodal_items
```python
# Source: raganything/utils.py lines 28-38
for item in content_list:
    content_type = item.get("type", "text")
    if content_type == "text":
        text_parts.append(item.get("text", ""))
    else:
        multimodal_items.append(item)  # "table" items go here
```

### Formula-None threshold (new, to be implemented)
```python
# Location: raganything/parser.py — module level or inside parse_spreadsheet
_FORMULA_NONE_THRESHOLD = 0.10

def _none_ratio_exceeds_threshold(content_list: list, threshold: float = _FORMULA_NONE_THRESHOLD) -> bool:
    """Return True if >threshold fraction of markdown table cells are empty."""
    total_cells = 0
    none_cells = 0
    for item in content_list:
        if item.get("type") == "table":
            body = item.get("table_body", "")
            for line in body.splitlines():
                if line.startswith("|") and "---" not in line:
                    cells = [c.strip() for c in line.strip().strip("|").split("|")]
                    total_cells += len(cells)
                    none_cells += sum(1 for c in cells if not c)
    if total_cells == 0:
        return False
    return (none_cells / total_cells) > threshold
```

### Existing test fixture pattern (openpyxl programmatic)
```python
# Source: tests/test_parse_spreadsheet.py lines 24–38
@pytest.fixture
def simple_xlsx(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventory"
    ws["A1"] = "Product"
    ws["B1"] = "Quantity"
    ws["A2"] = "Widget"
    ws["B2"] = 10
    path = tmp_path / "inventory.xlsx"
    wb.save(str(path))
    return path
```

### Formula-None fixture for threshold test
```python
# New pattern for Phase 3 — inject None values to simulate uncached formulas
@pytest.fixture
def formula_heavy_xlsx(tmp_path):
    """Workbook where >10% of cells are None (simulating uncached formulas)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Formulas"
    # 1 real cell + 20 None cells = 95.2% None
    ws["A1"] = "Revenue"
    # leave B1:U1 as None (not set = None when read back)
    path = tmp_path / "formula_heavy.xlsx"
    wb.save(str(path))
    return path
```

---

## New Files Required

| File | Purpose |
|------|---------|
| `tests/test_e2e_spreadsheet.py` | E2E tests: contract verification + mock LightRAG + slow real integration test |

| File | Change |
|------|--------|
| `raganything/parser.py` | Add `_none_ratio_exceeds_threshold()` + threshold check in `parse_spreadsheet()` |
| `pyproject.toml` | Add `[tool.pytest.ini_options]` with `slow` marker registration |

The following files are NOT modified in Phase 3 (already complete):
- `raganything/spreadsheet.py`
- `raganything/processor.py`
- `raganything/config.py`

---

## Open Questions

1. **Does the real integration test need LightRAG mocked or real?**
   - What we know: The locked decision says "one real integration test marked slow/optional" with "query LightRAG for known cell values"
   - What's unclear: LightRAG initialization in tests requires LLM API keys and a working LightRAG backend — this may not be available in all CI environments
   - Recommendation: Mark `@pytest.mark.slow` and skip unless an env var like `RAG_ANYTHING_INTEGRATION_TEST=1` is set, which matches the "optional" qualifier in the locked decision

2. **Threshold constant location**
   - What we know: `MineruParser.__slots__ = ()` forbids instance attributes
   - What's unclear: Whether threshold should be a module constant (`_FORMULA_NONE_THRESHOLD = 0.10`) or a parameter default in `parse_spreadsheet()`
   - Recommendation: Module-level constant — makes it easy to reference in tests

---

## Sources

### Primary (HIGH confidence)
- Direct inspection of `raganything/processor.py` — xlsx branch lines 380–398, zero-content guard lines 458–462
- Direct inspection of `raganything/parser.py` — `parse_spreadsheet()` lines 1231–1267, `__slots__` line 584
- Direct inspection of `raganything/spreadsheet.py` — `_chunk_rows()` lines 272–296, content item shape
- Direct inspection of `raganything/modalprocessors.py` — `TableModalProcessor.generate_description_only()` lines 1035–1123
- Direct inspection of `raganything/utils.py` — `separate_content()` lines 13–56, `get_processor_for_type()` lines 224–244
- Direct inspection of `raganything/processor.py` — `_apply_chunk_template()` lines 965–1038
- Direct inspection of `tests/test_parse_spreadsheet.py` — fixture pattern and existing tests
- Direct inspection of `tests/test_processor_spreadsheet.py` — `_StubProcessor` duck-typing pattern
- Direct inspection of `pyproject.toml` — no `[tool.pytest.ini_options]` exists yet
- Direct inspection of `.planning/STATE.md` — formula-None threshold listed as Phase 3 concern

---

## Metadata

**Confidence breakdown:**
- Phase 2 completion status: HIGH — verified by reading current source files
- Content contract (SpreadsheetParser → TableModalProcessor): HIGH — read both files, traced field names
- Formula-None threshold (new logic): HIGH for requirement, MEDIUM for exact implementation shape
- E2E test architecture: HIGH — based on existing test patterns in the repo
- type "table" vs "spreadsheet_table": HIGH — traced through get_processor_for_type() and _apply_chunk_template()

**Research date:** 2026-02-21
**Valid until:** Until parser.py, modalprocessors.py, or utils.py field names change
