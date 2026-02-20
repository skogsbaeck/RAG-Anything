# Project Research Summary

**Project:** RAG-Anything — Direct Spreadsheet Parser (xlsx/xls)
**Domain:** Document parsing / RAG pipeline integration
**Researched:** 2026-02-20
**Confidence:** HIGH

## Executive Summary

RAG-Anything already supports tabular data ingestion via `TableModalProcessor`, but xlsx/xls files currently route through a lossy LibreOffice → PDF conversion path. The goal of this milestone is a direct parser that reads spreadsheets with openpyxl (xlsx) and xlrd (xls), producing `content_list` items of type `"table"` that slot into the existing pipeline without any schema changes downstream. This is a well-understood integration pattern — the audio transcription feature (commits 4e51e1e–a8e2e02) established an identical pattern: isolated module, guarded import, method on `MineruParser`, routing split in `ProcessorMixin`, config flags in `RAGAnythingConfig`.

The recommended stack is openpyxl `>=3.1.2` for xlsx and xlrd `>=2.0.1` for xls, both grouped as an optional `spreadsheet` dependency. No pandas, no external markdown library, no system binaries — the only required libraries are pure-Python and install in under 2 MB total. The minimum viable parser (table stakes features only) is approximately 5 hours of implementation; a full-featured parser including merged cell annotation, named ranges, and large-sheet chunking is approximately 14 hours total. The recommended first milestone lands in between at around 8 hours: table stakes plus sheet metadata captions, empty sheet skipping, and configurable hidden sheet handling.

The dominant risk is not technical but correctness-related: spreadsheets are structurally irregular in ways that break naive renderers. Merged cells return `None` for sibling cells, formula cells can have no cached value when saved outside Excel, ragged rows produce misaligned markdown, and sheet name collisions across workbooks corrupt knowledge graph entities. Every one of these pitfalls has a known, prescriptive prevention strategy — the research is thorough on mitigations. The fallback to LibreOffice PDF conversion must remain intact and its invocation must be logged explicitly, not silently swallowed.

---

## Key Findings

### Recommended Stack

openpyxl is the correct xlsx parser: pure Python, zero system dependencies, exposes merged cell metadata, supports streaming read-only mode for large files, and is used internally by pandas and Django — making it the most battle-tested xlsx library in the ecosystem. xlrd `>=2.0.1` is the only viable xls parser (note: 2.x dropped xlsx support intentionally — routing logic must inspect file extension before library selection). No external markdown table library is needed; a clean internal implementation under 20 lines handles GFM table output, pipe escaping, and merged cell annotations without transitive dependencies.

**Core technologies:**

- `openpyxl>=3.1.2`: xlsx parsing — only pure-Python option with full merged cell access and streaming support
- `xlrd>=2.0.1`: xls (BIFF8) parsing — only viable option for legacy format; stable maintenance-mode library
- No pandas: ruled out — lossy merged cell handling, heavy C extension dependency chain, opinionated type inference corrupts cell values
- No calamine: ruled out — Rust binary extension adds build complexity; merged cell metadata not fully exposed in Python bindings
- Internal markdown renderer: no external library needed; custom logic handles merged cell annotations regardless

**Optional dependency group:**

```toml
[project.optional-dependencies]
spreadsheet = ["openpyxl>=3.1.2", "xlrd>=2.0.1"]
```

### Expected Features

**Must have (table stakes) — ~5h total:**

- Multi-sheet workbook traversal — missing this silently drops entire sheets from the knowledge graph
- Cell value type coercion (`_coerce_cell` helper) — raw Python types (`datetime`, `bool`, `None`) corrupt markdown without explicit handling
- Formula value extraction via `data_only=True` — formula strings have no semantic value in RAG; cached computed values are required
- Empty row and column stripping — `ws.max_row`/`ws.max_column` are unreliable; scan actual data extent to avoid sparse empty-cell tables
- Markdown table serialisation — fixed GFM format; no padding needed for RAG (LLM is indifferent to visual alignment)
- `content_list` item structure compliance — `type`, `table_body` (str), `table_caption` (list), `table_footnote` (list), `page_idx` must match exactly

**Should have (differentiators) — adds ~3–4h to reach recommended ~8h milestone:**

- Merged cell annotation — primary structural signal in spreadsheets; losing it collapses hierarchical headers into flat data
- Sheet-level metadata as caption (including workbook filename prefix) — prevents entity name collisions across multi-document batches
- Empty sheet skipping with DEBUG log — avoids empty `content_list` items that waste embedding calls
- Configurable hidden sheet handling (`SKIP_HIDDEN_SHEETS`, default `True`) — hidden sheets often contain intermediate calculation data

**Defer to later iteration:**

- Named range extraction (~2h) — semantically valuable but not required for baseline correctness
- Large sheet chunking (~3h) — important for sheets >100 rows but adds complexity; acceptable to defer if row truncation is in place as a guard
- Cross-sheet context preamble — desirable for retrieval quality but not a blocking concern for v1

**Anti-features (deliberately excluded):**

- Cell styling extraction (colors, fonts) — no semantic value in text-based RAG
- Chart/embedded image extraction — LibreOffice PDF fallback already handles this via `ImageModalProcessor`
- Formula string preservation — formula text is implementation detail, not knowledge; always use `data_only=True`
- Pivot table reconstruction — redundant view of source data; LibreOffice fallback produces rendered version
- Automatic header detection heuristics — fails unpredictably on edge cases; first non-empty row as header is sufficient

### Architecture Approach

The integration follows the exact pattern established by the audio transcription feature. A new `SpreadsheetParser` class lives in `raganything/spreadsheet.py` with a single `parse(file_path, ...) -> List[Dict]` method — pure parsing, no LightRAG dependency, no LLM calls. `MineruParser` in `parser.py` gains a `parse_spreadsheet()` method with a guarded import and fallback to `parse_office_doc`. `ProcessorMixin` in `processor.py` splits `.xls`/`.xlsx` out of the generic Office branch into their own routing branch. `RAGAnythingConfig` gains two new env-var-backed fields. `TableModalProcessor` and `utils.py` require zero changes — the `"type": "table"` reuse is the key architectural decision that eliminates downstream coupling.

**Major components:**

1. `raganything/spreadsheet.py` (new) — `SpreadsheetParser`: isolated xlsx/xls → markdown table string conversion; no external dependencies except openpyxl/xlrd
2. `raganything/parser.py` (modified) — `MineruParser.parse_spreadsheet()`: guarded import, fallback trigger, routing from `parse_document()`
3. `raganything/config.py` (modified) — `enable_direct_spreadsheet_parsing` bool, `spreadsheet_max_rows_per_sheet` int
4. `raganything/processor.py` (modified) — `ProcessorMixin`: split `.xls`/`.xlsx` into own branch, read config flag
5. `raganything/modalprocessors.py` (unchanged) — `TableModalProcessor` already accepts markdown `table_body` strings

**Data flow:**

```
process_document_complete("report.xlsx")
  → ProcessorMixin._parse_document()        [routing on ext + config flag]
    → MineruParser.parse_spreadsheet()      [guarded import, fallback on error]
      → SpreadsheetParser.parse()           [openpyxl/xlrd → List[Dict]]
        → per sheet: markdown table string
        → {"type": "table", "table_body": md, "table_caption": [...], ...}
  → separate_content(content_list)          [utils.py — routes on "type"]
    → TableModalProcessor.process_modal_item()
      → LLM entity extraction → LightRAG KG
```

### Critical Pitfalls

1. **Merged cell data loss (P1)** — openpyxl returns `None` for all sibling cells in merged regions. Build a merge map from `ws.merged_cells.ranges` before iterating; annotate anchor cells with `[merged NxM]`, render siblings as empty. Never iterate raw cells without resolving the merge map first.

2. **Formula cells returning None (P2)** — `data_only=True` reads cached values only; files saved outside Excel (Google Sheets exports, LibreOffice saves) may have `None` in all formula cells. Load with `data_only=True` always; annotate uncached formula cells as `[formula: no cached value]` rather than silently dropping; trigger LibreOffice fallback if >10% of non-empty cells have no cached value.

3. **Content list contract mismatch (P10)** — `TableModalProcessor` requires `table_caption` and `table_footnote` as `list[str]`, not bare strings; `table_body` must be a non-empty string. A type mismatch causes silent empty-table entities in the knowledge graph with no error during ingestion. Write a contract validation function and assert field types in tests, not just field names.

4. **Ragged table rows breaking markdown (P3 + P8)** — Sheets have rows of different lengths; cell content contains pipe characters and newlines. Before rendering, normalize all rows to `max_col` width. Apply a `sanitize_cell()` function that escapes `|`, strips embedded newlines, and removes leading/trailing whitespace — called consistently, never inline.

5. **Silent fallback masking parse failures (P12)** — If the direct parser fails silently and always triggers the LibreOffice fallback, the feature effectively does not run in production. Log fallback invocations at `WARNING` level with the filename and exception. In tests, explicitly assert that a valid `.xlsx` fixture uses the direct parser (mock LibreOffice and assert it was NOT called).

6. **Sheet name collisions in batch ingestion (P11)** — Generic sheet names ("Summary", "Data", "Sheet1") from different workbooks produce merged knowledge graph entities. Always prefix `table_caption` with the workbook filename stem: `[f"{workbook_filename} — {sheet_name}"]`.

---

## Implications for Roadmap

The architecture research explicitly provides a 5-phase build order with clear dependency boundaries. This maps cleanly to a roadmap.

### Phase 1: SpreadsheetParser Core Module

**Rationale:** Zero coupling to the rest of the codebase — can be built, tested, and validated in complete isolation. All downstream phases depend on this module being correct.
**Delivers:** `raganything/spreadsheet.py` with `SpreadsheetParser.parse()` covering all table stakes features plus merged cell annotation and sheet metadata captioning.
**Addresses features:** Multi-sheet traversal, type coercion, formula value extraction, empty row/col stripping, markdown serialisation, merged cell annotation, sheet metadata caption, empty sheet skipping, hidden sheet config.
**Avoids pitfalls:** P1 (merge map), P2 (data_only), P3 (ragged rows), P6 (empty sheets), P7 (type coercion), P8 (markdown escaping), P11 (filename-prefixed captions).
**Research flag:** Standard patterns — openpyxl API is well-documented; no additional research needed.

### Phase 2: MineruParser Integration

**Rationale:** Wires `SpreadsheetParser` into the existing parser without touching routing or config. Follows audio parser pattern exactly — low risk, well-understood.
**Delivers:** `MineruParser.parse_spreadsheet()` method with guarded import, xlrd fallback adapter, and routing update in `parse_document()`.
**Addresses features:** xls legacy support (xlrd adapter), fallback to LibreOffice PDF path.
**Avoids pitfalls:** P9 (xlrd date mode), P12 (explicit fallback logging), P2 (fallback trigger on high None-cell ratio).
**Research flag:** Standard patterns — mirrors `parse_audio` implementation directly.

### Phase 3: Config Additions

**Rationale:** Pure config expansion with no behavior change — low risk, keeps concerns separated.
**Delivers:** `enable_direct_spreadsheet_parsing` bool and `spreadsheet_max_rows_per_sheet` int in `RAGAnythingConfig` with env var support and defaults.
**Research flag:** Standard patterns — existing `get_env_value` helper already supports bool and int parsing.

### Phase 4: ProcessorMixin Routing

**Rationale:** Final integration step — splits `.xls`/`.xlsx` out of the generic Office branch and connects the config flag. This is the last change before end-to-end testing.
**Delivers:** Updated `ProcessorMixin._parse_document()` routing `.xls`/`.xlsx` to `parse_spreadsheet` when `enable_direct_spreadsheet_parsing=True`, otherwise retaining existing `parse_office_doc` path.
**Avoids pitfalls:** P10 (contract validation in integration tests), P12 (routing tests assert direct parser is called for valid xlsx).
**Research flag:** Standard patterns — routing logic is trivial; integration test coverage is the only complexity.

### Phase 5: End-to-End Validation

**Rationale:** Confirms the full pipeline works with real xlsx fixtures containing multiple sheets, unicode, numeric types, merged cells, and large row counts.
**Delivers:** `examples/spreadsheet_test.py`, test fixtures, and verification that `TableModalProcessor` correctly receives and processes all content items.
**Research flag:** No research needed — functional validation against real files.

### Phase Ordering Rationale

- Phase 1 first because `SpreadsheetParser` has no dependencies on the rest of the codebase; isolated development and testing reduces risk.
- Phase 2 before Phase 4 because `MineruParser.parse_spreadsheet()` must exist before `ProcessorMixin` can call it.
- Phase 3 (config) can be developed in parallel with Phase 2 — they are independent.
- Phase 4 is intentionally last among code changes because it activates the feature in the live routing path.
- This ordering mirrors the audio feature's build sequence and the explicit recommendation in ARCHITECTURE.md.

### Research Flags

Phases with standard patterns (skip `/gsd:research-phase`):

- **Phase 1:** openpyxl API is thoroughly documented; merge map and type coercion patterns are fully specified in PITFALLS.md.
- **Phase 2:** Mirrors `parse_audio` pattern directly; xlrd API differences are fully documented in PITFALLS.md P9.
- **Phase 3:** Existing `get_env_value` helper already handles bool/int; no new patterns.
- **Phase 4:** Trivial routing split; no novel patterns.
- **Phase 5:** Functional validation; no research needed.

No phases require additional research — the combined research files cover all implementation decisions with high confidence.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | openpyxl and xlrd are the established choices; alternatives evaluated and rejected with clear rationale; version constraints verified against library changelogs |
| Features | HIGH | Feature set derived directly from the existing `content_list` contract and `TableModalProcessor` API; table stakes are unambiguous; differentiator scoping is well-reasoned |
| Architecture | HIGH | Pattern is already proven in this codebase (audio feature); component boundaries, data flow, and build order are fully specified with concrete file/line references |
| Pitfalls | HIGH | 12 distinct pitfalls with concrete prevention code snippets; each mapped to a build phase; all grounded in openpyxl/xlrd behavior, not speculation |

**Overall confidence: HIGH**

### Gaps to Address

- **Large sheet chunking strategy:** The research recommends deferring this but notes it is important for sheets with >100 rows. During Phase 1 implementation, establish the `spreadsheet_max_rows_per_sheet` truncation guard. If user feedback indicates datasets with large sheets are common, prioritize the chunking feature in the next iteration.

- **xlrd fixture coverage:** PITFALLS.md P9 flags that xlrd date handling requires `workbook.datemode` and that some legacy `.xls` files raise `XLRDError`. Test fixtures for Excel 97-era files may be hard to source. Acceptable to use synthetic xlrd fixture files; document which BIFF versions are covered by tests.

- **Google Sheets exports and formula None values:** P2 identifies that files saved outside Excel commonly have no formula cache. The >10% threshold for triggering LibreOffice fallback is a heuristic — validate this threshold against real-world samples during Phase 5 end-to-end testing.

---

## Sources

### Primary (HIGH confidence)

- openpyxl official documentation — merged cells API, `data_only` mode, read-only streaming, sheet state
- xlrd 2.x changelog — confirms xlsx support removal, BIFF8 coverage, datemode behavior
- RAG-Anything codebase: `raganything/modalprocessors.py`, `raganything/processor.py` lines 978-990, `raganything/parser.py` (audio pattern) — ground truth for content_list contract and routing patterns
- RAG-Anything git history (commits 4e51e1e–a8e2e02) — audio parser integration as architectural precedent

### Secondary (MEDIUM confidence)

- Community knowledge: pandas `read_excel` merged cell behavior and forward-fill defaults
- Community knowledge: calamine Python bindings merged cell coverage limitations

### Tertiary (LOW confidence)

- The >10% formula-None threshold for LibreOffice fallback trigger is a heuristic derived from reasoning, not empirical measurement — validate during end-to-end testing.

---

*Research completed: 2026-02-20*
*Ready for roadmap: yes*
