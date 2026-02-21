# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** Preserve structural integrity of tabular spreadsheet data for RAG knowledge graph ingestion
**Current focus:** Phase 3 complete — all plans done

## Current Position

Phase: 3 of 3 (Routing End-to-End) — COMPLETE
Plan: 2 of 2 in Phase 3
Status: Plan 03-02 complete — E2E test suite in place, all Phase 3 success criteria proven
Last activity: 2026-02-21 — Completed 03-02-PLAN.md

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: ~2 minutes
- Total execution time: ~13 minutes

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 - SpreadsheetParser Core | 3/3 | ~6 min | ~2 min |
| 2 - Parser-Config Integration | 2/2 | ~3 min | ~1.5 min |
| 3 - Routing End-to-End | 2/2 | ~4 min | ~2 min |

**Recent Trend:**
- Last 5 plans: 02-01 (~1 min), 02-02 (~2 min), 03-01 (~2 min), 03-02 (~2 min)
- Trend: fast execution, consistent

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
- is_direct_spreadsheet flag is True even when parse_spreadsheet() internally falls back to LibreOffice — guard bypassed for both internal paths
- _StubProcessor duck-typing approach for routing tests — avoids full RAGAnything/LightRAG stack instantiation
- _FORMULA_NONE_THRESHOLD = 0.10 — 10% empty-cell ratio triggers LibreOffice fallback; validated in 03-02
- GFM separator detection requires at least one dash — distinguishes |---| separator rows from | | empty data rows in table_body parsing
- Patch SpreadsheetParser at raganything.spreadsheet (not raganything.parser) — local import pattern; parser module has no direct attribute
- sys.modules[module]=None for ImportError simulation — cleanest way to intercept local from-import, restore in finally

### Pending Todos

- .gitignore has `test_*` pattern that is too broad — test files require `git add -f`; consider narrowing the pattern

### Blockers/Concerns

None — all phases complete.

## Session Continuity

Last session: 2026-02-21
Stopped at: Completed 03-02-PLAN.md (all phases complete)
Resume file: None
