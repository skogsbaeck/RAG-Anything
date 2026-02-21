# Phase 2: Parser + Config Integration - Research

**Researched:** 2026-02-21
**Domain:** MineruParser integration, RAGAnythingConfig, SpreadsheetParser wiring
**Confidence:** HIGH (all findings from direct codebase inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Fallback behavior**
- Auto fallback: if SpreadsheetParser throws any exception, fall back to LibreOffice PDF path automatically
- Log at WARNING level with filename + exception type (e.g. "Direct parse failed for report.xlsx (MergeError), falling back to LibreOffice")
- No fallback on empty result — zero content items is valid (workbook genuinely had no data)
- No formula-None threshold — trust data_only=True results as-is, don't second-guess

**Config flag design**
- `enable_direct_spreadsheet_parsing` lives in RAGAnython constructor (not env var)
- Default: True (direct parsing on by default)
- `max_rows_per_chunk` exposed at RAGAnything level, not just internal SpreadsheetConfig
- Env var prefix: `RAG_ANYTHING_` (e.g. `RAG_ANYTHING_DIRECT_SPREADSHEET`, `RAG_ANYTHING_SPREADSHEET_MAX_ROWS`)

**Error handling strategy**
- Missing openpyxl/xlrd = hard error (ImportError with helpful install message) — don't silently degrade
- Corrupted/password-protected files trigger fallback to LibreOffice (it might handle what openpyxl can't)
- Partial sheet failure: skip the bad sheet with WARNING, continue processing remaining sheets
- Content_list contract validation: assert in debug mode only (trust SpreadsheetParser in production)

**xlrd adapter approach**
- Single entry point: `parse_spreadsheet()` handles both .xls and .xlsx — SpreadsheetParser already dispatches by extension
- Missing xlrd for .xls file = hard error (ImportError), not fallback
- .xls testing deferred to Phase 3 E2E — Phase 2 tests focus on xlsx integration path

### Claude's Discretion
- xlrd date tuple → datetime conversion implementation details
- Debug assertion implementation (assert vs logging)
- Exact env var parsing logic
- How config flows from RAGAnything constructor down to SpreadsheetParser

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

## Summary

This phase wires the already-built `SpreadsheetParser` (in `raganything/spreadsheet.py`) into `MineruParser` via a new `parse_spreadsheet()` method, and adds two config flags to `RAGAnythingConfig` that control direct-parse behaviour. The integration follows the exact pattern already used by `parse_audio()` in `MineruParser`: guarded import at call time, a local config dataclass created from RAGAnythingConfig values, and a single return of a `content_list`.

The most important structural insight: `MineruParser` currently routes `.xls` and `.xlsx` through `parse_office_doc()` (LibreOffice path). Phase 2 splits this path — spreadsheet extensions go to the new `parse_spreadsheet()` method first, with `parse_office_doc()` as fallback. The split happens inside `parse_document()` in `MineruParser`, or optionally inside `ProcessorMixin.parse_document()` in `processor.py` (where the actual extension dispatch lives in the production pipeline).

**Primary recommendation:** Add `parse_spreadsheet()` to `MineruParser`, update the Office-format branch in `ProcessorMixin.parse_document()` to call `parse_spreadsheet()` for `.xls`/`.xlsx` when `enable_direct_spreadsheet_parsing=True`, and add two fields to `RAGAnythingConfig`.

---

## Codebase Architecture: What Exists

### File Map

| File | Role |
|------|------|
| `raganything/parser.py` | `Parser` base class + `MineruParser` + `DoclingParser` |
| `raganything/spreadsheet.py` | `SpreadsheetParser`, `SpreadsheetConfig` (Phase 1, done) |
| `raganything/audio.py` | `AudioProcessor`, `AudioConfig` — pattern to replicate |
| `raganything/config.py` | `RAGAnythingConfig` dataclass with `get_env_value()` fields |
| `raganything/processor.py` | `ProcessorMixin.parse_document()` — actual file-type dispatch |
| `raganything/raganything.py` | `RAGAnything` dataclass that holds `config` and `doc_parser` |

### MineruParser Class Structure (parser.py lines 573–1314)

```
MineruParser(Parser)
  __slots__ = ()
  logger = logging.getLogger(__name__)

  __init__(self) -> None                  # calls super().__init__()

  # Class methods (all @classmethod)
  _run_mineru_command(...)                # spawns subprocess
  _read_output_files(output_dir, file_stem, method)  # reads JSON + MD

  # Instance methods
  parse_pdf(pdf_path, output_dir, method, lang, **kwargs) -> List[Dict]
  parse_image(image_path, output_dir, lang, **kwargs) -> List[Dict]
  parse_office_doc(doc_path, output_dir, lang, **kwargs) -> List[Dict]
  parse_text_file(text_path, output_dir, lang, **kwargs) -> List[Dict]
  parse_audio(audio_path, output_dir, lang, whisper_model, device, **kwargs) -> List[Dict]
  parse_document(file_path, method, output_dir, lang, **kwargs) -> List[Dict]  # routes by ext
  check_installation() -> bool
```

`__slots__ = ()` is set — no instance dict. This means **no instance attributes can be added** to `MineruParser`. Config values must be passed as method parameters, not stored on `self`. This is how `parse_audio()` works: it receives `whisper_model` and `device` as parameters, not from `self.config`.

### parse_office_doc: The LibreOffice Path (parser.py lines 1108–1143)

```python
def parse_office_doc(self, doc_path, output_dir=None, lang=None, **kwargs):
    # Step 1: convert_office_to_pdf(doc_path, output_dir)  -> pdf_path (Path)
    # Step 2: self.parse_pdf(pdf_path, output_dir, lang, **kwargs) -> content_list
    # Wraps both in try/except, re-raises on any error
```

Key facts:
- `convert_office_to_pdf()` is a `@classmethod` on `Parser` (inherited), tries `libreoffice` then `soffice`
- Output PDF is placed in `output_dir / libreoffice_output/` (or alongside original if no output_dir)
- Returns `List[Dict[str, Any]]` — same shape as `parse_pdf()`
- Already handles `.xls` and `.xlsx` (LibreOffice supports both)

### parse_audio: The Pattern to Follow (parser.py lines 1179–1228)

```python
def parse_audio(self, audio_path, output_dir=None, lang=None,
                whisper_model="base", device="cpu", **kwargs):
    try:
        from raganything.audio import AudioProcessor, AudioConfig  # guarded import
    except ImportError:
        raise ImportError(
            "Audio support requires additional dependencies.\n"
            "Install with: pip install raganything[audio]\n"
            "Or manually: pip install faster-whisper librosa soundfile"
        )

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(...)

    self.logger.info(f"Transcribing audio file: {audio_path.name}")

    config = AudioConfig(
        language=lang if lang else "auto",
        whisper_model=whisper_model,
        device=device
    )

    transcription = AudioProcessor(config).transcribe(audio_path)

    self.logger.info(...)

    return [{
        'type': 'text',
        'text': transcription.text,
        'page_idx': 0,
        'metadata': {...}
    }]
```

Key pattern observations:
1. **Guarded import** at the top of the method — ImportError with helpful pip message
2. **Config constructed inline** from method parameters (not from `self.config` — MineruParser has no config)
3. **Single return** of a `content_list` (list of dicts)
4. **No fallback** in `parse_audio` itself — audio has no fallback path
5. The `output_dir` parameter is accepted but not used (audio doesn't write files) — this is fine

### ProcessorMixin.parse_document: Where Production Routing Happens (processor.py lines 280–468)

This is the real dispatch point in the production pipeline. NOT `MineruParser.parse_document()`.

```python
# Lines 380-398 — the current Office/HTML branch:
elif ext in [
    ".doc", ".docx", ".ppt", ".pptx",
    ".xls", ".xlsx",          # <-- spreadsheet hits here currently
    ".html", ".htm", ".xhtml",
]:
    self.logger.info("Detected Office or HTML document, using parser for Office/HTML...")
    content_list = await asyncio.to_thread(
        doc_parser.parse_office_doc,
        doc_path=file_path,
        output_dir=output_dir,
        **kwargs,
    )
```

For Phase 2, `.xls` and `.xlsx` must be split out of this branch and routed through `parse_spreadsheet()` first (with fallback to `parse_office_doc()`). There are two options:

**Option A:** Add spreadsheet routing inside `ProcessorMixin.parse_document()` — directly reads `self.config.enable_direct_spreadsheet_parsing`
**Option B:** Route `.xls`/`.xlsx` through `parse_spreadsheet()` in `MineruParser.parse_document()` — but config isn't available there

Option A is correct because `ProcessorMixin` has `self.config` (it's part of `RAGAnything`). Option B doesn't work — `MineruParser` has `__slots__ = ()` and no config.

### RAGAnythingConfig Pattern (config.py)

All fields use `get_env_value()` from `lightrag.utils`. Pattern:

```python
audio_language: str = field(default=get_env_value("AUDIO_LANGUAGE", "auto", str))
audio_whisper_model: str = field(default=get_env_value("AUDIO_WHISPER_MODEL", "base", str))
audio_device: str = field(default=get_env_value("AUDIO_DEVICE", "cpu", str))
enable_image_processing: bool = field(default=get_env_value("ENABLE_IMAGE_PROCESSING", True, bool))
```

- Env var names have NO prefix — just `AUDIO_LANGUAGE`, `ENABLE_IMAGE_PROCESSING`, etc.
- But the locked decision specifies prefix `RAG_ANYTHING_` — so new fields will use `RAG_ANYTHING_DIRECT_SPREADSHEET` and `RAG_ANYTHING_SPREADSHEET_MAX_ROWS`
- `get_env_value(env_var_name, default, type)` — the signature

The `__post_init__` handles legacy env var mapping. New fields don't need legacy handling.

### How Config Flows to MineruParser

`MineruParser` has `__slots__ = ()` — it carries zero state. Config flows as:

1. `RAGAnythingConfig` stores `enable_direct_spreadsheet_parsing` and `spreadsheet_max_rows_per_chunk`
2. `ProcessorMixin.parse_document()` reads `self.config.enable_direct_spreadsheet_parsing`
3. If True, calls `doc_parser.parse_spreadsheet(doc_path, output_dir, max_rows_per_chunk=self.config.spreadsheet_max_rows_per_chunk)`
4. `parse_spreadsheet()` on `MineruParser` receives `max_rows_per_chunk` as a parameter, constructs `SpreadsheetConfig(max_rows_per_chunk=...)`, creates `SpreadsheetParser(config)`, calls `parser.parse(file_path)`

This mirrors how audio config flows: `ProcessorMixin` extracts `audio_whisper_model` and `audio_device` from `self.config`, passes them to `doc_parser.parse_audio(whisper_model=..., device=...)`.

---

## Architecture Patterns

### Pattern 1: Guarded Import (parse_audio style)

```python
def parse_spreadsheet(
    self,
    file_path: Union[str, Path],
    output_dir: Optional[str] = None,
    lang: Optional[str] = None,
    max_rows_per_chunk: int = 150,
    **kwargs,
) -> List[Dict[str, Any]]:
    try:
        from raganything.spreadsheet import SpreadsheetParser, SpreadsheetConfig
    except ImportError:
        raise ImportError(
            "Spreadsheet support requires additional dependencies.\n"
            "Install with: pip install raganything[spreadsheet]\n"
            "Or manually: pip install openpyxl"
        )
    ...
```

Note: `SpreadsheetParser` is always importable (it's in the package), but openpyxl/xlrd are guarded inside `SpreadsheetParser._parse_xlsx()` and `_parse_xls()` — they raise ImportError when called on the relevant file type. The guarded import at the `parse_spreadsheet()` level therefore only needs to guard the SpreadsheetParser import (which should succeed), but the actual missing-dependency error will bubble up from SpreadsheetParser itself when `.parse()` is called on an xlsx/xls file.

Decision: The hard ImportError for missing openpyxl/xlrd is already handled inside `SpreadsheetParser`. `parse_spreadsheet()` just lets those errors propagate (they are NOT caught by the fallback — per the locked decision: missing openpyxl/xlrd = hard error, not fallback).

### Pattern 2: Fallback Flow

```python
def parse_spreadsheet(self, file_path, output_dir=None, lang=None,
                      max_rows_per_chunk=150, **kwargs):
    from raganything.spreadsheet import SpreadsheetParser, SpreadsheetConfig

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    config = SpreadsheetConfig(max_rows_per_chunk=max_rows_per_chunk)

    try:
        content_list = SpreadsheetParser(config).parse(file_path)
        return content_list
    except ImportError:
        # Missing openpyxl/xlrd = hard error, NOT fallback
        raise
    except Exception as exc:
        self.logger.warning(
            f"Direct parse failed for {file_path.name} "
            f"({type(exc).__name__}), falling back to LibreOffice"
        )
        return self.parse_office_doc(file_path, output_dir, lang, **kwargs)
```

The `except ImportError: raise` block ensures that missing-dep errors are not swallowed by the broad `except Exception` fallback. This matches the locked decision.

### Pattern 3: ProcessorMixin Routing Update

```python
# In ProcessorMixin.parse_document() — replace the current Office block:

elif ext in [".doc", ".docx", ".ppt", ".pptx",
             ".html", ".htm", ".xhtml"]:
    # Non-spreadsheet Office/HTML (unchanged)
    content_list = await asyncio.to_thread(
        doc_parser.parse_office_doc, doc_path=file_path,
        output_dir=output_dir, **kwargs,
    )

elif ext in [".xls", ".xlsx"]:
    self.logger.info("Detected spreadsheet, using direct parser...")
    if self.config.enable_direct_spreadsheet_parsing:
        content_list = await asyncio.to_thread(
            doc_parser.parse_spreadsheet,
            file_path=file_path,
            output_dir=output_dir,
            max_rows_per_chunk=self.config.spreadsheet_max_rows_per_chunk,
            **kwargs,
        )
    else:
        self.logger.info("Direct spreadsheet parsing disabled, using LibreOffice...")
        content_list = await asyncio.to_thread(
            doc_parser.parse_office_doc, doc_path=file_path,
            output_dir=output_dir, **kwargs,
        )
```

### Pattern 4: RAGAnythingConfig Fields

```python
# Spreadsheet Processing Configuration
# ---
enable_direct_spreadsheet_parsing: bool = field(
    default=get_env_value("RAG_ANYTHING_DIRECT_SPREADSHEET", True, bool)
)
"""Enable direct spreadsheet parsing without LibreOffice conversion."""

spreadsheet_max_rows_per_chunk: int = field(
    default=get_env_value("RAG_ANYTHING_SPREADSHEET_MAX_ROWS", 150, int)
)
"""Maximum rows per content_list chunk when parsing spreadsheets directly."""
```

### Recommended Project Structure Changes

```
raganything/
├── parser.py          # Add parse_spreadsheet() to MineruParser (~30 lines)
├── config.py          # Add 2 fields to RAGAnythingConfig
├── processor.py       # Split .xls/.xlsx out of Office branch (~12 lines)
├── spreadsheet.py     # UNCHANGED (Phase 1 complete)
└── audio.py           # Reference pattern (unchanged)

tests/
├── test_spreadsheet_parser.py   # Existing Phase 1 tests (unchanged)
├── test_spreadsheet_helpers.py  # Existing Phase 1 tests (unchanged)
└── test_parse_spreadsheet.py    # NEW: Phase 2 integration tests
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| xls/xlsx dispatch | Custom ext check | `SpreadsheetParser.parse()` already dispatches by extension | It's done in Phase 1 |
| Cell-type conversion | Custom date handling | `format_cell_value()` + `_read_xls_rows()` already handle all types | Done in Phase 1 |
| Merge annotation | Custom merge logic | `build_merge_map()` + `_render_sheet_to_markdown()` | Done in Phase 1 |
| Fallback subprocess | New LibreOffice caller | `self.parse_office_doc()` already exists | Reuse the existing method |

---

## Common Pitfalls

### Pitfall 1: MineruParser.__slots__ = ()

**What goes wrong:** Trying to store `self.config` or `self.enable_direct_spreadsheet_parsing` on a `MineruParser` instance will raise `AttributeError` at runtime because `__slots__ = ()` forbids instance attributes.

**Why it happens:** The class explicitly blocks `__dict__` creation for memory efficiency.

**How to avoid:** Pass all config values as method parameters to `parse_spreadsheet()`. Never store state on `MineruParser`. Config lives in `RAGAnythingConfig` and is extracted by `ProcessorMixin` before the call.

**Warning signs:** Any attempt to write `self.x = ...` inside a `MineruParser` method.

### Pitfall 2: Catching ImportError in the Fallback

**What goes wrong:** If the broad `except Exception` catches `ImportError` (from missing openpyxl/xlrd), the code silently falls back to LibreOffice, violating the locked decision that missing deps = hard error.

**Why it happens:** `ImportError` is a subclass of `Exception`.

**How to avoid:** Always re-raise `ImportError` before the general except clause — `except ImportError: raise` must appear before `except Exception as exc:`.

**Warning signs:** Any `except Exception` block that wraps a guarded import call without first re-raising ImportError.

### Pitfall 3: Wrong Dispatch Location

**What goes wrong:** Adding the `enable_direct_spreadsheet_parsing` check inside `MineruParser.parse_document()` instead of `ProcessorMixin.parse_document()`.

**Why it happens:** `MineruParser` has a `parse_document()` method (lines 1230–1280) that routes by extension. It's tempting to modify that.

**How to avoid:** `MineruParser.parse_document()` has no access to `RAGAnythingConfig`. The actual production pipeline uses `ProcessorMixin.parse_document()` (processor.py lines 280–468). That's where the extension dispatch with `asyncio.to_thread` happens. Modify THAT file.

**Warning signs:** Any code change in `MineruParser.parse_document()` that tries to read config.

### Pitfall 4: output_dir Handling in Fallback

**What goes wrong:** When falling back to `parse_office_doc()`, the `output_dir` and `**kwargs` (lang, etc.) must be passed through correctly. Dropping `**kwargs` would lose `lang` parameter.

**Why it happens:** It's easy to hardcode a simpler call.

**How to avoid:** Pass all original parameters: `self.parse_office_doc(file_path, output_dir, lang, **kwargs)`.

### Pitfall 5: processor.py Zero-Content Guard

**What goes wrong:** `ProcessorMixin.parse_document()` raises `ValueError("Parsing failed: No content was extracted")` when `len(content_list) == 0` (line 441). Per the locked decision, zero-content from SpreadsheetParser is valid (empty workbook). But the existing guard would reject it.

**Why it happens:** The guard was written for PDF/OCR workflows where zero content means MinerU failed.

**How to avoid:** Either (a) bypass the zero-content check for spreadsheet extensions, or (b) understand that zero-content for genuine empty workbooks is still valid business logic — the existing check would reject it. This requires a conditional in the post-parse validation or adjusting the check to only apply to non-spreadsheet paths.

This is a non-trivial implication. The planner must address it.

---

## Code Examples

### MineruParser.parse_spreadsheet() Skeleton

```python
# Source: direct codebase analysis of parse_audio() pattern (parser.py lines 1179-1228)
def parse_spreadsheet(
    self,
    file_path: Union[str, Path],
    output_dir: Optional[str] = None,
    lang: Optional[str] = None,
    max_rows_per_chunk: int = 150,
    **kwargs,
) -> List[Dict[str, Any]]:
    from raganything.spreadsheet import SpreadsheetParser, SpreadsheetConfig

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Spreadsheet file does not exist: {file_path}")

    self.logger.info(f"Parsing spreadsheet directly: {file_path.name}")

    config = SpreadsheetConfig(max_rows_per_chunk=max_rows_per_chunk)

    try:
        content_list = SpreadsheetParser(config).parse(file_path)
        self.logger.info(
            f"Direct parse complete: {len(content_list)} content blocks from {file_path.name}"
        )
        return content_list
    except ImportError:
        raise  # hard error — missing openpyxl/xlrd
    except Exception as exc:
        self.logger.warning(
            f"Direct parse failed for {file_path.name} "
            f"({type(exc).__name__}), falling back to LibreOffice"
        )
        return self.parse_office_doc(file_path, output_dir, lang, **kwargs)
```

### RAGAnythingConfig New Fields

```python
# Source: config.py pattern for audio fields (lines 39-47)

# Spreadsheet Processing Configuration
# ---
enable_direct_spreadsheet_parsing: bool = field(
    default=get_env_value("RAG_ANYTHING_DIRECT_SPREADSHEET", True, bool)
)
"""Enable direct spreadsheet parsing without LibreOffice conversion."""

spreadsheet_max_rows_per_chunk: int = field(
    default=get_env_value("RAG_ANYTHING_SPREADSHEET_MAX_ROWS", 150, int)
)
"""Maximum rows per content_list chunk when parsing spreadsheets directly."""
```

### ProcessorMixin.parse_document() Split

```python
# Source: processor.py lines 380-398 (current Office block — to be split)

# OLD (single block):
elif ext in [".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
             ".html", ".htm", ".xhtml"]:
    content_list = await asyncio.to_thread(
        doc_parser.parse_office_doc, doc_path=file_path, output_dir=output_dir, **kwargs
    )

# NEW (two blocks):
elif ext in [".doc", ".docx", ".ppt", ".pptx", ".html", ".htm", ".xhtml"]:
    self.logger.info("Detected Office or HTML document, using parser for Office/HTML...")
    content_list = await asyncio.to_thread(
        doc_parser.parse_office_doc, doc_path=file_path, output_dir=output_dir, **kwargs
    )

elif ext in [".xls", ".xlsx"]:
    self.logger.info("Detected spreadsheet file...")
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
            doc_parser.parse_office_doc, doc_path=file_path,
            output_dir=output_dir, **kwargs,
        )
```

### Test Pattern (following existing test_spreadsheet_parser.py style)

```python
# Source: tests/test_spreadsheet_parser.py pattern

import openpyxl
import pytest
from unittest.mock import patch, MagicMock
from raganything.parser import MineruParser


class TestParseSpreadsheet:
    def test_parse_xlsx_returns_content_list(self, tmp_path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws["A1"] = "Name"
        ws["B1"] = "Value"
        ws["A2"] = "Alice"
        ws["B2"] = 42
        path = tmp_path / "test.xlsx"
        wb.save(str(path))

        parser = MineruParser()
        result = parser.parse_spreadsheet(path)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["type"] == "table"
        assert "Name" in result[0]["table_body"]

    def test_fallback_on_exception(self, tmp_path):
        path = tmp_path / "corrupted.xlsx"
        path.write_bytes(b"not a real xlsx")

        parser = MineruParser()
        fallback_result = [{"type": "text", "text": "fallback", "page_idx": 0}]

        with patch.object(parser, "parse_office_doc", return_value=fallback_result) as mock_fallback:
            result = parser.parse_spreadsheet(path)

        mock_fallback.assert_called_once()
        assert result == fallback_result

    def test_missing_openpyxl_is_hard_error(self, tmp_path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws["A1"] = "test"
        path = tmp_path / "test.xlsx"
        wb.save(str(path))

        parser = MineruParser()
        with patch("raganything.spreadsheet.openpyxl", side_effect=ImportError("openpyxl")):
            # Should re-raise, not fall back to LibreOffice
            with pytest.raises(ImportError):
                parser.parse_spreadsheet(path)

    def test_disabled_flag_goes_to_libreoffice(self, tmp_path):
        # Tests belong in processor tests, not here — parse_spreadsheet
        # always attempts direct parse; the flag lives in ProcessorMixin
        pass
```

---

## Zero-Content Guard: Critical Finding

`ProcessorMixin.parse_document()` line 440–441:

```python
if len(content_list) == 0:
    raise ValueError("Parsing failed: No content was extracted")
```

Per the locked decision: "No fallback on empty result — zero content items is valid (workbook genuinely had no data)."

These two requirements conflict. The planner must decide how to resolve this:

**Option A:** Add spreadsheet-specific bypass: skip the zero-content check when `ext in [".xls", ".xlsx"]` and direct parsing was used.

**Option B:** Only apply the zero-content guard when content came from a MinerU/LibreOffice path (not SpreadsheetParser).

**Option C:** Return a minimal placeholder content item from SpreadsheetParser when the workbook has no visible data, so zero-content never occurs in practice. This contradicts the locked decision.

**Recommendation:** Option A — add `and ext not in [".xls", ".xlsx"]` (or a flag) to the zero-content guard. The guard is currently unconditional and was not designed for direct-parse paths.

---

## Sources

### Primary (HIGH confidence)
- Direct inspection of `/raganything/parser.py` — MineruParser class, parse_audio pattern
- Direct inspection of `/raganything/config.py` — RAGAnythingConfig field pattern with get_env_value
- Direct inspection of `/raganything/processor.py` — ProcessorMixin.parse_document() dispatch
- Direct inspection of `/raganything/spreadsheet.py` — SpreadsheetParser API (Phase 1)
- Direct inspection of `/raganything/audio.py` — AudioProcessor pattern
- Direct inspection of `/raganything/raganything.py` — RAGAnything constructor, __post_init__
- Direct inspection of `/tests/test_spreadsheet_parser.py` — test structure pattern
- Direct inspection of `/.planning/phases/02-parser-config-integration/02-CONTEXT.md` — locked decisions

---

## Metadata

**Confidence breakdown:**
- MineruParser structure: HIGH — read full class
- AudioProcessor pattern: HIGH — read full implementation
- Config field pattern: HIGH — read full config.py
- ProcessorMixin dispatch: HIGH — read relevant lines
- Zero-content guard conflict: HIGH — identified exact line
- Test pattern: HIGH — read existing test files

**Research date:** 2026-02-21
**Valid until:** Until parser.py or config.py are modified
