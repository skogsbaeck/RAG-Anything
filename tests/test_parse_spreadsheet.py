"""
Integration tests for MineruParser.parse_spreadsheet() and RAGAnythingConfig
spreadsheet fields.

Uses real xlsx fixtures created via openpyxl in tmp_path.
"""

import logging
from unittest.mock import patch, MagicMock

import openpyxl
import pytest

from raganything.config import RAGAnythingConfig
from raganything.parser import MineruParser
from raganything.spreadsheet import SpreadsheetConfig, SpreadsheetParser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_xlsx(tmp_path):
    """Small xlsx with headers and two data rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventory"
    ws["A1"] = "Product"
    ws["B1"] = "Quantity"
    ws["A2"] = "Widget"
    ws["B2"] = 10
    ws["A3"] = "Gadget"
    ws["B3"] = 5
    path = tmp_path / "inventory.xlsx"
    wb.save(str(path))
    return path


# ---------------------------------------------------------------------------
# TestParseSpreadsheet
# ---------------------------------------------------------------------------


class TestParseSpreadsheet:
    def test_parse_xlsx_returns_content_list(self, simple_xlsx):
        result = MineruParser().parse_spreadsheet(simple_xlsx)

        assert isinstance(result, list)
        assert len(result) >= 1
        first = result[0]
        assert first["type"] == "table"
        assert "Product" in first["table_body"]

    def test_fallback_on_parse_exception(self, tmp_path, caplog):
        corrupted = tmp_path / "corrupted.xlsx"
        corrupted.write_bytes(b"not a real xlsx")

        fallback = [{"type": "text", "text": "fallback"}]
        parser = MineruParser()

        with patch.object(parser, "parse_office_doc", return_value=fallback) as mock_fallback:
            with caplog.at_level(logging.WARNING):
                result = parser.parse_spreadsheet(corrupted)

        mock_fallback.assert_called_once()
        assert result == fallback
        assert "corrupted.xlsx" in caplog.text
        # exception type name should appear in the warning
        assert any(
            "corrupted.xlsx" in r.message for r in caplog.records if r.levelno == logging.WARNING
        )

    def test_import_error_is_not_caught_by_fallback(self, simple_xlsx):
        parser = MineruParser()

        with patch.object(
            SpreadsheetParser,
            "parse",
            side_effect=ImportError("No module named 'openpyxl'"),
        ):
            with patch.object(parser, "parse_office_doc") as mock_fallback:
                with pytest.raises(ImportError):
                    parser.parse_spreadsheet(simple_xlsx)

        mock_fallback.assert_not_called()

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            MineruParser().parse_spreadsheet(tmp_path / "nonexistent.xlsx")

    def test_max_rows_flows_to_config(self, simple_xlsx):
        captured_config: list[SpreadsheetConfig] = []

        original_init = SpreadsheetParser.__init__

        def capturing_init(self, config=None):
            captured_config.append(config)
            original_init(self, config)

        with patch.object(SpreadsheetParser, "__init__", capturing_init):
            MineruParser().parse_spreadsheet(simple_xlsx, max_rows_per_chunk=50)

        assert len(captured_config) == 1
        assert captured_config[0].max_rows_per_chunk == 50

    def test_xls_extension_routes_to_parse_spreadsheet(self, tmp_path):
        """Verify .xls extension flows through parse_spreadsheet -> SpreadsheetParser.

        This is a routing test only — xlrd E2E coverage is deferred to Phase 3.
        """
        xls_path = tmp_path / "test.xls"
        xls_path.write_bytes(b"placeholder")

        valid_result = [{"type": "table", "table_body": "| A | B |\n| --- | --- |\n| 1 | 2 |", "table_caption": ["test"], "page_idx": 0}]

        with patch.object(SpreadsheetParser, "parse", return_value=valid_result) as mock_parse:
            result = MineruParser().parse_spreadsheet(xls_path)

        mock_parse.assert_called_once()
        assert result == valid_result


# ---------------------------------------------------------------------------
# TestRAGAnythingConfigSpreadsheet
# ---------------------------------------------------------------------------


class TestRAGAnythingConfigSpreadsheet:
    def test_default_values(self):
        config = RAGAnythingConfig()

        assert config.enable_direct_spreadsheet_parsing is True
        assert config.spreadsheet_max_rows_per_chunk == 150
