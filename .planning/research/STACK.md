# Stack Research: Direct xlsx/xls Parsing for RAG-Anything

**Research Date:** 2026-02-20
**Milestone:** Direct spreadsheet parsing — xlsx/xls without LibreOffice
**Scope:** Library selection for reading xlsx/xls files, handling merged cells, formulas, multi-sheet workbooks, and converting output to markdown tables compatible with the existing `content_list` format.

> **Version Note:** Versions below are verified against training data (knowledge cutoff: August 2025). Confidence levels are assigned per recommendation. Before pinning in `pyproject.toml`, verify the latest patch release via `pip index versions <package>` or PyPI.

---

## Decision Summary

| Library | Role | Version | Confidence |
|---------|------|---------|------------|
| `openpyxl` | Primary xlsx parser | `>=3.1.2` | High |
| `xlrd` | Legacy xls parser | `>=2.0.1` | High |
| No pandas | Ruled out — heavy, lossy for structure | — | High |
| No xlwings | Ruled out — requires Excel installation | — | High |
| No calamine | Ruled out — Rust extension, poor portability | — | Medium |

---

## Primary Library: openpyxl

**Install:** `pip install openpyxl>=3.1.2`

**Rationale:**

openpyxl is the de-facto standard for reading and writing `.xlsx` files in Python. It is the library used internally by `pandas.read_excel()` when the xlsx engine is selected, which means it is battle-tested at scale. Its key properties for this milestone are:

- **Merged cell support.** openpyxl exposes `worksheet.merged_cells` as a set of `MergedCellRange` objects. The top-left cell of each merged region retains the value; all others return `None`. This is exactly the right model for annotation-based rendering (e.g., `[merged 3×2]`) rather than silent data duplication.
- **Formula resolution.** When a workbook is opened with `data_only=True`, openpyxl reads the cached computed value (last saved by Excel) rather than the formula string. This is appropriate for RAG use: we want the data, not the formula expression.
- **Read-only mode.** `openpyxl.load_workbook(path, read_only=True)` uses a streaming SAX parser that is significantly more memory-efficient for large files. Since we only need to read, this should be the default.
- **Multi-sheet support.** `workbook.sheetnames` and iteration over `workbook.worksheets` give full access to all sheets. Each sheet can be processed independently and emitted as a separate `content_list` item.
- **Active maintenance.** openpyxl is actively maintained, has no binary C extensions (pure Python), and has zero system dependencies. This is important for the project's lightweight dependency philosophy.
- **No LibreOffice required.** Direct file parsing removes the subprocess dependency, eliminates the PDF conversion lossy path, and makes the parser portable to any Python 3.10+ environment.

**Known limitations:**

- `read_only=True` mode does not expose merged cell metadata — `worksheet.merged_cells` is unavailable in streaming mode. To handle merged cells, the workbook must be opened in standard (non-streaming) mode. For large files, this is a memory trade-off that should be surfaced in configuration (e.g., a `SPREADSHEET_MAX_SIZE_MB` threshold).
- `data_only=True` only returns the last cached value. If the spreadsheet was never saved after a formula edit, the cell may return `None`. This edge case should be handled gracefully by falling back to the formula string.
- openpyxl does not support `.xls` (legacy Excel 97-2003 binary format). This requires a separate library.

**Confidence: High.** openpyxl is the correct choice for `.xlsx`. No alternatives compete on the combination of merged-cell access, pure-Python portability, and zero system dependencies.

---

## Legacy Format Library: xlrd

**Install:** `pip install xlrd>=2.0.1`

**Rationale:**

xlrd is the only actively maintained Python library for reading `.xls` (BIFF8) format files. Important context: xlrd **2.0.0 dropped xlsx support** (released 2020) to focus exclusively on the legacy binary format. This is the correct version to use — do not use xlrd for xlsx files.

- **BIFF8 format coverage.** xlrd handles the Excel 97-2003 binary format that openpyxl cannot read.
- **Merged cell support.** `sheet.merged_cells` returns a list of `(row_lo, row_hi, col_lo, col_hi)` tuples. Coverage is equivalent to openpyxl for the annotation approach.
- **Formula values.** xlrd reads computed values by default (no formula expressions); there is no equivalent to openpyxl's `data_only=True` because the BIFF8 format stores values and formulas separately and xlrd always reads the value cell.
- **Stable, minimal API.** xlrd has been in maintenance mode since xlrd 2.x — no new features, but stable and reliable for the BIFF8 use case.

**Known limitations:**

- `.xls` files older than Excel 97 (BIFF5/BIFF4) are not supported. In practice, these are extremely rare in modern data pipelines. Graceful error handling with a fallback to the LibreOffice PDF path is appropriate.
- xlrd does not support `.xlsx` in version 2.x — routing logic must check file extension before selecting the library.
- xlrd is in maintenance mode. If it becomes unmaintained and a security issue surfaces, the fallback is always the LibreOffice PDF conversion path which already exists.

**Confidence: High.** xlrd is the only viable option for `.xls` without LibreOffice. The fallback to LibreOffice PDF conversion means that xlrd failure is non-fatal.

---

## What NOT to Use

### pandas

`pandas.read_excel()` is superficially appealing but wrong for this use case.

- **Heavy dependency chain.** pandas pulls in numpy, which is a compiled C extension (~30 MB installed). The project's dependency philosophy favors lightweight optional groups.
- **Merged cell handling is lossy.** `read_excel()` fills forward-filled values for merged cells by default, destroying the structural information. The `header` parameter requires manual tuning per file. There is no clean way to detect and annotate merged regions.
- **Opinionated dtype inference.** pandas aggressively infers column types (dates, booleans, floats), which can corrupt cell values for RAG purposes. A date cell that should read `"2024-01-15"` may become a `Timestamp` object.
- **No multi-sheet structural awareness.** While `sheet_name=None` returns all sheets, the sheet-level metadata (sheet index, sheet relationships) is not preserved in the output.

pandas would be the right tool if we were building an analysis pipeline. For structure-preserving extraction to markdown, it is the wrong abstraction.

### xlwings

`xlwings` requires a running Excel installation (Windows or macOS with Excel) and communicates via COM or the Excel scripting bridge. This is not portable, not suitable for server environments, and contradicts the project's zero-external-dependency goal for the spreadsheet parsing path.

### calamine (python-calamine)

`python-calamine` is a Python binding to the Rust `calamine` library. It is fast and handles both xlsx and xls formats. However:

- It requires a Rust-compiled binary extension, which adds build complexity and may break on unusual platforms or Python version combinations.
- Merged cell support as of the last reviewed version was incomplete — merged cell metadata was not exposed in the Python bindings.
- The library is younger and less battle-tested than openpyxl for production use cases.

If performance on very large xlsx files becomes a bottleneck (>50k rows), calamine could be reconsidered. For this milestone, the portability risk outweighs the performance benefit.

### pyxlsb

`pyxlsb` handles `.xlsb` (Excel Binary Workbook) format. This is a different format from `.xls`. xlsb files are uncommon in the wild and out of scope per PROJECT.md. Document this as a future consideration if user feedback indicates demand.

---

## Markdown Table Generation

No external library is needed for markdown table generation. The output format is straightforward:

```
| Header A | Header B | Header C |
|----------|----------|----------|
| value 1  | value 2  | value 3  |
```

A clean internal implementation under 20 lines handles column width normalization, cell escaping (pipe characters in values), and merged cell annotations. Using an external library like `tabulate` would add a dependency for trivial string formatting.

**Rationale for no external library:**
- The target format is fixed (GitHub Flavored Markdown tables)
- Cell values are already strings after openpyxl extraction
- Merged cell annotations (`[merged 3×2]`) require custom logic regardless
- Keeping it internal avoids a transitive dependency in the `spreadsheet` extras group

**Confidence: High.**

---

## Optional Dependency Group

Following the established pattern in `pyproject.toml`:

```toml
[project.optional-dependencies]
spreadsheet = [
    "openpyxl>=3.1.2",
    "xlrd>=2.0.1",
]
```

And in the `all` group:

```toml
all = [
    # ... existing entries ...
    "openpyxl>=3.1.2",
    "xlrd>=2.0.1",
]
```

**Installation:**
```bash
pip install "raganything[spreadsheet]"
```

**Rationale for bundling xlrd with openpyxl in one group:**
- Users who work with spreadsheets encounter both `.xlsx` and `.xls` files in practice. Splitting into separate groups (`xlsx` and `xls`) adds cognitive overhead for no real benefit.
- xlrd is tiny (~200 KB installed). The incremental cost of including it alongside openpyxl is negligible.
- The pattern matches the audio group, which bundles all three audio dependencies together.

**Confidence: High.**

---

## content_list Integration

The existing `TableModalProcessor` in `raganything/modalprocessors.py` already handles table content items. The spreadsheet parser must emit items in the exact format the processor expects:

```python
# Text block (sheet header / metadata)
{
    "type": "text",
    "text": "Sheet: Sheet1 (3 rows × 4 columns)",
    "page_idx": 0,  # sheet_idx for spreadsheets
}

# Table block (one per sheet)
{
    "type": "table",
    "table_body": "| Col A | Col B |\n|-------|-------|\n| val1  | val2  |",
    "table_caption": "Sheet1",
    "page_idx": 0,  # sheet_idx
}
```

The `page_idx` field maps sheet index to the existing positional concept. This preserves the multi-sheet ordering without schema changes.

**Confidence: High** — derived directly from `raganything/processor.py` lines 112-119 and `raganything/modalprocessors.py` `TableModalProcessor`.

---

## Summary Rationale

The recommended stack (`openpyxl` + `xlrd`) is prescriptive because:

1. **Correctness over convenience.** Direct library access gives full control over merged cell detection, formula value resolution, and sheet-level metadata. Higher-level wrappers (pandas) trade this control for ergonomics we do not need.
2. **Zero system dependencies.** Neither library requires any non-Python binary on the host. This removes the LibreOffice system package requirement for the xlsx/xls path.
3. **Minimal footprint.** openpyxl (~2 MB installed) and xlrd (~200 KB) are negligible additions to the optional dependency group.
4. **Established in the ecosystem.** Both libraries are used by pandas, Django, and major data tools as their underlying Excel engines — they are well-maintained and widely battle-tested.
5. **Clean fallback.** The existing LibreOffice PDF conversion path remains intact as a fallback for edge cases (corrupted files, unusual BIFF versions, xlsb). Direct parsing is the preferred path, not the only path.

---

*Research: 2026-02-20 | Model knowledge cutoff: August 2025 | Verify versions before shipping*
