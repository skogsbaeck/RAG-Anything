# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** Preserve structural integrity of tabular spreadsheet data for RAG knowledge graph ingestion
**Current focus:** Phase 2 in progress — parser-config integration

## Current Position

Phase: 2 of 3 (Parser-Config Integration)
Plan: 1 of 2 in current phase
Status: In progress
Last activity: 2026-02-21 — Completed 02-01-PLAN.md

Progress: [████████░░] 80%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: ~2 minutes
- Total execution time: ~7 minutes

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 - SpreadsheetParser Core | 3/3 | ~6 min | ~2 min |
| 2 - Parser-Config Integration | 1/2 | ~1 min | ~1 min |

**Recent Trend:**
- Last 5 plans: 01-01 (~1 min), 01-02 (~2 min), 01-03 (~3 min), 02-01 (~1 min)
- Trend: fast execution

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- openpyxl for xlsx, xlrd for xls — most mature pure-Python options; pandas explicitly ruled out
- Annotate merged cells with `[merged NxM]` rather than fill or ignore — preserves structure for LLM
- No external markdown table library — custom ~20-line renderer handles GFM output and pipe escaping
- LibreOffice fallback must remain and log at WARNING — silent fallback masks parser failures
- bool checked before int in format_cell_value — bool is subclass of int in Python
- datetime.datetime checked before datetime.date — datetime is subclass of date
- strip_empty_edges preserves leading rows/columns — A1 offset semantics locked
- worksheet typed as Any in build_merge_map — guarded import pattern, no module-level openpyxl
- Spreadsheet deps are optional — base install stays lightweight; users opt in with pip install raganything[spreadsheet]
- Both openpyxl and xlrd added to the all group so raganything[all] covers everything
- env var prefix RAG_ANYTHING_ for spreadsheet config fields — intentional divergence from existing unprefixed fields
- ImportError from SpreadsheetParser is a hard error (re-raised) — missing deps must not silently fall back
- SPREADSHEET_FORMATS separate from OFFICE_FORMATS — enables clean routing in parse_document()

### Pending Todos

- .gitignore has `test_*` pattern that is too broad — test files require `git add -f`; consider narrowing the pattern

### Blockers/Concerns

- Formula-None threshold (>10% triggers LibreOffice fallback) is a heuristic — validate against real samples in Phase 3
- xlrd legacy .xls fixture coverage may require synthetic files if real Excel 97 era files are hard to source
- .gitignore `test_*` pattern may cause issues for future test file commits

## Session Continuity

Last session: 2026-02-21
Stopped at: Completed 02-01-PLAN.md
Resume file: None
