"""
Sheet Analyzer Service for SheetMind.

Pre-processes spreadsheet data to extract structured metadata before the agent runs.
This enables smarter, more accurate formula generation without guessing.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ColumnMetadata:
    """Metadata for a single column."""
    letter: str
    header: str
    column_type: str  # "numeric", "text", "date", "categorical", "empty"
    unique_count: int = 0
    null_count: int = 0
    total_count: int = 0
    samples: List[str] = field(default_factory=list)

    # Numeric stats (only for numeric columns)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    avg_value: Optional[float] = None
    sum_value: Optional[float] = None

    # Categorical stats (only for categorical columns)
    categories: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "letter": self.letter,
            "header": self.header,
            "type": self.column_type,
            "uniqueCount": self.unique_count,
            "nullCount": self.null_count,
            "samples": self.samples[:5],  # Limit samples
        }

        if self.column_type == "numeric":
            result["min"] = self.min_value
            result["max"] = self.max_value
            result["avg"] = round(self.avg_value, 2) if self.avg_value else None
            result["sum"] = round(self.sum_value, 2) if self.sum_value else None

        if self.column_type == "categorical":
            result["categories"] = self.categories[:20]  # Limit categories

        return result


@dataclass
class SheetMetadata:
    """Complete metadata for a spreadsheet."""
    sheet_name: str
    total_rows: int
    data_rows: int  # Excluding header
    last_row: int
    total_columns: int
    columns: List[ColumnMetadata] = field(default_factory=list)
    suggested_group_by: List[str] = field(default_factory=list)  # Column letters
    suggested_aggregate: List[str] = field(default_factory=list)  # Column letters
    suggested_date_column: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "sheetName": self.sheet_name,
            "totalRows": self.total_rows,
            "dataRows": self.data_rows,
            "lastRow": self.last_row,
            "totalColumns": self.total_columns,
            "columns": [col.to_dict() for col in self.columns],
            "suggestedGroupBy": self.suggested_group_by,
            "suggestedAggregate": self.suggested_aggregate,
            "suggestedDateColumn": self.suggested_date_column,
        }


# ---------------------------------------------------------------------------
# Type Detection Helpers
# ---------------------------------------------------------------------------

# Date patterns to detect
DATE_PATTERNS = [
    r"^\d{1,2}/\d{1,2}/\d{2,4}$",           # MM/DD/YYYY or M/D/YY
    r"^\d{4}-\d{2}-\d{2}$",                  # YYYY-MM-DD (ISO)
    r"^\d{1,2}-\d{1,2}-\d{2,4}$",           # DD-MM-YYYY
    r"^\d{1,2}\s+\w{3,9}\s+\d{2,4}$",       # 1 Jan 2024
    r"^\w{3,9}\s+\d{1,2},?\s+\d{2,4}$",     # January 1, 2024
]

_DATE_REGEX = [re.compile(p, re.IGNORECASE) for p in DATE_PATTERNS]


def _is_numeric(value: str) -> bool:
    """Check if a value is numeric (including currency/percentage)."""
    if not value or value.strip() == "":
        return False

    # Remove common formatting
    cleaned = value.strip()
    cleaned = cleaned.replace(",", "")
    cleaned = cleaned.replace("$", "")
    cleaned = cleaned.replace("%", "")
    cleaned = cleaned.replace("(", "-").replace(")", "")  # Accounting format
    cleaned = cleaned.strip()

    try:
        float(cleaned)
        return True
    except (ValueError, TypeError):
        return False


def _is_date(value: str) -> bool:
    """Check if a value looks like a date."""
    if not value or value.strip() == "":
        return False

    cleaned = value.strip()

    for pattern in _DATE_REGEX:
        if pattern.match(cleaned):
            return True

    return False


def _parse_numeric(value: str) -> Optional[float]:
    """Parse a numeric value, handling currency/percentage formatting."""
    if not value or value.strip() == "":
        return None

    cleaned = value.strip()
    cleaned = cleaned.replace(",", "")
    cleaned = cleaned.replace("$", "")
    cleaned = cleaned.replace("%", "")
    cleaned = cleaned.replace("(", "-").replace(")", "")
    cleaned = cleaned.strip()

    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _detect_column_type(values: List[str]) -> str:
    """
    Detect the predominant type of a column.

    Returns: "numeric", "date", "categorical", "text", or "empty"
    """
    if not values:
        return "empty"

    # Filter out empty values
    non_empty = [v for v in values if v and str(v).strip()]

    if not non_empty:
        return "empty"

    total = len(non_empty)
    numeric_count = 0
    date_count = 0

    for val in non_empty:
        val_str = str(val)
        if _is_numeric(val_str):
            numeric_count += 1
        elif _is_date(val_str):
            date_count += 1

    # Require 80% threshold for numeric
    if numeric_count / total >= 0.8:
        return "numeric"

    # Require 50% threshold for date
    if date_count / total >= 0.5:
        return "date"

    # Check for categorical (low cardinality text)
    unique_values = set(non_empty)
    unique_ratio = len(unique_values) / total

    # If less than 30% unique values and fewer than 20 categories, it's categorical
    if unique_ratio < 0.3 and len(unique_values) <= 20:
        return "categorical"

    return "text"


# ---------------------------------------------------------------------------
# Main Analyzer Function
# ---------------------------------------------------------------------------

def analyze_sheet(cells: Dict[str, str], sheet_name: str = "Sheet1") -> SheetMetadata:
    """
    Analyze sheet structure and return comprehensive metadata.

    This should be called ONCE before the agent runs to provide
    accurate context about the sheet structure.

    Args:
        cells: Dictionary mapping cell references (e.g., "A1") to values
        sheet_name: Name of the sheet being analyzed

    Returns:
        SheetMetadata object with complete analysis
    """
    if not cells:
        return SheetMetadata(
            sheet_name=sheet_name,
            total_rows=0,
            data_rows=0,
            last_row=0,
            total_columns=0,
        )

    # Parse cell references to extract structure
    cell_pattern = re.compile(r"^([A-Z]+)(\d+)$")

    # Organize data by column
    column_data: Dict[str, Dict[int, str]] = {}  # column_letter -> {row: value}
    all_rows = set()
    all_cols = set()

    for ref, value in cells.items():
        match = cell_pattern.match(ref)
        if not match:
            continue

        col_letter = match.group(1)
        row_num = int(match.group(2))

        all_rows.add(row_num)
        all_cols.add(col_letter)

        if col_letter not in column_data:
            column_data[col_letter] = {}
        column_data[col_letter][row_num] = str(value) if value is not None else ""

    if not all_rows or not all_cols:
        return SheetMetadata(
            sheet_name=sheet_name,
            total_rows=0,
            data_rows=0,
            last_row=0,
            total_columns=0,
        )

    # Sort columns alphabetically (A, B, C, ... AA, AB)
    sorted_cols = sorted(all_cols, key=lambda c: (len(c), c))
    min_row = min(all_rows)
    max_row = max(all_rows)
    total_rows = max_row - min_row + 1
    data_rows = total_rows - 1  # Assuming row 1 is header

    # Analyze each column
    columns: List[ColumnMetadata] = []
    suggested_group_by: List[str] = []
    suggested_aggregate: List[str] = []
    suggested_date_column: Optional[str] = None

    for col_letter in sorted_cols:
        col_rows = column_data.get(col_letter, {})

        # Get header (row 1 or min_row)
        header = col_rows.get(min_row, col_rows.get(1, f"Column {col_letter}"))

        # Get data values (excluding header)
        data_values = [
            col_rows.get(r, "")
            for r in range(min_row + 1, max_row + 1)
            if r in col_rows or r <= max_row
        ]

        # Detect column type
        col_type = _detect_column_type(data_values)

        # Calculate statistics
        non_empty_values = [v for v in data_values if v and str(v).strip()]
        unique_values = list(set(non_empty_values))
        null_count = len(data_values) - len(non_empty_values)

        col_meta = ColumnMetadata(
            letter=col_letter,
            header=str(header),
            column_type=col_type,
            unique_count=len(unique_values),
            null_count=null_count,
            total_count=len(data_values),
            samples=non_empty_values[:5],
        )

        # Calculate numeric stats
        if col_type == "numeric":
            numeric_vals = []
            for v in non_empty_values:
                parsed = _parse_numeric(v)
                if parsed is not None:
                    numeric_vals.append(parsed)

            if numeric_vals:
                col_meta.min_value = min(numeric_vals)
                col_meta.max_value = max(numeric_vals)
                col_meta.avg_value = sum(numeric_vals) / len(numeric_vals)
                col_meta.sum_value = sum(numeric_vals)

            # Numeric columns are good for aggregation
            suggested_aggregate.append(col_letter)

        # Store categories for categorical columns
        if col_type == "categorical":
            col_meta.categories = sorted(unique_values)[:20]
            # Categorical columns are good for grouping
            suggested_group_by.append(col_letter)

        # Track date columns
        if col_type == "date" and not suggested_date_column:
            suggested_date_column = col_letter

        columns.append(col_meta)

    logger.info(
        f"Analyzed sheet '{sheet_name}': {total_rows} rows, {len(columns)} columns, "
        f"group_by={suggested_group_by}, aggregate={suggested_aggregate}"
    )

    return SheetMetadata(
        sheet_name=sheet_name,
        total_rows=total_rows,
        data_rows=data_rows,
        last_row=max_row,
        total_columns=len(columns),
        columns=columns,
        suggested_group_by=suggested_group_by,
        suggested_aggregate=suggested_aggregate,
        suggested_date_column=suggested_date_column,
    )


def format_metadata_for_prompt(metadata: SheetMetadata) -> str:
    """
    Format sheet metadata as a string for inclusion in the agent prompt.

    Args:
        metadata: SheetMetadata object from analyze_sheet()

    Returns:
        Human-readable string describing the sheet structure
    """
    lines = [
        f"Sheet: '{metadata.sheet_name}'",
        f"Total rows: {metadata.total_rows} (data rows: {metadata.data_rows}, last row: {metadata.last_row})",
        f"Columns: {metadata.total_columns}",
        "",
        "Column Details:",
    ]

    for col in metadata.columns:
        type_info = col.column_type
        if col.column_type == "numeric" and col.sum_value is not None:
            type_info = f"numeric (min={col.min_value}, max={col.max_value}, sum={round(col.sum_value, 2)})"
        elif col.column_type == "categorical":
            cats = ", ".join(col.categories[:5])
            if len(col.categories) > 5:
                cats += f"... ({len(col.categories)} total)"
            type_info = f"categorical [{cats}]"

        lines.append(
            f"  - Column {col.letter}: '{col.header}' ({type_info}, {col.unique_count} unique, {col.null_count} empty)"
        )

    if metadata.suggested_group_by:
        group_cols = [
            f"{c} ({next((col.header for col in metadata.columns if col.letter == c), c)})"
            for c in metadata.suggested_group_by
        ]
        lines.append(f"\nGood for grouping (categorical): {', '.join(group_cols)}")

    if metadata.suggested_aggregate:
        agg_cols = [
            f"{c} ({next((col.header for col in metadata.columns if col.letter == c), c)})"
            for c in metadata.suggested_aggregate
        ]
        lines.append(f"Good for aggregation (numeric): {', '.join(agg_cols)}")

    if metadata.suggested_date_column:
        lines.append(f"Date column: {metadata.suggested_date_column}")

    return "\n".join(lines)


def get_column_by_header(metadata: SheetMetadata, header_name: str) -> Optional[ColumnMetadata]:
    """
    Find a column by its header name (case-insensitive partial match).

    Args:
        metadata: SheetMetadata object
        header_name: Header name to search for

    Returns:
        ColumnMetadata if found, None otherwise
    """
    header_lower = header_name.lower()

    # Exact match first
    for col in metadata.columns:
        if col.header.lower() == header_lower:
            return col

    # Partial match
    for col in metadata.columns:
        if header_lower in col.header.lower():
            return col

    return None
