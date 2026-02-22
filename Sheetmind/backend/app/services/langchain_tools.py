"""
LangChain tools for Google Sheets operations.

These tools allow the LangChain ReAct agent to:
- Read sheet data (headers, columns, cells)
- Create execution plans (create sheet, set formulas, etc.)
- Perform sheet manipulations (filter, sort, highlight)
"""

import json
import logging
import re
from contextvars import ContextVar
from typing import List, Dict, Optional

from langchain.tools import tool

logger = logging.getLogger(__name__)


def _sanitize_json(input_str: str) -> str:
    """
    Sanitize JSON input to handle common LLM mistakes.

    Fixes:
    - Python-style booleans (True/False -> true/false)
    - Python-style None -> null
    - Single quotes -> double quotes (when safe)
    """
    if not input_str:
        return input_str

    # Replace Python booleans with JSON booleans
    # Use word boundaries to avoid replacing inside strings
    result = re.sub(r'\bTrue\b', 'true', input_str)
    result = re.sub(r'\bFalse\b', 'false', result)
    result = re.sub(r'\bNone\b', 'null', result)

    return result


def _parse_json_input(input_str: str, default_error: str = "Invalid JSON input") -> tuple[dict | None, str | None]:
    """
    Parse JSON input with sanitization and error handling.

    Returns:
        (parsed_dict, None) on success
        (None, error_message) on failure
    """
    if not input_str or not input_str.strip():
        return None, f'{{"error": "{default_error}"}}'

    # Remove common prefixes the LLM might add
    cleaned = input_str.strip()
    # Remove "input_json=" prefix if present
    if cleaned.startswith("input_json="):
        cleaned = cleaned[11:]
    # Remove any variable assignment like "data=" or "json="
    if re.match(r'^[a-z_]+=', cleaned):
        cleaned = re.sub(r'^[a-z_]+=', '', cleaned)

    # Try parsing as-is first
    try:
        return json.loads(cleaned), None
    except json.JSONDecodeError:
        pass

    # Try with sanitization
    try:
        sanitized = _sanitize_json(cleaned)
        return json.loads(sanitized), None
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e}. Input: {input_str[:100]}")
        return None, f'{{"error": "{default_error}"}}'

# ---------------------------------------------------------------------------
# Thread-safe Per-Request State (via contextvars)
# ---------------------------------------------------------------------------
# Using ContextVar instead of module-level globals ensures each thread
# (i.e. each concurrent agent run) gets its own isolated copy.
# This prevents cross-user data leakage when multiple requests run in parallel.

_current_sheet_context: ContextVar[Optional[Dict]] = ContextVar("sheet_context", default=None)
_pending_actions: ContextVar[Optional[List[Dict]]] = ContextVar("pending_actions", default=None)


def set_sheet_context(context: Dict) -> None:
    """Set the current sheet context for tools to use.

    Args:
        context: Dict with keys:
            - cells: Dict[str, Any] mapping cell refs to values
            - sheetName: str name of the active sheet
            - dataRange: str like "A1:G31"
    """
    _current_sheet_context.set(context or {})
    # Each new context gets a fresh actions list
    _pending_actions.set([])


def get_sheet_context() -> Dict:
    """Get the current sheet context."""
    ctx = _current_sheet_context.get()
    return ctx if ctx is not None else {}


def get_pending_actions() -> List[Dict]:
    """Get and clear pending actions for frontend execution."""
    actions = _pending_actions.get()
    result = list(actions) if actions is not None else []
    _pending_actions.set([])
    return result


def clear_pending_actions() -> None:
    """Clear pending actions without returning them."""
    _pending_actions.set([])


def _queue_action(action: Dict) -> str:
    """Queue an action for frontend execution and return confirmation.

    Includes deduplication to prevent duplicate actions (like creating same sheet twice).
    """
    actions = _pending_actions.get()
    if actions is None:
        actions = []
        _pending_actions.set(actions)
    # Check for duplicate createSheet actions
    if action.get("action") == "createSheet":
        for existing in actions:
            if existing.get("action") == "createSheet" and existing.get("name") == action.get("name"):
                logger.info(f"Skipping duplicate createSheet for '{action.get('name')}'")
                return json.dumps({"status": "already_queued", "name": action.get("name")})

    actions.append(action)
    _pending_actions.set(actions)
    return json.dumps(action)


def _parse_cell_ref(cell_ref: str) -> tuple:
    """Parse cell reference into (column, row) tuple."""
    match = re.match(r"^([A-Z]+)(\d+)$", cell_ref.upper())
    if match:
        return match.group(1), int(match.group(2))
    return None, None


# ---------------------------------------------------------------------------
# SHEET READING TOOLS
# ---------------------------------------------------------------------------

@tool
def get_headers() -> str:
    """
    Get the column headers from the current sheet.
    Use this FIRST to understand the data structure before any operations.

    Returns:
        JSON object mapping column letters to header names.
        Example: {"A": "Name", "B": "Age", "C": "Major", "D": "GPA"}
    """
    ctx = _current_sheet_context.get()
    if not ctx or "cells" not in ctx:
        return '{"error": "No sheet data available"}'

    cells = ctx["cells"]
    headers = {}

    for cell_ref, value in cells.items():
        col, row = _parse_cell_ref(cell_ref)
        if col and row == 1:
            headers[col] = str(value)

    # Sort by column letter
    sorted_headers = dict(sorted(headers.items(), key=lambda x: (len(x[0]), x[0])))
    return json.dumps(sorted_headers, indent=2)


@tool
def get_column_values(column: str, limit: int = 20) -> str:
    """
    Get sample values from a column to understand the data types and patterns.

    Args:
        column: Column letter (e.g., "A", "B", "C")
        limit: Maximum number of values to return (default 20)

    Returns:
        JSON array of {row, value} objects from that column.
    """
    ctx = _current_sheet_context.get()
    if not ctx or "cells" not in ctx:
        return '{"error": "No sheet data available"}'

    cells = ctx["cells"]
    values = []

    col_upper = column.upper()
    for cell_ref, value in cells.items():
        col, row = _parse_cell_ref(cell_ref)
        if col == col_upper and row > 1:  # Skip header row
            values.append({"row": row, "value": str(value)})

    values.sort(key=lambda x: x["row"])
    return json.dumps(values[:limit], indent=2)


@tool
def get_row(row_number: int) -> str:
    """
    Get all values from a specific row.

    Args:
        row_number: The row number to retrieve (1-indexed)

    Returns:
        JSON object mapping column letters to values for that row.
    """
    ctx = _current_sheet_context.get()
    if not ctx or "cells" not in ctx:
        return '{"error": "No sheet data available"}'

    cells = ctx["cells"]
    row_data = {}

    for cell_ref, value in cells.items():
        col, row = _parse_cell_ref(cell_ref)
        if col and row == row_number:
            row_data[col] = str(value)

    if not row_data:
        return f'{{"error": "Row {row_number} not found"}}'

    sorted_data = dict(sorted(row_data.items(), key=lambda x: (len(x[0]), x[0])))
    return json.dumps(sorted_data, indent=2)


@tool
def get_cell(cell_ref: str) -> str:
    """
    Get the value of a specific cell.

    Args:
        cell_ref: Cell reference like "A1", "B5", "C10"

    Returns:
        The cell value as a string, or error if not found.
    """
    ctx = _current_sheet_context.get()
    if not ctx or "cells" not in ctx:
        return '{"error": "No sheet data available"}'

    cells = ctx["cells"]
    ref_upper = cell_ref.upper()

    if ref_upper in cells:
        return str(cells[ref_upper])

    return f'{{"error": "Cell {cell_ref} not found"}}'


@tool
def get_data_range() -> str:
    """
    Get information about the data range in the current sheet.

    Returns:
        JSON with sheet name, data range, row count, and column count.
    """
    ctx = _current_sheet_context.get()
    if not ctx:
        return '{"error": "No sheet data available"}'

    info = {
        "sheetName": ctx.get("sheetName", "Sheet1"),
        "dataRange": ctx.get("dataRange", ""),
    }

    cells = ctx.get("cells", {})
    if cells:
        rows = set()
        cols = set()
        for cell_ref in cells.keys():
            col, row = _parse_cell_ref(cell_ref)
            if col and row:
                rows.add(row)
                cols.add(col)

        info["rowCount"] = len(rows)
        info["columnCount"] = len(cols)
        info["lastRow"] = max(rows) if rows else 0
        info["columns"] = sorted(cols, key=lambda x: (len(x), x))

    return json.dumps(info, indent=2)


@tool
def count_rows() -> str:
    """
    Count the number of data rows (excluding header).

    Returns:
        The count of data rows as a string.
    """
    ctx = _current_sheet_context.get()
    if not ctx or "cells" not in ctx:
        return '{"error": "No sheet data available"}'

    cells = ctx["cells"]
    rows = set()

    for cell_ref in cells.keys():
        col, row = _parse_cell_ref(cell_ref)
        if row and row > 1:  # Exclude header
            rows.add(row)

    return str(len(rows))


@tool
def get_column_stats(column: str) -> str:
    """
    Get statistics for a column including unique count.
    IMPORTANT: Use this to determine chart endRow = startRow + uniqueCount - 1

    Args:
        column: Column letter (e.g., "B" for Gender, "E" for Major)

    Returns:
        JSON with:
        - header: Column header name
        - uniqueCount: Number of unique values (USE THIS FOR CHART ENDROW!)
        - uniqueValues: List of unique values (first 10)
        - totalRows: Total data rows
        - type: "categorical" or "numeric" or "text"

    Example usage for charts:
        If uniqueCount=2 (e.g., Male/Female), then:
        - UNIQUE formula will produce 2 rows (row 2 and 3)
        - Chart endRow = 2 + 2 - 1 = 3
    """
    ctx = _current_sheet_context.get()
    if not ctx or "cells" not in ctx:
        return '{"error": "No sheet data available"}'

    cells = ctx["cells"]
    col_upper = column.upper()

    # Get header
    header_ref = f"{col_upper}1"
    header = cells.get(header_ref, f"Column {col_upper}")

    # Get all values in column
    values = []
    for cell_ref, value in cells.items():
        col, row = _parse_cell_ref(cell_ref)
        if col == col_upper and row > 1:
            values.append(str(value))

    # Calculate stats
    unique_values = list(set(values))
    unique_count = len(unique_values)

    # Detect type
    col_type = "text"
    if unique_count <= 20 and unique_count < len(values) * 0.5:
        col_type = "categorical"
    else:
        # Check if numeric
        numeric_count = sum(1 for v in values if v.replace('.', '').replace('-', '').isdigit())
        if numeric_count > len(values) * 0.8:
            col_type = "numeric"

    result = {
        "header": header,
        "uniqueCount": unique_count,
        "uniqueValues": unique_values[:10],  # First 10 for preview
        "totalRows": len(values),
        "type": col_type,
        "chartEndRowFormula": f"startRow + {unique_count} - 1 = 2 + {unique_count} - 1 = {2 + unique_count - 1}"
    }

    return json.dumps(result, indent=2)


@tool
def get_chart_range(column: str) -> str:
    """
    Get the correct startRow and endRow for creating a chart based on unique values in a column.

    Use this BEFORE create_chart to get the exact row range.

    Args:
        column: The column letter used for grouping/labels (e.g., "A" for the UNIQUE column in summary sheet)

    Returns:
        JSON with startRow, endRow, uniqueCount, and fillDownLastRow ready to use in create_chart and autoFillDown.
    """
    ctx = _current_sheet_context.get()
    if not ctx or "cells" not in ctx:
        return '{"error": "No sheet data available"}'

    metadata = ctx.get("metadata", {})
    cells = ctx.get("cells", {})
    col_upper = column.upper()

    # Try to get unique count from metadata
    columns = metadata.get("columns", [])
    unique_count = None

    for col in columns:
        col_letter = col.get("letter", "")
        if col_letter.upper() == col_upper:
            unique_count = col.get("unique_count") or col.get("uniqueCount")
            break

    if unique_count is None:
        # Fallback: calculate from cell data
        values = []
        for cell_ref, value in cells.items():
            parsed_col, row = _parse_cell_ref(cell_ref)
            if parsed_col == col_upper and row and row > 1:
                values.append(str(value))
        unique_count = len(set(values)) if values else 10

    start_row = 2  # Data starts at row 2 (row 1 is headers)
    end_row = start_row + unique_count - 1
    fill_down_last_row = 1 + unique_count  # For autoFillDown

    return json.dumps({
        "startRow": start_row,
        "endRow": end_row,
        "uniqueCount": unique_count,
        "fillDownLastRow": fill_down_last_row,
        "explanation": f"{unique_count} unique values -> chart rows {start_row} to {end_row}, autoFillDown to row {fill_down_last_row}"
    })


# ---------------------------------------------------------------------------
# FORMULA KNOWLEDGE BASE TOOL
# ---------------------------------------------------------------------------

@tool
def lookup_formula(intent: str) -> str:
    """
    IMPORTANT: Call this BEFORE writing any formula to get the correct formula pattern.

    This tool searches the formula knowledge base to find the right formula for your intent.
    It returns the correct formula template, examples, and warnings about common mistakes.

    Args:
        intent: Describe what you want to calculate, e.g.:
                - "sum by category"
                - "sum of price times quantity by region"
                - "count unique values"
                - "average by group"
                - "multiply columns and sum with condition"

    Returns:
        JSON with:
        - formula_name: The recommended formula (SUMIF, SUMPRODUCT, etc.)
        - template: Formula pattern to follow
        - example: Ready-to-use example with current sheet name
        - warning: Important limitations to avoid errors
        - common_mistakes: What NOT to do

    ALWAYS use this tool before set_formula when doing aggregations!
    """
    from app.services.formula_patterns import get_formula_for_intent, find_formula_pattern, format_pattern_for_prompt

    # Get sheet context for filling in examples
    ctx = _current_sheet_context.get()
    sheet_name = ctx.get("sheetName", "Sheet1")
    metadata = ctx.get("metadata", {})
    last_row = metadata.get("last_row", 100)

    result = get_formula_for_intent(intent, sheet_name, last_row)

    # Enhance with formatted pattern for better agent readability
    if result.get("found"):
        patterns = find_formula_pattern(intent)
        if patterns:
            result["formatted_guide"] = format_pattern_for_prompt(patterns[0])

    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# SHEET WRITING TOOLS (Queue actions for frontend)
# ---------------------------------------------------------------------------

@tool
def create_sheet(name: str) -> str:
    """
    Create a new Google Sheet with the given name.
    Use this when creating summary sheets or output sheets.

    Args:
        name: The name for the new sheet (e.g., "Sales Summary", "Duplicate Report")

    Returns:
        Confirmation message.
    """
    # Clean up the name - remove any parameter prefix like 'name=' if present
    clean_name = name.strip()
    if clean_name.startswith('name='):
        clean_name = clean_name[5:].strip()
    # Remove surrounding quotes if present
    clean_name = clean_name.strip('"\'')

    action = {"action": "createSheet", "name": clean_name}
    _queue_action(action)
    return f"Created sheet '{clean_name}'"


def _validate_and_fix_formula(formula: str, last_row: int) -> tuple[str, list[str]]:
    """
    Validate formula and fix common mistakes.

    Returns:
        (fixed_formula, list_of_warnings)
    """
    warnings = []
    fixed = formula

    # Fix 1: SUMIF with multiplication in sum_range -> SUMPRODUCT
    # Pattern: =SUMIF(range, criteria, range1*range2)
    sumif_mult_pattern = re.compile(
        r"=SUMIF\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+\*[^)]+)\s*\)",
        re.IGNORECASE
    )
    match = sumif_mult_pattern.match(formula)
    if match:
        criteria_range, criteria, mult_expr = match.groups()
        # Convert to SUMPRODUCT
        fixed = f"=SUMPRODUCT(({criteria_range}={criteria})*({mult_expr}))"
        warnings.append(f"CONVERTED: SUMIF with multiplication is invalid. Changed to SUMPRODUCT: {fixed}")

    # Fix 2: Full column references (A:A, B:B) -> use last_row
    # Pattern: 'SheetName'!A:A or A:A
    def replace_full_col(m):
        prefix = m.group(1) or ""  # Sheet name prefix if exists
        col = m.group(2)
        warnings.append(f"Fixed full column {col}:{col} to {col}2:{col}{last_row}")
        return f"{prefix}{col}2:{col}{last_row}"

    # Match 'SheetName'!A:A or just A:A
    full_col_pattern = re.compile(r"('[\w\s]+'!)?\b([A-Z]):\2\b")
    fixed = full_col_pattern.sub(replace_full_col, fixed)

    # Fix 3: Partial column references (A2:A, B2:B) -> add last_row
    def replace_partial_col(m):
        prefix = m.group(1) or ""
        col = m.group(2)
        start_row = m.group(3)
        warnings.append(f"Fixed open-ended range {col}{start_row}:{col} to {col}{start_row}:{col}{last_row}")
        return f"{prefix}{col}{start_row}:{col}{last_row}"

    # Match 'SheetName'!A2:A or just A2:A (missing end row)
    partial_col_pattern = re.compile(r"('[\w\s]+'!)?\b([A-Z])(\d+):\2\b(?!\d)")
    fixed = partial_col_pattern.sub(replace_partial_col, fixed)

    # Fix 4: Syntax validation (parentheses, function names, arg counts)
    from app.services.formula_validator import validate_formula, suggest_alternatives
    is_valid, syntax_errors = validate_formula(fixed)
    if not is_valid:
        # Classify errors as critical vs non-critical
        critical_keywords = ["parenthesis", "Unknown function", "Empty formula", "must start"]
        for err in syntax_errors:
            is_critical = any(kw.lower() in err.lower() for kw in critical_keywords)
            if is_critical:
                logger.warning(f"Formula critical syntax error: {err} | formula: {fixed[:100]}")
                warnings.append(f"CRITICAL SYNTAX ERROR: {err}")
            else:
                warnings.append(f"SYNTAX: {err}")

    # Fix 5: Suggest modern alternatives
    suggestions = suggest_alternatives(fixed)
    if suggestions:
        warnings.extend([f"Suggestion: {s}" for s in suggestions])

    return fixed, warnings


@tool
def set_formula(input_json: str) -> str:
    """
    Set a formula in a specific cell.

    Args:
        input_json: A JSON string with keys: sheet, cell, formula, fillDown (optional)
            Example: {"sheet": "Summary", "cell": "B2", "formula": "=SUMIF('Sheet1'!A:A, A2, 'Sheet1'!C:C)", "fillDown": true}

    Returns:
        Confirmation message with formula preview.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON input. Expected {"sheet": "...", "cell": "...", "formula": "..."}'
    )
    if error:
        return error

    sheet = data.get("sheet", "Sheet1")
    cell = data.get("cell", "A1")
    formula = data.get("formula", "")
    fill_down = data.get("fillDown", False)

    # Get last_row from metadata for formula validation
    ctx = _current_sheet_context.get()
    metadata = ctx.get("metadata", {})
    last_row = metadata.get("last_row", 100)

    # Validate and fix formula
    fixed_formula, warnings = _validate_and_fix_formula(formula, last_row)

    # Check for UNIQUE/FILTER with fillDown (auto-spill formulas)
    auto_spill_pattern = re.compile(r"=\s*(UNIQUE|FILTER|SORT|SORTN|SEQUENCE|ARRAYFORMULA)\s*\(", re.IGNORECASE)
    if fill_down and auto_spill_pattern.match(fixed_formula):
        fill_down = False
        warnings.append(f"BLOCKED fillDown=true for auto-spill formula ({auto_spill_pattern.match(fixed_formula).group(1)}). These formulas auto-expand.")

    action = {
        "action": "setFormula",
        "sheet": sheet,
        "cell": cell,
        "formula": fixed_formula,  # Use validated/fixed formula
        "fillDown": fill_down
    }
    _queue_action(action)

    msg = f"Set {sheet}!{cell} = {fixed_formula}"
    if fill_down:
        msg += " (will fill down)"

    # Include any validation warnings
    if warnings:
        msg += "\n\nFORMULA VALIDATION NOTES:\n" + "\n".join(f"- {w}" for w in warnings)

    return msg


@tool
def set_values(input_json: str) -> str:
    """
    Set multiple values in a range at once.

    Args:
        input_json: A JSON string with keys: sheet, range, values
            Example: {"sheet": "Summary", "range": "A1:B1", "values": [["Major", "Total"]]}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON input. Expected {"sheet": "...", "range": "...", "values": [[...]]}'
    )
    if error:
        return error

    sheet = data.get("sheet", "Sheet1")
    range_str = data.get("range", "A1")
    values = data.get("values", [[]])

    action = {
        "action": "setValues",
        "sheet": sheet,
        "range": range_str,
        "values": values
    }
    _queue_action(action)
    return f"Set values in {sheet}!{range_str}"


@tool
def format_headers(input_json: str) -> str:
    """
    Format a range as headers (bold, blue background, white text).
    Use this after setting header values to make them stand out.

    Args:
        input_json: A JSON string with keys: sheet, range
            Example: {"sheet": "Summary", "range": "A1:B1"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON input. Expected {"sheet": "...", "range": "..."}'
    )
    if error:
        return error

    sheet = data.get("sheet", "Sheet1")
    range_str = data.get("range", "A1")

    action = {
        "action": "formatRange",
        "sheet": sheet,
        "range": range_str,
        "bold": True,
        "background": "#4472C4",
        "fontColor": "#FFFFFF"
    }
    _queue_action(action)
    return f"Formatted {sheet}!{range_str} as headers"


@tool
def auto_fill_down(input_json: str) -> str:
    """
    Copy a formula from source cell down to the specified last row.

    Args:
        input_json: A JSON string with keys: sheet, sourceCell, lastRow
            Example: {"sheet": "Summary", "sourceCell": "B2", "lastRow": 5}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON input. Expected {"sheet": "...", "sourceCell": "...", "lastRow": ...}'
    )
    if error:
        return error

    sheet = data.get("sheet", "Sheet1")
    source_cell = data.get("sourceCell", "A2")
    last_row = data.get("lastRow", 10)

    action = {
        "action": "autoFillDown",
        "sheet": sheet,
        "sourceCell": source_cell,
        "lastRow": last_row
    }
    _queue_action(action)
    return f"Filled formula from {sheet}!{source_cell} down to row {last_row}"


# ---------------------------------------------------------------------------
# SHEET MANIPULATION TOOLS
# ---------------------------------------------------------------------------

@tool
def highlight_range(range_str: str, color: str = "#FFFF00") -> str:
    """
    Highlight cells with a background color.

    Args:
        range_str: Range to highlight (e.g., "A2:A10", "B5:D5")
        color: Hex color code (default: yellow #FFFF00)
               Common colors: red=#FF0000, green=#00FF00, blue=#0000FF,
                             orange=#FFA500, pink=#FFC0CB

    Returns:
        Confirmation message.
    """
    action = {"action": "highlight", "range": range_str, "color": color}
    _queue_action(action)
    return f"Highlighted {range_str} with color {color}"


@tool
def filter_data(column: str, criteria: str) -> str:
    """
    Apply a filter to show only rows matching the criteria.

    Args:
        column: Column letter to filter (e.g., "C", "D")
        criteria: Filter condition:
                  - Text match: "=Male", "=Active" (use exact value from data)
                  - Not equal: "!=Inactive"
                  - Numbers: ">100", ">=50", "<10", "<=0"

    Returns:
        Confirmation message.
    """
    action = {"action": "filter", "column": column, "criteria": criteria}
    _queue_action(action)
    return f"Filtered column {column} where {criteria}"


@tool
def sort_data(column: str, ascending: bool = True) -> str:
    """
    Sort the sheet by a column.

    Args:
        column: Column letter to sort by (e.g., "A", "B")
        ascending: True for A-Z/0-9, False for Z-A/9-0

    Returns:
        Confirmation message.
    """
    action = {"action": "sort", "column": column, "ascending": ascending}
    _queue_action(action)
    direction = "ascending" if ascending else "descending"
    return f"Sorted by column {column} ({direction})"


@tool
def clear_filters() -> str:
    """
    Remove all filters from the sheet.

    Returns:
        Confirmation message.
    """
    action = {"action": "clearFilters"}
    _queue_action(action)
    return "Cleared all filters"


@tool
def create_chart(input_json: str) -> str:
    """
    Create a chart from sheet data.
    Use this when the user asks for a chart, graph, or visualization.

    Args:
        input_json: A JSON string with chart configuration:
            - type: "bar", "line", "pie", "doughnut", "scatter" (required)
            - title: Chart title (required)
            - dataSheet: Sheet name containing the data (required)
            - labelColumn: Column letter for labels/categories, e.g., "A" (required)
            - valueColumn: Column letter for values, e.g., "B" (required)
            - startRow: First data row (default 2, assuming row 1 is headers)
            - endRow: Last data row (optional, will auto-detect if not provided)

        Example: {"type": "bar", "title": "Students by Major", "dataSheet": "Major Counts", "labelColumn": "A", "valueColumn": "B", "startRow": 2}

    Returns:
        Confirmation message that chart will be created.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON input. Expected chart configuration object.'
    )
    if error:
        return error

    chart_type = data.get("type", "bar")
    title = data.get("title", "Chart")
    data_sheet = data.get("dataSheet", "Sheet1")
    label_col = data.get("labelColumn", "A")
    value_col = data.get("valueColumn", "B")
    start_row = data.get("startRow", 2)
    end_row = data.get("endRow")

    action = {
        "action": "createChart",
        "chartType": chart_type,
        "title": title,
        "dataSheet": data_sheet,
        "labelColumn": label_col,
        "valueColumn": value_col,
        "startRow": start_row,
        "endRow": end_row,
    }
    _queue_action(action)

    return f"Chart '{title}' ({chart_type}) will be created using data from {data_sheet}!{label_col}{start_row}:{value_col}{end_row or 'last'}"


@tool
def insert_column(input_json: str) -> str:
    """
    Insert a new column into the active sheet.
    Use this when you need to add a new column for calculations like totals, percentages, etc.

    Args:
        input_json: A JSON string with keys:
            - after: Column letter to insert after (e.g., "E" inserts new column after E)
            - header: (optional) Header text for the new column

        Example: {"after": "E", "header": "Total Sales"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON input. Expected {"after": "E", "header": "Total Sales"}'
    )
    if error:
        return error

    after_col = data.get("after", "A")
    header = data.get("header", "")

    action = {"action": "insertColumn", "after": after_col}
    if header:
        action["header"] = header

    _queue_action(action)
    msg = f"Inserted column after {after_col}"
    if header:
        msg += f" with header '{header}'"
    return msg


@tool
def set_cell_value(input_json: str) -> str:
    """
    Set a value or formula in a single cell on the ACTIVE sheet.
    Use this for quick single-cell updates like adding a formula, a label, or a computed value.

    For formulas on a NEW/DIFFERENT sheet, use set_formula instead.
    For multiple cells at once, use set_values instead.

    Args:
        input_json: A JSON string with keys:
            - cell: Cell reference (e.g., "F2", "A1")
            - value: The value or formula to set (e.g., "=D2+E2", "Total", 100)

        Example: {"cell": "F2", "value": "=D2+E2"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON input. Expected {"cell": "F2", "value": "=D2+E2"}'
    )
    if error:
        return error

    cell = data.get("cell", "A1")
    value = data.get("value", "")

    action = {"action": "setValue", "cell": cell, "value": value}
    _queue_action(action)
    return f"Set {cell} = {value}"


# ---------------------------------------------------------------------------
# BATCH 1: FORMATTING POWERHOUSE (5 actions)
# ---------------------------------------------------------------------------

@tool
def format_range(input_json: str) -> str:
    """
    Apply rich formatting to a range: bold, italic, strikethrough, fontSize, fontFamily,
    fontColor, background, alignment, and text wrap.

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (required)
            - range: Range like "A1:D1" (required)
            - bold: true/false
            - italic: true/false
            - strikethrough: true/false
            - fontSize: number (e.g. 12, 14, 18)
            - fontFamily: font name (e.g. "Arial", "Roboto", "Courier New")
            - fontColor: hex color (e.g. "#FF0000")
            - background: hex color (e.g. "#4472C4")
            - horizontalAlignment: "left", "center", or "right"
            - verticalAlignment: "top", "middle", or "bottom"
            - wrapStrategy: "WRAP", "OVERFLOW", or "CLIP"

        Example: {"sheet": "Sheet1", "range": "A1:D1", "bold": true, "fontSize": 14, "horizontalAlignment": "center", "background": "#4472C4", "fontColor": "#FFFFFF"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"sheet": "...", "range": "...", "bold": true, ...}'
    )
    if error:
        return error

    sheet = data.get("sheet", "Sheet1")
    range_str = data.get("range", "A1")

    action = {
        "action": "formatRange",
        "sheet": sheet,
        "range": range_str,
    }
    for key in ["bold", "italic", "strikethrough", "fontSize", "fontFamily",
                 "fontColor", "background", "horizontalAlignment", "verticalAlignment", "wrapStrategy"]:
        if key in data:
            action[key] = data[key]

    _queue_action(action)
    return f"Formatted {sheet}!{range_str}"


@tool
def set_number_format(input_json: str) -> str:
    """
    Set number format for a range (currency, percent, date, etc.).

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (required)
            - range: Range like "B2:B100" (required)
            - format: "currency", "percent", "number", "date", "datetime", "text", or "custom" (required)
            - decimals: Number of decimal places (default 2)
            - currencySymbol: e.g. "$", "€", "£" (for currency format)
            - customPattern: Custom pattern like "#,##0.00" (for custom format)

        Example: {"sheet": "Sheet1", "range": "C2:C50", "format": "currency", "decimals": 2, "currencySymbol": "$"}
        Example: {"sheet": "Sheet1", "range": "D2:D50", "format": "percent", "decimals": 1}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"sheet": "...", "range": "...", "format": "currency"}'
    )
    if error:
        return error

    sheet = data.get("sheet", "Sheet1")
    range_str = data.get("range", "A1")
    fmt = data.get("format", "number")

    action = {
        "action": "numberFormat",
        "sheet": sheet,
        "range": range_str,
        "format": fmt,
    }
    for key in ["decimals", "currencySymbol", "customPattern"]:
        if key in data:
            action[key] = data[key]

    _queue_action(action)
    return f"Set number format '{fmt}' on {sheet}!{range_str}"


@tool
def set_borders(input_json: str) -> str:
    """
    Add borders to a range.

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (required)
            - range: Range like "A1:F20" (required)
            - style: "all", "outline", "inner", "top", "bottom", "left", "right" (default "all")
            - weight: "thin" or "thick" (default "thin")
            - color: Hex color (default "#000000")

        Example: {"sheet": "Sheet1", "range": "A1:F20", "style": "all", "weight": "thin"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"sheet": "...", "range": "...", "style": "all"}'
    )
    if error:
        return error

    sheet = data.get("sheet", "Sheet1")
    range_str = data.get("range", "A1")

    action = {
        "action": "setBorders",
        "sheet": sheet,
        "range": range_str,
        "style": data.get("style", "all"),
        "weight": data.get("weight", "thin"),
        "color": data.get("color", "#000000"),
    }
    _queue_action(action)
    return f"Set borders ({action['style']}) on {sheet}!{range_str}"


@tool
def freeze_rows_columns(input_json: str) -> str:
    """
    Freeze rows and/or columns so they stay visible when scrolling.

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (optional, defaults to active sheet)
            - rows: Number of rows to freeze from the top (e.g. 1 for header row)
            - columns: Number of columns to freeze from the left (e.g. 1)

        Example: {"rows": 1}  — freeze header row
        Example: {"sheet": "Data", "rows": 2, "columns": 1}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"rows": 1} or {"rows": 1, "columns": 1}'
    )
    if error:
        return error

    action = {
        "action": "freeze",
    }
    if "sheet" in data:
        action["sheet"] = data["sheet"]
    if "rows" in data:
        action["rows"] = data["rows"]
    if "columns" in data:
        action["columns"] = data["columns"]

    _queue_action(action)
    parts = []
    if "rows" in data:
        parts.append(f"{data['rows']} row(s)")
    if "columns" in data:
        parts.append(f"{data['columns']} column(s)")
    return f"Froze {' and '.join(parts)}"


@tool
def auto_resize_columns(input_json: str) -> str:
    """
    Auto-resize columns to fit their content.

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (optional, defaults to active sheet)
            - columns: Array of column letters (e.g. ["A", "B", "C"]) or "all"

        Example: {"columns": ["A", "B", "C"]}
        Example: {"sheet": "Summary", "columns": "all"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"columns": ["A", "B"]} or {"columns": "all"}'
    )
    if error:
        return error

    action = {
        "action": "autoResize",
        "columns": data.get("columns", "all"),
    }
    if "sheet" in data:
        action["sheet"] = data["sheet"]

    _queue_action(action)
    cols = data.get("columns", "all")
    col_str = ", ".join(cols) if isinstance(cols, list) else cols
    return f"Auto-resized columns: {col_str}"


# ---------------------------------------------------------------------------
# BATCH 2: ROW/COLUMN/DATA OPERATIONS (5 actions)
# ---------------------------------------------------------------------------

@tool
def delete_rows(input_json: str) -> str:
    """
    Delete rows from the sheet. WARNING: This action is irreversible!

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (optional, defaults to active sheet)
            - rows: Array of row numbers to delete (e.g. [3, 5, 8])
            OR
            - condition: Object with {column, value} to delete matching rows
              or {column, empty: true} to delete rows where that column is empty

        Example: {"rows": [3, 5, 8]}
        Example: {"sheet": "Data", "condition": {"column": "B", "value": "N/A"}}
        Example: {"condition": {"column": "A", "empty": true}}  — delete all rows where column A is empty

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"rows": [3, 5]} or {"condition": {"column": "B", "value": "..."}}'
    )
    if error:
        return error

    action = {"action": "deleteRows"}
    if "sheet" in data:
        action["sheet"] = data["sheet"]
    if "rows" in data:
        action["rows"] = data["rows"]
    if "condition" in data:
        action["condition"] = data["condition"]

    _queue_action(action)
    if "rows" in data:
        return f"Deleting rows: {data['rows']}"
    elif "condition" in data:
        cond = data["condition"]
        if cond.get("empty"):
            return f"Deleting rows where column {cond['column']} is empty"
        return f"Deleting rows where column {cond['column']} = {cond.get('value', '')}"
    return "Delete rows queued"


@tool
def delete_columns(input_json: str) -> str:
    """
    Delete columns from the sheet. WARNING: This action is irreversible!

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (optional, defaults to active sheet)
            - columns: Array of column letters to delete (e.g. ["C", "E"])

        Example: {"columns": ["C", "E"]}
        Example: {"sheet": "Data", "columns": ["F"]}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"columns": ["C", "E"]}'
    )
    if error:
        return error

    action = {
        "action": "deleteColumns",
        "columns": data.get("columns", []),
    }
    if "sheet" in data:
        action["sheet"] = data["sheet"]

    _queue_action(action)
    return f"⚠️ WARNING: Deleting columns is irreversible! Please make sure you have a backup of your data before proceeding. Deleting columns: {', '.join(data.get('columns', []))}"


@tool
def merge_cells(input_json: str) -> str:
    """
    Merge or unmerge cells in a range.

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (required)
            - range: Range to merge (e.g. "A1:D1")
            - type: "merge" (all), "mergeVertically", "mergeHorizontally", or "unmerge"

        Example: {"sheet": "Sheet1", "range": "A1:D1", "type": "merge"}
        Example: {"sheet": "Sheet1", "range": "A1:D1", "type": "unmerge"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"sheet": "...", "range": "A1:D1", "type": "merge"}'
    )
    if error:
        return error

    action = {
        "action": "mergeCells",
        "sheet": data.get("sheet", "Sheet1"),
        "range": data.get("range", "A1"),
        "type": data.get("type", "merge"),
    }
    _queue_action(action)
    return f"{action['type'].capitalize()} cells {action['sheet']}!{action['range']}"


@tool
def clear_range(input_json: str) -> str:
    """
    Clear contents, formatting, or both from a range.

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (required)
            - range: Range to clear (e.g. "A2:F100")
            - type: "all" (contents + formatting), "contents" (values/formulas only), or "formatting" (styles only)

        Example: {"sheet": "Sheet1", "range": "A2:F100", "type": "contents"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"sheet": "...", "range": "...", "type": "all"}'
    )
    if error:
        return error

    action = {
        "action": "clearRange",
        "sheet": data.get("sheet", "Sheet1"),
        "range": data.get("range", "A1"),
        "type": data.get("type", "all"),
    }
    _queue_action(action)
    return f"Cleared {action['type']} from {action['sheet']}!{action['range']}"


@tool
def copy_range(input_json: str) -> str:
    """
    Copy a range from one location to another, optionally across sheets.

    Args:
        input_json: JSON with keys:
            - sourceSheet: Source sheet name (required)
            - sourceRange: Range to copy (e.g. "A1:D10") (required)
            - destSheet: Destination sheet name (required)
            - destCell: Top-left cell of destination (e.g. "A1") (required)
            - valuesOnly: If true, paste values only (no formulas/formatting). Default false.

        Example: {"sourceSheet": "Sheet1", "sourceRange": "A1:D10", "destSheet": "Sheet2", "destCell": "A1", "valuesOnly": true}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"sourceSheet": "...", "sourceRange": "...", "destSheet": "...", "destCell": "..."}'
    )
    if error:
        return error

    action = {
        "action": "copyRange",
        "sourceSheet": data.get("sourceSheet", "Sheet1"),
        "sourceRange": data.get("sourceRange", "A1"),
        "destSheet": data.get("destSheet", "Sheet1"),
        "destCell": data.get("destCell", "A1"),
        "valuesOnly": data.get("valuesOnly", False),
    }
    _queue_action(action)
    return f"Copied {action['sourceSheet']}!{action['sourceRange']} to {action['destSheet']}!{action['destCell']}"


# ---------------------------------------------------------------------------
# BATCH 3: CONDITIONAL FORMATTING & DATA VALIDATION (2 actions)
# ---------------------------------------------------------------------------

@tool
def conditional_format(input_json: str) -> str:
    """
    Add a conditional formatting rule to a range.

    IMPORTANT: Before calling this, ALWAYS call get_headers first to identify the correct
    column letter. Never guess column positions. Use the actual sheet name and last_row.
    The range should be "ColumnLetter2:ColumnLetterN" (skip header row).

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (required — use the actual sheet name, not "Sheet1")
            - range: Range to format (e.g. "D2:D100") (required — must match the correct column)
            - type: "comparison", "text", "colorScale", "empty", "notEmpty" (required)
            - operator: For comparison: "greaterThan", "lessThan", "equalTo", "greaterThanOrEqualTo",
                        "lessThanOrEqualTo", "notEqualTo", "between"
            - value: Comparison value (number or text)
            - valueTo: Second value for "between" operator
            - textContains: Text to match for type="text"
            - background: Hex color for matching cells (e.g. "#FF0000")
            - fontColor: Hex color for text in matching cells
            - bold: true/false for matching cells
            - colorScaleMin: Hex color for minimum value (for colorScale)
            - colorScaleMid: Hex color for midpoint value (for colorScale)
            - colorScaleMax: Hex color for maximum value (for colorScale)

        Example: {"sheet": "Sheet1", "range": "C2:C100", "type": "comparison", "operator": "greaterThan", "value": 100, "background": "#FF0000"}
        Example: {"sheet": "Sheet1", "range": "A2:A100", "type": "text", "textContains": "error", "background": "#FFCCCC"}
        Example: {"sheet": "Sheet1", "range": "D2:D100", "type": "colorScale", "colorScaleMin": "#FF0000", "colorScaleMax": "#00FF00"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"sheet": "...", "range": "...", "type": "comparison", ...}'
    )
    if error:
        return error

    action = {
        "action": "conditionalFormat",
        "sheet": data.get("sheet", "Sheet1"),
        "range": data.get("range", "A1"),
        "type": data.get("type", "comparison"),
    }
    for key in ["operator", "value", "valueTo", "textContains", "background",
                 "fontColor", "bold", "colorScaleMin", "colorScaleMid", "colorScaleMax"]:
        if key in data:
            action[key] = data[key]

    _queue_action(action)
    return f"Added conditional format rule on {action['sheet']}!{action['range']}"


@tool
def set_data_validation(input_json: str) -> str:
    """
    Set data validation rules on a range (dropdowns, number ranges, checkboxes).

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (required)
            - range: Range to validate (e.g. "E2:E100") (required)
            - type: "list", "number", "date", "checkbox", "custom" (required)
            - values: Array of allowed values for type="list" (e.g. ["Yes", "No", "Maybe"])
            - min: Minimum value for type="number"
            - max: Maximum value for type="number"
            - allowInvalid: If false, reject invalid input (default true)
            - customFormula: Formula for type="custom" (e.g. "=LEN(A1)>5")

        Example: {"sheet": "Sheet1", "range": "E2:E100", "type": "list", "values": ["Yes", "No", "Maybe"]}
        Example: {"sheet": "Sheet1", "range": "F2:F100", "type": "number", "min": 0, "max": 100}
        Example: {"sheet": "Sheet1", "range": "G2:G100", "type": "checkbox"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"sheet": "...", "range": "...", "type": "list", "values": [...]}'
    )
    if error:
        return error

    action = {
        "action": "dataValidation",
        "sheet": data.get("sheet", "Sheet1"),
        "range": data.get("range", "A1"),
        "type": data.get("type", "list"),
    }
    for key in ["values", "min", "max", "allowInvalid", "customFormula"]:
        if key in data:
            action[key] = data[key]

    _queue_action(action)
    return f"Set data validation ({action['type']}) on {action['sheet']}!{action['range']}"


# ---------------------------------------------------------------------------
# BATCH 4: SHEET MANAGEMENT & SEARCH (4 actions)
# ---------------------------------------------------------------------------

@tool
def rename_sheet(input_json: str) -> str:
    """
    Rename an existing sheet.

    Args:
        input_json: JSON with keys:
            - oldName: Current sheet name (required)
            - newName: New sheet name (required)

        Example: {"oldName": "Sheet1", "newName": "Raw Data"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"oldName": "...", "newName": "..."}'
    )
    if error:
        return error

    action = {
        "action": "renameSheet",
        "oldName": data.get("oldName", ""),
        "newName": data.get("newName", ""),
    }
    _queue_action(action)
    return f"Renamed sheet '{action['oldName']}' to '{action['newName']}'"


@tool
def copy_sheet(input_json: str) -> str:
    """
    Duplicate/copy an existing sheet within the same spreadsheet.

    Args:
        input_json: JSON with keys:
            - source: Name of the sheet to copy (required)
            - newName: Name for the copy (required)

        Example: {"source": "Sheet1", "newName": "Sheet1 - Backup"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"source": "...", "newName": "..."}'
    )
    if error:
        return error

    action = {
        "action": "copySheet",
        "source": data.get("source", ""),
        "newName": data.get("newName", ""),
    }
    _queue_action(action)
    return f"Copied sheet '{action['source']}' as '{action['newName']}'"


@tool
def delete_sheet(input_json: str) -> str:
    """
    Delete a sheet. WARNING: This is irreversible! Cannot delete the last remaining sheet.

    Args:
        input_json: JSON with keys:
            - name: Name of the sheet to delete (required)

        Example: {"name": "Old Summary"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"name": "..."}'
    )
    if error:
        return error

    action = {
        "action": "deleteSheet",
        "name": data.get("name", ""),
    }
    _queue_action(action)
    return f"Deleting sheet '{action['name']}'"


@tool
def find_and_replace(input_json: str) -> str:
    """
    Find and replace text across a sheet or range.

    Args:
        input_json: JSON with keys:
            - sheet: Sheet name (optional, defaults to active sheet)
            - find: Text to search for (required)
            - replace: Replacement text (required, use "" for empty)
            - range: Limit search to a range (optional, e.g. "A1:D100")
            - matchCase: Case-sensitive search (default false)

        Example: {"find": "N/A", "replace": ""}
        Example: {"sheet": "Data", "find": "USD", "replace": "$", "matchCase": true}
        Example: {"sheet": "Data", "find": "old", "replace": "new", "range": "A1:A100"}

    Returns:
        Confirmation message.
    """
    data, error = _parse_json_input(
        input_json,
        'Invalid JSON. Expected {"find": "...", "replace": "..."}'
    )
    if error:
        return error

    action = {
        "action": "findReplace",
        "find": data.get("find", ""),
        "replace": data.get("replace", ""),
    }
    if "sheet" in data:
        action["sheet"] = data["sheet"]
    if "range" in data:
        action["range"] = data["range"]
    if "matchCase" in data:
        action["matchCase"] = data["matchCase"]

    _queue_action(action)
    return f"Find '{action['find']}' and replace with '{action['replace']}'"


# ---------------------------------------------------------------------------
# TOOL LISTS
# ---------------------------------------------------------------------------

# Reading tools (don't create actions)
READING_TOOLS = [
    get_headers,
    get_column_values,
    get_column_stats,  # Get unique count for chart sizing
    get_chart_range,   # Get startRow/endRow for charts
    get_row,
    get_cell,
    get_data_range,
    count_rows,
    lookup_formula,  # Formula knowledge base lookup
]

# Writing tools (create actions for frontend)
WRITING_TOOLS = [
    create_sheet,
    set_formula,
    set_values,
    set_cell_value,
    format_headers,
    format_range,
    auto_fill_down,
    insert_column,
    create_chart,
    set_number_format,
    set_borders,
    merge_cells,
    copy_range,
    clear_range,
    rename_sheet,
    copy_sheet,
    delete_sheet,
    find_and_replace,
]

# Manipulation tools (create actions for frontend)
MANIPULATION_TOOLS = [
    highlight_range,
    filter_data,
    sort_data,
    clear_filters,
    delete_rows,
    delete_columns,
    conditional_format,
    set_data_validation,
    freeze_rows_columns,
    auto_resize_columns,
]

# All sheet tools (RAG tools added separately)
SHEET_TOOLS = READING_TOOLS + WRITING_TOOLS + MANIPULATION_TOOLS

# Will be populated by rag_system.py
RAG_TOOLS: List = []

def verify_actions() -> dict:
    """
    Verify all queued actions for correctness.
    Called after agent completes to catch issues before execution.

    Returns:
        Dict with verification results and any fixes applied.
    """
    issues = []
    fixes = []

    ctx = _current_sheet_context.get()
    actions = _pending_actions.get()

    # Get metadata for validation
    metadata = ctx.get("metadata", {})
    last_row = metadata.get("last_row", 100)

    # Track created sheets for reference validation
    created_sheets = set()

    for i, action in enumerate(actions):
        action_type = action.get("action")

        # Track created sheets
        if action_type == "createSheet":
            created_sheets.add(action.get("name"))

        # Validate setFormula actions
        if action_type == "setFormula":
            formula = action.get("formula", "")
            sheet = action.get("sheet", "")

            # Check for open-ended ranges
            if re.search(r"[A-Z]\d+:[A-Z](?!\d)", formula):
                issues.append(f"Action {i+1}: Formula has open-ended range")
                # Auto-fix
                fixed_formula = re.sub(
                    r"([A-Z])(\d+):(\1)(?!\d)",
                    rf"\g<1>\g<2>:\g<3>{last_row}",
                    formula
                )
                action["formula"] = fixed_formula
                fixes.append(f"Fixed range to use lastRow={last_row}")

            # Check for SUMIF with multiplication
            if re.search(r"SUMIF.*\*", formula, re.IGNORECASE):
                issues.append(f"Action {i+1}: SUMIF with multiplication detected")

            # Syntax validation
            from app.services.formula_validator import validate_formula
            is_valid, syntax_errors = validate_formula(formula)
            if not is_valid:
                for err in syntax_errors:
                    issues.append(f"Action {i+1}: {err}")

        # Validate chart actions
        if action_type == "createChart":
            data_sheet = action.get("dataSheet", "")
            end_row = action.get("endRow")
            start_row = action.get("startRow", 2)

            # Check if chart references created sheet
            if data_sheet not in created_sheets and data_sheet != ctx.get("sheetName"):
                issues.append(f"Action {i+1}: Chart references unknown sheet '{data_sheet}'")

            # Check for unreasonable endRow
            if end_row and end_row > last_row + 10:
                issues.append(f"Action {i+1}: Chart endRow={end_row} seems too large")

        # Validate new action types
        if action_type == "deleteRows":
            if not action.get("rows") and not action.get("condition"):
                issues.append(f"Action {i+1}: deleteRows requires 'rows' or 'condition'")

        if action_type == "deleteColumns":
            if not action.get("columns"):
                issues.append(f"Action {i+1}: deleteColumns requires 'columns'")

        if action_type == "deleteSheet":
            if not action.get("name"):
                issues.append(f"Action {i+1}: deleteSheet requires 'name'")

        if action_type == "conditionalFormat":
            cf_type = action.get("type", "")
            if cf_type == "comparison" and not action.get("operator"):
                issues.append(f"Action {i+1}: conditionalFormat comparison requires 'operator'")
            if cf_type == "comparison" and action.get("value") is None:
                issues.append(f"Action {i+1}: conditionalFormat comparison requires 'value'")
            if cf_type == "text" and not action.get("textContains"):
                issues.append(f"Action {i+1}: conditionalFormat text requires 'textContains'")
            # Warn if no visible formatting effect
            if cf_type != "colorScale" and not action.get("background") and not action.get("fontColor") and not action.get("bold"):
                issues.append(f"Action {i+1}: conditionalFormat has no visible effect — add 'background', 'fontColor', or 'bold'")
            # Fix sheet name if it's the default "Sheet1" but actual sheet is different
            cf_sheet = action.get("sheet", "")
            actual_sheet = ctx.get("sheetName", "")
            if cf_sheet == "Sheet1" and actual_sheet and actual_sheet != "Sheet1":
                action["sheet"] = actual_sheet
                fixes.append(f"Action {i+1}: Fixed conditionalFormat sheet from 'Sheet1' to '{actual_sheet}'")

        if action_type == "dataValidation":
            dv_type = action.get("type", "")
            if dv_type == "list" and not action.get("values"):
                issues.append(f"Action {i+1}: dataValidation list requires 'values'")

        if action_type == "findReplace":
            if not action.get("find") and action.get("find") != "":
                issues.append(f"Action {i+1}: findReplace requires 'find'")

    # Write back any fixes applied to actions
    _pending_actions.set(actions)

    return {
        "total_actions": len(actions),
        "issues_found": len(issues),
        "issues": issues,
        "fixes_applied": fixes,
        "verification": "PASSED" if len(issues) == 0 else "PASSED_WITH_FIXES" if len(fixes) > 0 else "NEEDS_REVIEW"
    }


# All tools combined
ALL_TOOLS = SHEET_TOOLS  # RAG_TOOLS added after import
