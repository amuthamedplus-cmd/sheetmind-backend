"""
Source Linker — extracts row/cell references from AI responses
and converts them into structured SourceReference objects for
click-to-verify navigation in the Google Sheets sidebar.
"""

import logging
import re
from app.schemas.message import SourceReference

logger = logging.getLogger(__name__)


# Patterns to detect spreadsheet references in AI text
PATTERNS = [
    # "Rows 45-67" or "rows 12-18"
    (r'[Rr]ows?\s+(\d+)\s*[-–to]+\s*(\d+)', 'row_range'),
    # "Row 5" or "row 12"
    (r'[Rr]ow\s+(\d+)(?!\s*[-–to])', 'single_row'),
    # "Sheet1!A2:B50"
    (r'(\w+)!([A-Z]+\d+):([A-Z]+\d+)', 'sheet_range'),
    # "Range A1:D10" or "range B2:C5"
    (r'[Rr]ange\s+([A-Z]+\d+):([A-Z]+\d+)', 'range'),
    # "Cell B3" or "cell A1"
    (r'[Cc]ell\s+([A-Z]+\d+)', 'single_cell'),
    # Standalone range like "A1:D10" (not already captured)
    (r'(?<![A-Za-z!])([A-Z]+\d+):([A-Z]+\d+)', 'bare_range'),
]


def extract_sources(
    response_text: str,
    default_sheet: str = "Sheet1",
) -> list[SourceReference]:
    """
    Parse AI response text and extract all spreadsheet references.

    Args:
        response_text: The AI-generated response text.
        default_sheet: Sheet name to use when not specified in the reference.

    Returns:
        List of SourceReference objects with label, sheet, and range.
    """
    sources: list[SourceReference] = []
    seen: set[str] = set()  # Deduplicate

    for pattern, ref_type in PATTERNS:
        try:
            for match in re.finditer(pattern, response_text):
                source = _match_to_source(match, ref_type, default_sheet)
                if source and source.range not in seen:
                    seen.add(source.range)
                    sources.append(source)
        except (ValueError, IndexError, re.error) as e:
            logger.warning(f"Source extraction failed for pattern {ref_type}: {e}")
            continue

    return sources


def _match_to_source(
    match: re.Match,
    ref_type: str,
    default_sheet: str,
) -> SourceReference | None:
    """Convert a regex match to a SourceReference."""

    if ref_type == "row_range":
        start_row = int(match.group(1))
        end_row = int(match.group(2))
        return SourceReference(
            label=f"Rows {start_row}-{end_row}",
            sheet=default_sheet,
            range=f"A{start_row}:Z{end_row}",
        )

    elif ref_type == "single_row":
        row = int(match.group(1))
        return SourceReference(
            label=f"Row {row}",
            sheet=default_sheet,
            range=f"A{row}:Z{row}",
        )

    elif ref_type == "sheet_range":
        sheet = match.group(1)
        start = match.group(2)
        end = match.group(3)
        return SourceReference(
            label=f"{sheet}!{start}:{end}",
            sheet=sheet,
            range=f"{start}:{end}",
        )

    elif ref_type == "range":
        start = match.group(1)
        end = match.group(2)
        return SourceReference(
            label=f"Range {start}:{end}",
            sheet=default_sheet,
            range=f"{start}:{end}",
        )

    elif ref_type == "single_cell":
        cell = match.group(1)
        return SourceReference(
            label=f"Cell {cell}",
            sheet=default_sheet,
            range=cell,
        )

    elif ref_type == "bare_range":
        start = match.group(1)
        end = match.group(2)
        return SourceReference(
            label=f"{start}:{end}",
            sheet=default_sheet,
            range=f"{start}:{end}",
        )

    return None
