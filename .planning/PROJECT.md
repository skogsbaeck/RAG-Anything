# Direct Spreadsheet Parsing for RAG-Anything

## What This Is

A direct xlsx/xls parsing path for RAG-Anything that reads spreadsheet files using openpyxl (xlsx) and xlrd (xls), converting tabular data into structured GFM markdown tables compatible with the existing LightRAG pipeline. Includes merged cell annotation, hidden/empty sheet filtering, configurable row chunking, and automatic LibreOffice fallback for uncached-formula workbooks.

## Core Value

Preserve the structural integrity of tabular spreadsheet data — headers, data types, multi-sheet organization, and merged cell semantics — so the RAG knowledge graph captures what the data actually represents, not a lossy visual rendering.

## Requirements

### Validated

- ✓ xlsx/xls files can be ingested via LibreOffice PDF conversion — existing
- ✓ Processor routes files by extension to appropriate parser — existing
- ✓ content_list format accepted by LightRAG pipeline — existing
- ✓ Audio parser follows the same pattern (dedicated parser module + processor integration) — existing
- ✓ Optional dependency groups work via pyproject.toml extras — existing
- ✓ Direct xlsx/xls parsing with openpyxl (no LibreOffice needed) — v1
- ✓ Multi-sheet workbook support — each sheet parsed independently — v1
- ✓ Merged cell handling with annotations (e.g., `[merged 3×2]`) — v1
- ✓ Formula cells resolved to computed values — v1
- ✓ Markdown table output preserving headers, rows, and data types — v1
- ✓ content_list integration matching existing processor contract — v1
- ✓ Processor routing: try direct parse first, fall back to LibreOffice PDF path on failure — v1
- ✓ Configuration options for spreadsheet parsing (enable/disable, chunk size) — v1
- ✓ Optional dependency group `spreadsheet` in pyproject.toml — v1

### Active

(None — next milestone requirements to be defined)

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
- The audio parser (`raganything/audio.py`) was recently added following the same pattern
- `content_list` is the key contract — list of dicts with `type` field routing to modal processors
- Tables have a `TableModalProcessor` in `modalprocessors.py` that handles table content
- SpreadsheetParser lives in `raganything/spreadsheet.py` with optional deps (openpyxl, xlrd)
- ProcessorMixin routes `.xls`/`.xlsx` to `parse_spreadsheet()` (direct parser) with LibreOffice fallback
- v1 shipped: 1,892 lines Python across 7 files (production + tests), 73 tests passing

## Constraints

- **Compatibility**: Must return content_list items in the exact format the existing processor and TableModalProcessor expect
- **Fallback**: LibreOffice PDF path must remain as fallback — direct parsing is preferred but not mandatory
- **Dependencies**: openpyxl as required dep in `spreadsheet` extras group; keep core install lightweight
- **Python**: 3.10+ (existing project constraint)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| openpyxl for xlsx parsing | Most mature Python xlsx library, read-only mode available, handles merged cells | ✓ Good |
| xlrd for xls parsing | Only maintained Python library for legacy .xls format | ✓ Good |
| Annotate merged cells rather than fill or ignore | Gives LLM context about original structure without duplicating data | ✓ Good |
| Keep LibreOffice as fallback | Safety net for edge cases openpyxl can't handle | ✓ Good |
| Follow audio.py pattern (dedicated module) | Proven pattern in this codebase, clean separation | ✓ Good |
| ImportError is hard error (re-raised) | Missing deps should not silently fall back to LibreOffice | ✓ Good |
| Formula-None 10% threshold | Detect uncached formulas and auto-fallback to LibreOffice | ✓ Good |
| GFM separator detection requires dash | Distinguishes `|---|` separators from `| |` empty data rows | ✓ Good |
| Guarded imports inside method bodies | Optional deps stay optional; no module-level ImportError | ✓ Good |
| SPREADSHEET_FORMATS separate from OFFICE_FORMATS | Clean routing distinction in parse_document() | ✓ Good |

---
*Last updated: 2026-02-21 after v1 milestone*
