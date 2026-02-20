"""
Spreadsheet processing module for structured tabular data parsing.

Provides helper functions for converting spreadsheet content into
markdown tables suitable for RAG knowledge graph ingestion.
"""

import datetime
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SpreadsheetConfig:
    """Configuration for spreadsheet processing."""

    max_rows_per_chunk: int = 150


SUPPORTED_FORMATS: list[str] = [".xlsx", ".xls"]


def get_supported_formats() -> list[str]:
    """Return list of supported spreadsheet file extensions."""
    return SUPPORTED_FORMATS


def is_supported_format(file_path: Path) -> bool:
    """Return True if file extension is a supported spreadsheet format."""
    return Path(file_path).suffix.lower() in SUPPORTED_FORMATS


def sanitize_cell(value: str) -> str:
    """
    Escape markdown special characters in a string cell value.

    Replaces newlines with spaces and escapes pipe characters
    to prevent breaking GFM table structure.
    """
    value = value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    value = value.replace("|", r"\|")
    return value.strip()


def format_cell_value(value: Any) -> str:
    """
    Coerce an openpyxl cell value to a clean string.

    Handles all Python types returned by openpyxl: None, bool, int,
    float, datetime.datetime, datetime.date, str, and arbitrary types.
    Bool is checked before int because bool is a subclass of int.
    datetime.datetime is checked before datetime.date because datetime
    is a subclass of date.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, str):
        return sanitize_cell(value)
    return str(value)


def build_merge_map(worksheet: Any) -> dict[tuple[int, int], dict]:
    """
    Build a lookup dict from (row, col) -> merge info for a worksheet.

    Each entry contains:
    - is_anchor: True for the top-left cell of the merged region
    - span_rows: number of rows in the merge
    - span_cols: number of columns in the merge

    Degenerate 1x1 merges (no actual span) are skipped.
    """
    merge_map: dict[tuple[int, int], dict] = {}

    for cell_range in worksheet.merged_cells.ranges:
        span_rows = cell_range.max_row - cell_range.min_row + 1
        span_cols = cell_range.max_col - cell_range.min_col + 1

        if span_rows == 1 and span_cols == 1:
            continue

        for row in range(cell_range.min_row, cell_range.max_row + 1):
            for col in range(cell_range.min_col, cell_range.max_col + 1):
                is_anchor = (row == cell_range.min_row and col == cell_range.min_col)
                merge_map[(row, col)] = {
                    "is_anchor": is_anchor,
                    "span_rows": span_rows,
                    "span_cols": span_cols,
                }

    return merge_map


def strip_empty_edges(rows: list[list[Any]]) -> list[list[Any]]:
    """
    Remove trailing empty columns and rows from a 2D list of cell values.

    Empty means None or "". Only trailing (right/bottom) edges are removed;
    leading rows and columns are preserved to maintain A1 offset semantics.
    Returns [] if the entire grid is empty.
    """
    if not rows:
        return []

    def is_empty_value(v: Any) -> bool:
        return v is None or v == ""

    # Find the last non-empty column index across all rows
    max_col_count = max(len(row) for row in rows)
    last_col = -1
    for col in range(max_col_count):
        for row in rows:
            if col < len(row) and not is_empty_value(row[col]):
                last_col = col
                break

    # Recompute: scan all rows for each col to find rightmost non-empty col
    last_col = -1
    for col in range(max_col_count):
        for row in rows:
            if col < len(row) and not is_empty_value(row[col]):
                last_col = max(last_col, col)

    if last_col == -1:
        return []

    # Trim columns
    trimmed = [row[:last_col + 1] for row in rows]

    # Find the last non-empty row index
    last_row = -1
    for row_idx, row in enumerate(trimmed):
        if not all(is_empty_value(v) for v in row):
            last_row = row_idx

    if last_row == -1:
        return []

    return trimmed[:last_row + 1]
