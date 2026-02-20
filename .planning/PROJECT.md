# Direct Spreadsheet Parsing for RAG-Anything

## What This Is

A new parsing path for RAG-Anything that reads `.xlsx` and `.xls` files directly using `openpyxl`, bypassing the current LibreOffice-to-PDF conversion. It converts spreadsheet data into structured markdown tables and returns `content_list` items compatible with the existing LightRAG pipeline.

## Core Value

Preserve the structural integrity of tabular spreadsheet data — headers, data types, multi-sheet organization, and merged cell semantics — so the RAG knowledge graph captures what the data actually represents, not a lossy visual rendering.

## Requirements

### Validated

- ✓ xlsx/xls files can be ingested via LibreOffice PDF conversion — existing
- ✓ Processor routes files by extension to appropriate parser — existing
- ✓ content_list format accepted by LightRAG pipeline — existing
- ✓ Audio parser follows the same pattern (dedicated parser module + processor integration) — existing
- ✓ Optional dependency groups work via pyproject.toml extras — existing

### Active

- [ ] Direct xlsx/xls parsing with openpyxl (no LibreOffice needed)
- [ ] Multi-sheet workbook support — each sheet parsed independently
- [ ] Merged cell handling with annotations (e.g., `[merged 3×2]`)
- [ ] Formula cells resolved to computed values
- [ ] Markdown table output preserving headers, rows, and data types
- [ ] content_list integration matching existing processor contract
- [ ] Processor routing: try direct parse first, fall back to LibreOffice PDF path on failure
- [ ] Configuration options for spreadsheet parsing (enable/disable, sheet selection)
- [ ] Optional dependency group `spreadsheet` in pyproject.toml

### Out of Scope

- Google Sheets API integration — only handling exported .xlsx files, not live connections
- CSV/TSV parsing — different format, different parser, defer to future
- Cell styling/color extraction — not useful for RAG text content
- Chart/graph extraction from spreadsheets — complex, low value for text RAG
- Macro execution — security risk, not relevant to data extraction

## Context

- RAG-Anything is a multimodal RAG system wrapping LightRAG (lightrag-hku)
- The codebase uses a mixin architecture: ProcessorMixin, QueryMixin, BatchMixin composed into RAGAnything
- Parsers live in `raganything/parser.py` with a base Parser class
- The audio parser (`raganything/audio.py`) was recently added following the same pattern we'll use
- `content_list` is the key contract — list of dicts with `type` field routing to modal processors
- Tables already have a `TableModalProcessor` in `modalprocessors.py` that handles table content
- The processor in `processor.py` routes `.xls`/`.xlsx` to `parse_office_doc` (LibreOffice path) at line ~380
- openpyxl handles `.xlsx` natively; for `.xls` (legacy Excel), `xlrd` would be needed as a secondary dependency

## Constraints

- **Compatibility**: Must return content_list items in the exact format the existing processor and TableModalProcessor expect
- **Fallback**: LibreOffice PDF path must remain as fallback — direct parsing is preferred but not mandatory
- **Dependencies**: openpyxl as required dep in `spreadsheet` extras group; keep core install lightweight
- **Python**: 3.10+ (existing project constraint)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| openpyxl for xlsx parsing | Most mature Python xlsx library, read-only mode available, handles merged cells | — Pending |
| Annotate merged cells rather than fill or ignore | Gives LLM context about original structure without duplicating data | — Pending |
| Keep LibreOffice as fallback | Safety net for edge cases openpyxl can't handle | — Pending |
| Follow audio.py pattern (dedicated module) | Proven pattern in this codebase, clean separation | — Pending |

---
*Last updated: 2026-02-20 after initialization*
