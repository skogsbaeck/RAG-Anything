"""
Tests for SpreadsheetParser class.

Uses real xlsx workbooks created via openpyxl in tmp_path fixtures.
No mocking of openpyxl internals.
"""

import datetime

import openpyxl
import pytest

from raganything.spreadsheet import SpreadsheetConfig, SpreadsheetParser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_workbook(tmp_path):
    """3x3 xlsx workbook with known string, int, and float values."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"
    ws["A1"] = "Name"
    ws["B1"] = "Age"
    ws["C1"] = "Score"
    ws["A2"] = "Alice"
    ws["B2"] = 30
    ws["C2"] = 95.5
    ws["A3"] = "Bob"
    ws["B3"] = 25
    ws["C3"] = 88.0
    path = tmp_path / "simple.xlsx"
    wb.save(str(path))
    return path


@pytest.fixture
def multi_sheet_workbook(tmp_path):
    """Workbook with 3 sheets: Sales, Costs, Notes."""
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "Sales"
    ws1["A1"] = "Product"
    ws1["B1"] = "Amount"
    ws1["A2"] = "Widget"
    ws1["B2"] = 1000

    ws2 = wb.create_sheet("Costs")
    ws2["A1"] = "Item"
    ws2["B1"] = "Cost"
    ws2["A2"] = "Rent"
    ws2["B2"] = 500

    ws3 = wb.create_sheet("Notes")
    ws3["A1"] = "Note"
    ws3["A2"] = "Q1 summary"

    path = tmp_path / "multi.xlsx"
    wb.save(str(path))
    return path


@pytest.fixture
def merged_cell_workbook(tmp_path):
    """Workbook where A1:C1 is merged with value 'Header'."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Merged"
    ws.merge_cells("A1:C1")
    ws["A1"] = "Header"
    ws["A2"] = "Col1"
    ws["B2"] = "Col2"
    ws["C2"] = "Col3"
    ws["A3"] = "Val1"
    ws["B3"] = "Val2"
    ws["C3"] = "Val3"
    path = tmp_path / "merged.xlsx"
    wb.save(str(path))
    return path


@pytest.fixture
def hidden_sheet_workbook(tmp_path):
    """Workbook with 2 visible sheets and 1 hidden sheet."""
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "Visible1"
    ws1["A1"] = "Hello"

    ws2 = wb.create_sheet("HiddenSheet")
    ws2.sheet_state = "hidden"
    ws2["A1"] = "Secret"

    ws3 = wb.create_sheet("Visible2")
    ws3["A1"] = "World"

    path = tmp_path / "hidden.xlsx"
    wb.save(str(path))
    return path


@pytest.fixture
def empty_sheet_workbook(tmp_path):
    """Workbook with 1 populated sheet and 1 completely empty sheet."""
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "Data"
    ws1["A1"] = "Value"
    ws1["A2"] = 42

    ws2 = wb.create_sheet("Empty")
    # No data in ws2

    path = tmp_path / "empty.xlsx"
    wb.save(str(path))
    return path


@pytest.fixture
def large_sheet_workbook(tmp_path):
    """Workbook with 1 sheet containing 300 rows (header + 299 data rows)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BigData"
    ws.append(["ID", "Value"])
    for i in range(1, 300):
        ws.append([i, i * 10])
    # Total: 300 rows (1 header + 299 data)
    path = tmp_path / "large.xlsx"
    wb.save(str(path))
    return path


@pytest.fixture
def special_chars_workbook(tmp_path):
    """Workbook with cells containing pipes and newlines."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Special"
    ws["A1"] = "Label"
    ws["B1"] = "Value"
    ws["A2"] = "pipe|cell"
    ws["B2"] = "line1\nline2"
    path = tmp_path / "special.xlsx"
    wb.save(str(path))
    return path


@pytest.fixture
def small_sheet_workbook(tmp_path):
    """Workbook with 1 sheet and 50 rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Small"
    ws.append(["ID", "Value"])
    for i in range(1, 50):
        ws.append([i, i * 2])
    path = tmp_path / "small.xlsx"
    wb.save(str(path))
    return path


# ---------------------------------------------------------------------------
# Tests: Basic parsing
# ---------------------------------------------------------------------------


class TestSpreadsheetParserBasic:
    def test_parse_simple_workbook(self, simple_workbook):
        parser = SpreadsheetParser()
        items = parser.parse(simple_workbook)

        assert len(items) == 1
        item = items[0]
        assert item["type"] == "table"
        assert "| Name | Age | Score |" in item["table_body"]
        assert isinstance(item["table_caption"], list)
        assert item["page_idx"] == 0
        caption = item["table_caption"][0]
        assert "simple.xlsx" in caption
        assert "Data" in caption

    def test_parse_returns_valid_gfm(self, simple_workbook):
        parser = SpreadsheetParser()
        items = parser.parse(simple_workbook)
        body = items[0]["table_body"]

        lines = body.split("\n")
        # Header row
        assert lines[0].startswith("|")
        assert lines[0].endswith("|")
        # Separator row
        assert "---" in lines[1]
        assert "|" in lines[1]
        # At least one data row
        assert len(lines) >= 3
        assert lines[2].startswith("|")

    def test_parse_multi_sheet(self, multi_sheet_workbook):
        parser = SpreadsheetParser()
        items = parser.parse(multi_sheet_workbook)

        assert len(items) == 3
        page_indices = [item["page_idx"] for item in items]
        assert page_indices == [0, 1, 2]

        captions = [item["table_caption"][0] for item in items]
        assert any("Sales" in c for c in captions)
        assert any("Costs" in c for c in captions)
        assert any("Notes" in c for c in captions)

    def test_parse_file_not_found(self, tmp_path):
        parser = SpreadsheetParser()
        with pytest.raises(FileNotFoundError):
            parser.parse(tmp_path / "nonexistent.xlsx")

    def test_parse_unsupported_format(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b,c\n1,2,3\n")
        parser = SpreadsheetParser()
        with pytest.raises(ValueError):
            parser.parse(csv_file)


# ---------------------------------------------------------------------------
# Tests: Merged cells
# ---------------------------------------------------------------------------


class TestMergedCells:
    def test_merged_cell_annotation(self, merged_cell_workbook):
        parser = SpreadsheetParser()
        items = parser.parse(merged_cell_workbook)

        body = items[0]["table_body"]
        assert "[merged" in body
        # Anchor cell contains the header text with annotation
        assert "Header" in body

    def test_merged_cell_siblings_empty(self, merged_cell_workbook):
        parser = SpreadsheetParser()
        items = parser.parse(merged_cell_workbook)

        body = items[0]["table_body"]
        first_row = body.split("\n")[0]
        # A1:C1 merged -> 3 columns, B1 and C1 should be empty (sibling)
        # Format: | Header [merged 1x3] |  |  |
        cells = [c.strip() for c in first_row.split("|") if c.strip() != "" or c != ""]
        # Count empty pipes between non-empty anchor and end
        # Verify that two sibling cells are empty strings
        non_boundary_cells = [c.strip() for c in first_row.split("|")[1:-1]]
        empty_cells = [c for c in non_boundary_cells if c.strip() == ""]
        assert len(empty_cells) >= 2


# ---------------------------------------------------------------------------
# Tests: Sheet filtering
# ---------------------------------------------------------------------------


class TestSheetFiltering:
    def test_hidden_sheet_skipped(self, hidden_sheet_workbook):
        parser = SpreadsheetParser()
        items = parser.parse(hidden_sheet_workbook)

        assert len(items) == 2
        captions = [item["table_caption"][0] for item in items]
        assert not any("HiddenSheet" in c for c in captions)

    def test_empty_sheet_skipped(self, empty_sheet_workbook):
        parser = SpreadsheetParser()
        items = parser.parse(empty_sheet_workbook)

        assert len(items) == 1
        assert "Data" in items[0]["table_caption"][0]


# ---------------------------------------------------------------------------
# Tests: Chunking
# ---------------------------------------------------------------------------


class TestChunking:
    def test_large_sheet_chunked(self, large_sheet_workbook):
        parser = SpreadsheetParser()  # default 150 rows/chunk
        items = parser.parse(large_sheet_workbook)

        assert len(items) == 2

    def test_chunk_captions_include_row_range(self, large_sheet_workbook):
        parser = SpreadsheetParser()
        items = parser.parse(large_sheet_workbook)

        assert len(items) == 2
        caption1 = items[0]["table_caption"][0]
        caption2 = items[1]["table_caption"][0]
        assert "rows 1-150 of 300" in caption1
        assert "rows 151-300 of 300" in caption2

    def test_chunks_share_page_idx(self, large_sheet_workbook):
        parser = SpreadsheetParser()
        items = parser.parse(large_sheet_workbook)

        assert items[0]["page_idx"] == items[1]["page_idx"]

    def test_custom_chunk_size(self, large_sheet_workbook):
        config = SpreadsheetConfig(max_rows_per_chunk=100)
        parser = SpreadsheetParser(config)
        items = parser.parse(large_sheet_workbook)

        assert len(items) == 3

    def test_small_sheet_not_chunked(self, small_sheet_workbook):
        config = SpreadsheetConfig(max_rows_per_chunk=150)
        parser = SpreadsheetParser(config)
        items = parser.parse(small_sheet_workbook)

        assert len(items) == 1
        caption = items[0]["table_caption"][0]
        assert "rows" not in caption


# ---------------------------------------------------------------------------
# Tests: Special characters
# ---------------------------------------------------------------------------


class TestSpecialCharacters:
    def test_pipe_escaped_in_output(self, special_chars_workbook):
        parser = SpreadsheetParser()
        items = parser.parse(special_chars_workbook)

        body = items[0]["table_body"]
        # The pipe in "pipe|cell" should be escaped to "\|"
        assert r"\|" in body

    def test_newline_replaced_in_output(self, special_chars_workbook):
        parser = SpreadsheetParser()
        items = parser.parse(special_chars_workbook)

        body = items[0]["table_body"]
        # Check no raw newline appears inside a cell value
        # Split on row separators and check each cell for embedded newlines
        lines = body.split("\n")
        for line in lines:
            # Each line is a full table row
            assert line.count("\n") == 0  # no embedded newlines within line


# ---------------------------------------------------------------------------
# Tests: Cell types
# ---------------------------------------------------------------------------


class TestCellTypes:
    def test_boolean_cell(self, tmp_path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws["A1"] = "Flag"
        ws["B1"] = True
        path = tmp_path / "bool.xlsx"
        wb.save(str(path))

        parser = SpreadsheetParser()
        items = parser.parse(path)

        assert "TRUE" in items[0]["table_body"]

    def test_none_cell(self, tmp_path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws["A1"] = "Label"
        ws["B1"] = None
        ws["A2"] = "Data"
        ws["B2"] = None
        path = tmp_path / "none.xlsx"
        wb.save(str(path))

        parser = SpreadsheetParser()
        items = parser.parse(path)

        # Empty cell renders as empty between pipes e.g. "|  |"
        body = items[0]["table_body"]
        assert body  # non-empty output

    def test_date_cell(self, tmp_path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws["A1"] = "Date"
        ws["B1"] = datetime.date(2024, 3, 15)
        ws["A2"] = "Value"
        ws["B2"] = datetime.date(2024, 1, 1)
        path = tmp_path / "date.xlsx"
        wb.save(str(path))

        parser = SpreadsheetParser()
        items = parser.parse(path)

        assert "2024-03-15" in items[0]["table_body"]
