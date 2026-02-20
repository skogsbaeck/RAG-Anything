"""
Unit tests for raganything.spreadsheet helper functions.

Tests cover: cell value formatting, markdown sanitization,
merge map construction, and empty edge stripping.
"""

import datetime

import pytest

from raganything.spreadsheet import (
    build_merge_map,
    format_cell_value,
    sanitize_cell,
    strip_empty_edges,
)


# ---------------------------------------------------------------------------
# Mock worksheet helpers (avoids openpyxl dependency in tests)
# ---------------------------------------------------------------------------


class MockMergedRange:
    def __init__(self, min_row: int, max_row: int, min_col: int, max_col: int) -> None:
        self.min_row = min_row
        self.max_row = max_row
        self.min_col = min_col
        self.max_col = max_col


class MockMergedCells:
    def __init__(self, ranges: list) -> None:
        self.ranges = ranges


class MockWorksheet:
    def __init__(self, ranges: list) -> None:
        self.merged_cells = MockMergedCells(ranges)


# ---------------------------------------------------------------------------
# TestFormatCellValue
# ---------------------------------------------------------------------------


class TestFormatCellValue:
    def test_none_returns_empty_string(self) -> None:
        assert format_cell_value(None) == ""

    def test_bool_true(self) -> None:
        assert format_cell_value(True) == "TRUE"

    def test_bool_false(self) -> None:
        assert format_cell_value(False) == "FALSE"

    def test_int(self) -> None:
        assert format_cell_value(42) == "42"

    def test_float(self) -> None:
        assert format_cell_value(3.14) == "3.14"

    def test_float_with_trailing_zero(self) -> None:
        # Raw float value preserved, not truncated
        assert format_cell_value(10.0) == "10.0"

    def test_date(self) -> None:
        assert format_cell_value(datetime.date(2024, 1, 15)) == "2024-01-15"

    def test_datetime(self) -> None:
        assert (
            format_cell_value(datetime.datetime(2024, 1, 15, 10, 30, 45))
            == "2024-01-15T10:30:45"
        )

    def test_string_passthrough(self) -> None:
        assert format_cell_value("hello") == "hello"

    def test_string_with_pipe_escaped(self) -> None:
        assert format_cell_value("A|B") == r"A\|B"

    def test_string_with_newline_replaced(self) -> None:
        assert format_cell_value("line1\nline2") == "line1 line2"


# ---------------------------------------------------------------------------
# TestSanitizeCell
# ---------------------------------------------------------------------------


class TestSanitizeCell:
    def test_pipe_escaped(self) -> None:
        assert sanitize_cell("A|B|C") == r"A\|B\|C"

    def test_newline_replaced(self) -> None:
        assert sanitize_cell("a\nb") == "a b"

    def test_carriage_return_newline(self) -> None:
        assert sanitize_cell("a\r\nb") == "a b"

    def test_carriage_return_only(self) -> None:
        assert sanitize_cell("a\rb") == "a b"

    def test_whitespace_stripped(self) -> None:
        assert sanitize_cell("  hello  ") == "hello"

    def test_combined(self) -> None:
        assert sanitize_cell("  A|B\nC  ") == r"A\|B C"


# ---------------------------------------------------------------------------
# TestBuildMergeMap
# ---------------------------------------------------------------------------


class TestBuildMergeMap:
    def test_horizontal_merge(self) -> None:
        # A1:C1 => row 1, cols 1-3
        ws = MockWorksheet([MockMergedRange(1, 1, 1, 3)])
        result = build_merge_map(ws)

        assert result[(1, 1)]["is_anchor"] is True
        assert result[(1, 1)]["span_rows"] == 1
        assert result[(1, 1)]["span_cols"] == 3
        assert result[(1, 2)]["is_anchor"] is False
        assert result[(1, 3)]["is_anchor"] is False

    def test_vertical_merge(self) -> None:
        # A1:A3 => rows 1-3, col 1
        ws = MockWorksheet([MockMergedRange(1, 3, 1, 1)])
        result = build_merge_map(ws)

        assert result[(1, 1)]["is_anchor"] is True
        assert result[(1, 1)]["span_rows"] == 3
        assert result[(2, 1)]["is_anchor"] is False
        assert result[(3, 1)]["is_anchor"] is False

    def test_2d_merge(self) -> None:
        # A1:B2 => 2x2, anchor + 3 siblings
        ws = MockWorksheet([MockMergedRange(1, 2, 1, 2)])
        result = build_merge_map(ws)

        assert len(result) == 4
        assert result[(1, 1)]["is_anchor"] is True
        assert result[(1, 1)]["span_rows"] == 2
        assert result[(1, 1)]["span_cols"] == 2
        assert result[(1, 2)]["is_anchor"] is False
        assert result[(2, 1)]["is_anchor"] is False
        assert result[(2, 2)]["is_anchor"] is False

    def test_no_merges(self) -> None:
        ws = MockWorksheet([])
        assert build_merge_map(ws) == {}

    def test_degenerate_1x1_skipped(self) -> None:
        # A single-cell "merge" should not appear in the map
        ws = MockWorksheet([MockMergedRange(2, 2, 3, 3)])
        assert build_merge_map(ws) == {}


# ---------------------------------------------------------------------------
# TestStripEmptyEdges
# ---------------------------------------------------------------------------


class TestStripEmptyEdges:
    def test_trailing_empty_columns_removed(self) -> None:
        rows = [[1, 2, None], [3, 4, None]]
        assert strip_empty_edges(rows) == [[1, 2], [3, 4]]

    def test_trailing_empty_rows_removed(self) -> None:
        rows = [[1, 2], [None, None]]
        assert strip_empty_edges(rows) == [[1, 2]]

    def test_leading_empty_preserved(self) -> None:
        # Leading None column must NOT be stripped (A1 offset preserved)
        rows = [[None, 1], [None, 2]]
        assert strip_empty_edges(rows) == [[None, 1], [None, 2]]

    def test_all_empty_returns_empty(self) -> None:
        rows = [[None, None], [None, None]]
        assert strip_empty_edges(rows) == []

    def test_no_stripping_needed(self) -> None:
        rows = [[1, 2], [3, 4]]
        assert strip_empty_edges(rows) == [[1, 2], [3, 4]]

    def test_empty_string_treated_as_empty(self) -> None:
        rows = [[1, ""], ["", ""]]
        assert strip_empty_edges(rows) == [[1]]
