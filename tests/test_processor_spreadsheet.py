"""
Processor routing tests for spreadsheet dispatch in ProcessorMixin.parse_document().

These tests mock asyncio.to_thread to capture which parser method is dispatched
to for .xls/.xlsx files depending on config.enable_direct_spreadsheet_parsing.
"""

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raganything.config import RAGAnythingConfig


# ---------------------------------------------------------------------------
# Minimal stub that exercises the routing logic from ProcessorMixin
# without instantiating the full RAGAnything/LightRAG stack.
# ---------------------------------------------------------------------------

class _StubProcessor:
    """
    Minimal stub that replicates parse_document routing logic.

    Uses the real ProcessorMixin.parse_document() by duck-typing the required
    attributes (config, logger, parse_cache) so we can invoke it directly.
    """

    def __init__(self, config: RAGAnythingConfig):
        self.config = config
        self.logger = logging.getLogger("stub")
        self.parse_cache = None  # disables cache branch

    # Bind the real parse_document from ProcessorMixin
    from raganything.processor import ProcessorMixin
    parse_document = ProcessorMixin.parse_document
    _generate_cache_key = ProcessorMixin._generate_cache_key
    _get_cached_result = ProcessorMixin._get_cached_result
    _generate_content_based_doc_id = ProcessorMixin._generate_content_based_doc_id
    _store_cached_result = ProcessorMixin._store_cached_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_file(tmp_path: Path, ext: str) -> Path:
    """Create a zero-byte file with the given extension so Path.exists() is True."""
    f = tmp_path / f"sample{ext}"
    f.write_bytes(b"")
    return f


def _stub(config: RAGAnythingConfig) -> _StubProcessor:
    return _StubProcessor(config)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestProcessorSpreadsheetRouting:

    def test_xlsx_routes_to_parse_spreadsheet_when_enabled(self, tmp_path):
        """parse_document dispatches to parse_spreadsheet for .xlsx when direct parsing is enabled."""
        config = RAGAnythingConfig(enable_direct_spreadsheet_parsing=True)
        processor = _stub(config)
        xlsx_path = _make_fake_file(tmp_path, ".xlsx")

        content_stub = [{"type": "text", "text": "data"}]
        called_with_fn = []

        async def fake_to_thread(fn, **kwargs):
            called_with_fn.append(fn)
            return content_stub

        with patch("asyncio.to_thread", side_effect=fake_to_thread):
            result = asyncio.get_event_loop().run_until_complete(
                processor.parse_document(str(xlsx_path))
            )

        assert len(called_with_fn) == 1
        assert called_with_fn[0].__name__ == "parse_spreadsheet"

    def test_xlsx_routes_to_parse_office_doc_when_disabled(self, tmp_path):
        """parse_document dispatches to parse_office_doc for .xlsx when direct parsing is disabled."""
        config = RAGAnythingConfig(enable_direct_spreadsheet_parsing=False)
        processor = _stub(config)
        xlsx_path = _make_fake_file(tmp_path, ".xlsx")

        content_stub = [{"type": "text", "text": "data"}]
        called_with_fn = []

        async def fake_to_thread(fn, **kwargs):
            called_with_fn.append(fn)
            return content_stub

        with patch("asyncio.to_thread", side_effect=fake_to_thread):
            asyncio.get_event_loop().run_until_complete(
                processor.parse_document(str(xlsx_path))
            )

        assert len(called_with_fn) == 1
        assert called_with_fn[0].__name__ == "parse_office_doc"

    def test_xls_routes_same_as_xlsx(self, tmp_path):
        """parse_document dispatches to parse_spreadsheet for .xls (same as .xlsx)."""
        config = RAGAnythingConfig(enable_direct_spreadsheet_parsing=True)
        processor = _stub(config)
        xls_path = _make_fake_file(tmp_path, ".xls")

        content_stub = [{"type": "text", "text": "data"}]
        called_with_fn = []

        async def fake_to_thread(fn, **kwargs):
            called_with_fn.append(fn)
            return content_stub

        with patch("asyncio.to_thread", side_effect=fake_to_thread):
            asyncio.get_event_loop().run_until_complete(
                processor.parse_document(str(xls_path))
            )

        assert len(called_with_fn) == 1
        assert called_with_fn[0].__name__ == "parse_spreadsheet"

    def test_docx_still_routes_to_office_doc(self, tmp_path):
        """parse_document still dispatches to parse_office_doc for .docx (unaffected by spreadsheet split)."""
        config = RAGAnythingConfig(enable_direct_spreadsheet_parsing=True)
        processor = _stub(config)
        docx_path = _make_fake_file(tmp_path, ".docx")

        content_stub = [{"type": "text", "text": "data"}]
        called_with_fn = []

        async def fake_to_thread(fn, **kwargs):
            called_with_fn.append(fn)
            return content_stub

        with patch("asyncio.to_thread", side_effect=fake_to_thread):
            asyncio.get_event_loop().run_until_complete(
                processor.parse_document(str(docx_path))
            )

        assert len(called_with_fn) == 1
        assert called_with_fn[0].__name__ == "parse_office_doc"

    def test_zero_content_allowed_for_direct_spreadsheet(self, tmp_path):
        """Empty content_list does NOT raise ValueError when direct spreadsheet parsing is enabled."""
        config = RAGAnythingConfig(enable_direct_spreadsheet_parsing=True)
        processor = _stub(config)
        xlsx_path = _make_fake_file(tmp_path, ".xlsx")

        async def fake_to_thread(fn, **kwargs):
            return []  # empty workbook

        with patch("asyncio.to_thread", side_effect=fake_to_thread):
            # Should not raise
            content_list, doc_id = asyncio.get_event_loop().run_until_complete(
                processor.parse_document(str(xlsx_path))
            )

        assert content_list == []

    def test_zero_content_raises_for_disabled_spreadsheet(self, tmp_path):
        """Empty content_list from the LibreOffice path (disabled direct) raises ValueError."""
        config = RAGAnythingConfig(enable_direct_spreadsheet_parsing=False)
        processor = _stub(config)
        xlsx_path = _make_fake_file(tmp_path, ".xlsx")

        async def fake_to_thread(fn, **kwargs):
            return []

        with patch("asyncio.to_thread", side_effect=fake_to_thread):
            with pytest.raises(ValueError, match="No content was extracted"):
                asyncio.get_event_loop().run_until_complete(
                    processor.parse_document(str(xlsx_path))
                )

    def test_max_rows_passed_from_config(self, tmp_path):
        """spreadsheet_max_rows_per_chunk from config flows through to parse_spreadsheet call."""
        config = RAGAnythingConfig(
            enable_direct_spreadsheet_parsing=True,
            spreadsheet_max_rows_per_chunk=75,
        )
        processor = _stub(config)
        xlsx_path = _make_fake_file(tmp_path, ".xlsx")

        content_stub = [{"type": "text", "text": "data"}]
        captured_kwargs = {}

        async def fake_to_thread(fn, **kwargs):
            captured_kwargs.update(kwargs)
            return content_stub

        with patch("asyncio.to_thread", side_effect=fake_to_thread):
            asyncio.get_event_loop().run_until_complete(
                processor.parse_document(str(xlsx_path))
            )

        assert captured_kwargs.get("max_rows_per_chunk") == 75

    def test_zero_content_from_internal_fallback_allowed(self, tmp_path):
        """
        When direct parsing is enabled and parse_spreadsheet() internally falls
        back to LibreOffice (which also returns empty), the zero-content guard is
        still bypassed.

        Design decision: if SpreadsheetParser failed AND the internal LibreOffice
        fallback within parse_spreadsheet() also returned nothing, the workbook is
        genuinely unparseable. Raising ValueError here would not help the caller —
        there is no content to extract. Returning empty content_list signals this
        gracefully, allowing the caller to handle it (e.g., skip, log, or store
        an empty entry).

        is_direct_spreadsheet is True whenever config enables direct parsing,
        regardless of what parse_spreadsheet() does internally.
        """
        config = RAGAnythingConfig(enable_direct_spreadsheet_parsing=True)
        processor = _stub(config)
        xlsx_path = _make_fake_file(tmp_path, ".xlsx")

        async def fake_to_thread(fn, **kwargs):
            # Simulates parse_spreadsheet() falling back to LibreOffice internally
            # and both returning empty — the real function swallows the error and
            # returns [] from the internal LibreOffice path.
            return []

        with patch("asyncio.to_thread", side_effect=fake_to_thread):
            # Must NOT raise — empty result from internal fallback is acceptable
            content_list, doc_id = asyncio.get_event_loop().run_until_complete(
                processor.parse_document(str(xlsx_path))
            )

        assert content_list == []
