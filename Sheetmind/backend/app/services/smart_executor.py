"""
Smart Executor - Hybrid approach for efficient sheet operations.

Reduces LLM calls from 10-15 to 1-2 by:
1. Classifying request type in one call (with Redis caching)
2. Using templates for known patterns (no additional LLM)
3. Using plan+execute for complex requests (one additional LLM call)
"""

import hashlib
import json
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Classifier Cache (Redis-backed, 30 min TTL)
# ---------------------------------------------------------------------------

_CLASSIFIER_CACHE_TTL = 1800  # 30 minutes


def _classifier_cache_key(request: str, headers: List[str], col_types: List[str]) -> str:
    """Build a cache key from the request and sheet structure.

    Numbers are preserved (not normalized) because they carry semantic meaning
    (e.g., "top 5" vs "top 10").
    """
    normalized = request.lower().strip()
    # Sort headers/types for stability
    key_data = f"{normalized}|{'|'.join(sorted(headers))}|{'|'.join(sorted(col_types))}"
    return f"classifier:{hashlib.sha256(key_data.encode()).hexdigest()[:24]}"


def _get_cached_classification(cache_key: str) -> Optional[Dict]:
    """Try to get a cached classification result from Redis."""
    try:
        from app.services.cache import _get_redis
        r = _get_redis()
        if r is None:
            return None
        data = r.get(cache_key)
        if data:
            logger.info(f"Classifier cache HIT: {cache_key[:20]}...")
            return json.loads(data)
    except Exception:
        pass
    return None


def _set_cached_classification(cache_key: str, result: Dict):
    """Cache a classification result in Redis."""
    try:
        from app.services.cache import _get_redis
        r = _get_redis()
        if r is None:
            return
        r.setex(cache_key, _CLASSIFIER_CACHE_TTL, json.dumps(result))
        logger.info(f"Classifier cache SET: {cache_key[:20]}...")
    except Exception:
        pass


# =============================================================================
# REQUEST TYPES
# =============================================================================

class RequestType(str, Enum):
    SIMPLE_QUESTION = "simple_question"      # Just answer, no sheet actions
    GROUPED_SUMMARY = "grouped_summary"       # Sum/count/avg by category
    GROUPED_SUMMARY_CHART = "grouped_summary_chart"  # Same with chart
    ADD_TO_EXISTING = "add_to_existing"      # Add column/data to an existing sheet
    TOP_N = "top_n"                          # Top/bottom N values
    FIND_DUPLICATES = "find_duplicates"      # Find duplicate rows
    FILTER_HIGHLIGHT = "filter_highlight"    # Filter and highlight
    COMPARISON = "comparison"                # Compare A vs B
    CHANGE_CHART_TYPE = "change_chart_type"  # Modify existing chart type
    COMPLEX = "complex"                      # Custom - use plan+execute


@dataclass
class ClassifiedRequest:
    """Result of classifying a user request."""
    request_type: RequestType
    group_by_column: Optional[str] = None
    value_column: Optional[str] = None
    aggregation: Optional[str] = None  # sum, count, avg, max, min
    chart_type: Optional[str] = None   # bar, line, pie
    n_value: Optional[int] = None      # for top_n
    filter_column: Optional[str] = None
    filter_value: Optional[str] = None
    duplicate_columns: Optional[List[str]] = None  # Column letters to check, None = all
    custom_plan: Optional[List[Dict]] = None
    answer: Optional[str] = None       # for simple questions
    summary_sheet: Optional[str] = None  # sheet name where chart exists
    target_sheet: Optional[str] = None   # existing sheet to modify (for add_to_existing)
    new_column_header: Optional[str] = None  # header for the new column
    new_column_formula: Optional[str] = None  # formula/value for the new column
    existing_headers: Optional[List[str]] = None  # headers already in the target sheet


# =============================================================================
# TEMPLATES
# =============================================================================

def template_grouped_summary(
    sheet_name: str,
    last_row: int,
    group_by_col: str,
    group_by_header: str,
    value_col: str,
    value_header: str,
    aggregation: str = "sum",
    unique_count: int = 10
) -> List[Dict]:
    """
    Template for: "Sum of X by Y", "Count by category", etc.
    """
    summary_name = f"{group_by_header} Summary"
    agg_upper = aggregation.upper()

    # Choose formula based on aggregation type
    if aggregation == "sum":
        formula = f"=SUMIF('{sheet_name}'!{group_by_col}2:{group_by_col}{last_row}, A2, '{sheet_name}'!{value_col}2:{value_col}{last_row})"
    elif aggregation == "count":
        formula = f"=COUNTIF('{sheet_name}'!{group_by_col}2:{group_by_col}{last_row}, A2)"
    elif aggregation == "avg":
        formula = f"=AVERAGEIF('{sheet_name}'!{group_by_col}2:{group_by_col}{last_row}, A2, '{sheet_name}'!{value_col}2:{value_col}{last_row})"
    elif aggregation == "max":
        formula = f"=MAXIFS('{sheet_name}'!{value_col}2:{value_col}{last_row}, '{sheet_name}'!{group_by_col}2:{group_by_col}{last_row}, A2)"
    elif aggregation == "min":
        formula = f"=MINIFS('{sheet_name}'!{value_col}2:{value_col}{last_row}, '{sheet_name}'!{group_by_col}2:{group_by_col}{last_row}, A2)"
    else:
        formula = f"=SUMIF('{sheet_name}'!{group_by_col}2:{group_by_col}{last_row}, A2, '{sheet_name}'!{value_col}2:{value_col}{last_row})"

    fill_down_row = 1 + unique_count  # header + unique values

    return [
        {"action": "createSheet", "name": summary_name},
        {"action": "setValues", "sheet": summary_name, "range": "A1:B1",
         "values": [[group_by_header, f"{agg_upper} of {value_header}"]]},
        {"action": "formatRange", "sheet": summary_name, "range": "A1:B1",
         "bold": True, "background": "#4472C4", "fontColor": "#FFFFFF"},
        {"action": "setFormula", "sheet": summary_name, "cell": "A2",
         "formula": f"=UNIQUE('{sheet_name}'!{group_by_col}2:{group_by_col}{last_row})"},
        {"action": "setFormula", "sheet": summary_name, "cell": "B2",
         "formula": formula},
        {"action": "autoFillDown", "sheet": summary_name, "sourceCell": "B2",
         "lastRow": fill_down_row}
    ]


def template_grouped_summary_chart(
    sheet_name: str,
    last_row: int,
    group_by_col: str,
    group_by_header: str,
    value_col: str,
    value_header: str,
    aggregation: str = "sum",
    chart_type: str = "bar",
    unique_count: int = 10
) -> List[Dict]:
    """
    Template for: "Chart of sales by region", "Pie chart of count by category"
    """
    # Get base summary actions
    actions = template_grouped_summary(
        sheet_name, last_row, group_by_col, group_by_header,
        value_col, value_header, aggregation, unique_count
    )

    summary_name = f"{group_by_header} Summary"
    chart_end_row = 1 + unique_count  # header row + unique values
    agg_upper = aggregation.upper()

    # Add chart action
    actions.append({
        "action": "createChart",
        "chartType": chart_type,
        "title": f"{agg_upper} of {value_header} by {group_by_header}",
        "dataSheet": summary_name,
        "labelColumn": "A",
        "valueColumn": "B",
        "startRow": 2,
        "endRow": chart_end_row
    })

    return actions


def template_add_column_to_existing(
    target_sheet: str,
    source_sheet: str,
    last_row: int,
    new_header: str,
    group_by_col: str,
    value_col: str,
    aggregation: str = "sum",
    existing_col_count: int = 2,
    unique_count: int = 10,
) -> List[Dict]:
    """
    Template for adding a column to an existing summary sheet.
    Instead of recreating the sheet, just adds the new column.
    """
    # The new column letter (after existing columns)
    new_col_letter = chr(ord('A') + existing_col_count)
    fill_down_row = 1 + unique_count

    # Choose formula based on aggregation type
    if aggregation == "count":
        formula = f"=COUNTIF('{source_sheet}'!{group_by_col}2:{group_by_col}{last_row}, A2)"
    elif aggregation == "avg":
        formula = f"=AVERAGEIF('{source_sheet}'!{group_by_col}2:{group_by_col}{last_row}, A2, '{source_sheet}'!{value_col}2:{value_col}{last_row})"
    elif aggregation == "max":
        formula = f"=MAXIFS('{source_sheet}'!{value_col}2:{value_col}{last_row}, '{source_sheet}'!{group_by_col}2:{group_by_col}{last_row}, A2)"
    elif aggregation == "min":
        formula = f"=MINIFS('{source_sheet}'!{value_col}2:{value_col}{last_row}, '{source_sheet}'!{group_by_col}2:{group_by_col}{last_row}, A2)"
    else:  # sum
        formula = f"=SUMIF('{source_sheet}'!{group_by_col}2:{group_by_col}{last_row}, A2, '{source_sheet}'!{value_col}2:{value_col}{last_row})"

    agg_upper = aggregation.upper()

    return [
        # Set the new header
        {
            "action": "setValues",
            "sheet": target_sheet,
            "range": f"{new_col_letter}1:{new_col_letter}1",
            "values": [[f"{agg_upper} of {new_header}"]],
        },
        # Format the new header to match
        {
            "action": "formatRange",
            "sheet": target_sheet,
            "range": f"{new_col_letter}1:{new_col_letter}1",
            "bold": True,
            "background": "#4472C4",
            "fontColor": "#FFFFFF",
        },
        # Set formula in the first data cell
        {
            "action": "setFormula",
            "sheet": target_sheet,
            "cell": f"{new_col_letter}2",
            "formula": formula,
        },
        # Fill down to match existing data
        {
            "action": "autoFillDown",
            "sheet": target_sheet,
            "sourceCell": f"{new_col_letter}2",
            "lastRow": fill_down_row,
        },
    ]


def template_multi_value_summary_chart(
    sheet_name: str,
    last_row: int,
    group_by_col: str,
    group_by_header: str,
    value_columns: List[tuple],  # [(col_letter, header_name), ...]
    chart_type: str = "bar",
    unique_count: int = 10
) -> List[Dict]:
    """
    Template for: "Chart of sales AND profits by region"
    Multiple value columns.
    """
    summary_name = f"{group_by_header} Summary"

    # Build headers
    headers = [group_by_header] + [f"Total {h}" for _, h in value_columns]
    header_range = f"A1:{chr(ord('A') + len(value_columns))}1"

    actions = [
        {"action": "createSheet", "name": summary_name},
        {"action": "setValues", "sheet": summary_name, "range": header_range,
         "values": [headers]},
        {"action": "formatRange", "sheet": summary_name, "range": header_range,
         "bold": True, "background": "#4472C4", "fontColor": "#FFFFFF"},
        {"action": "setFormula", "sheet": summary_name, "cell": "A2",
         "formula": f"=UNIQUE('{sheet_name}'!{group_by_col}2:{group_by_col}{last_row})"},
    ]

    # Add formula for each value column
    for i, (col_letter, col_header) in enumerate(value_columns):
        cell_col = chr(ord('B') + i)  # B, C, D, ...
        formula = f"=SUMIF('{sheet_name}'!{group_by_col}2:{group_by_col}{last_row}, A2, '{sheet_name}'!{col_letter}2:{col_letter}{last_row})"
        actions.append({
            "action": "setFormula",
            "sheet": summary_name,
            "cell": f"{cell_col}2",
            "formula": formula
        })

    fill_down_row = 1 + unique_count

    # Fill down each column
    for i in range(len(value_columns)):
        cell_col = chr(ord('B') + i)
        actions.append({
            "action": "autoFillDown",
            "sheet": summary_name,
            "sourceCell": f"{cell_col}2",
            "lastRow": fill_down_row
        })

    # Add chart (uses first value column)
    actions.append({
        "action": "createChart",
        "chartType": chart_type,
        "title": f"{group_by_header} Summary",
        "dataSheet": summary_name,
        "labelColumn": "A",
        "valueColumn": "B",
        "startRow": 2,
        "endRow": fill_down_row
    })

    return actions


def template_find_duplicates(
    sheet_name: str,
    last_row: int,
    columns_info: List[tuple],  # [(col_letter, header_name), ...]
    cells: Dict,
    highlight_color: str = "#FFCDD2",
) -> tuple:
    """
    Template for: "Find duplicate rows", "Show me duplicates"

    Scans cell data for duplicate values, highlights them in the original sheet,
    and creates a Duplicates Report sheet.

    Returns:
        (actions, response_text, chart_data) where chart_data is (labels, values, header) or None
    """
    import re as _re

    cell_pattern = _re.compile(r"^([A-Z]+)(\d+)$")

    # Build column_letter -> {value -> [row_numbers]} map
    col_letters = {letter for letter, _ in columns_info}
    col_duplicates = {}  # col_letter -> {value: [rows]}

    for ref, val in cells.items():
        m = cell_pattern.match(ref)
        if not m:
            continue
        col = m.group(1)
        row = int(m.group(2))
        if row < 2 or col not in col_letters:
            continue  # skip header row and irrelevant columns
        str_val = str(val).strip()
        if not str_val:
            continue
        if col not in col_duplicates:
            col_duplicates[col] = {}
        if str_val not in col_duplicates[col]:
            col_duplicates[col][str_val] = []
        col_duplicates[col][str_val].append(row)

    # Filter to values appearing 2+ times
    col_header_map = {letter: header for letter, header in columns_info}
    duplicate_entries = []  # [(value, column_header, count, rows_list)]
    highlight_rows = set()

    for col_letter in sorted(col_duplicates.keys()):
        for value, rows in col_duplicates[col_letter].items():
            if len(rows) >= 2:
                header = col_header_map.get(col_letter, col_letter)
                duplicate_entries.append((value, header, len(rows), sorted(rows)))
                highlight_rows.update(rows)

    if not duplicate_entries:
        return [], "No duplicate values found in the selected columns.", None

    # Sort by count descending
    duplicate_entries.sort(key=lambda x: x[2], reverse=True)

    # Build actions
    report_name = "Duplicates Report"
    actions = [
        {"action": "createSheet", "name": report_name},
        {
            "action": "setValues",
            "sheet": report_name,
            "range": "A1:D1",
            "values": [["Duplicate Value", "Column", "Count", "Found in Rows"]],
        },
        {
            "action": "formatRange",
            "sheet": report_name,
            "range": "A1:D1",
            "bold": True,
            "background": "#4472C4",
            "fontColor": "#FFFFFF",
        },
    ]

    # Batch all report rows into a single setValues
    report_rows = []
    for value, header, count, rows in duplicate_entries:
        rows_str = ", ".join(str(r) for r in rows[:20])
        if len(rows) > 20:
            rows_str += f" (+{len(rows) - 20} more)"
        report_rows.append([str(value), header, count, rows_str])

    if report_rows:
        end_row = 1 + len(report_rows)
        actions.append({
            "action": "setValues",
            "sheet": report_name,
            "range": f"A2:D{end_row}",
            "values": report_rows,
        })

    # Highlight duplicate rows in original sheet (light red)
    last_col = max(col_letters) if col_letters else "A"
    for row in sorted(highlight_rows):
        actions.append({
            "action": "formatRange",
            "sheet": sheet_name,
            "range": f"A{row}:{last_col}{row}",
            "background": highlight_color,
        })

    total_dupes = len(duplicate_entries)
    total_rows = len(highlight_rows)
    response = (
        f"Found **{total_dupes} duplicate value(s)** across **{total_rows} rows**. "
        f"Highlighted duplicate rows in red and created a '{report_name}' sheet with details."
    )

    # Build chart data for top duplicates
    chart_data = None
    top_entries = duplicate_entries[:15]
    if top_entries:
        labels = [f"{e[0][:20]} ({e[1]})" for e in top_entries]
        values = [e[2] for e in top_entries]
        chart_data = (labels, values, "Duplicate Count")

    return actions, response, chart_data


# =============================================================================
# CLASSIFIER PROMPT
# =============================================================================

CLASSIFIER_PROMPT = """You are a request classifier for a Google Sheets AI assistant.

Given the user's request and sheet metadata, classify it and extract parameters.

SHEET METADATA:
{sheet_metadata}

DATA SAMPLE (first rows):
{data_sample}

CONVERSATION HISTORY:
{history}

USER REQUEST: "{user_request}"

Classify into ONE of these types:
1. simple_question - User just wants information, no sheet modifications needed
2. grouped_summary - Sum/count/avg by category (e.g., "sum of sales by region")
3. grouped_summary_chart - Same as above but with chart (e.g., "chart of sales by region")
4. add_to_existing - User wants to ADD a column, modify, or extend something that was ALREADY created in a previous turn. Look for [ACTIONS PERFORMED] in conversation history. Include "target_sheet" (existing sheet name), "new_column_header", and optionally "value_column" (source data column letter), "aggregation".
5. top_n - Find top/bottom N values (e.g., "top 5 products by sales")
6. find_duplicates - Find duplicate rows. Include "duplicate_columns" (list of column letters to check, or null for all columns)
7. filter_highlight - Filter and highlight rows
8. complex - Anything else that needs custom handling
9. change_chart_type - User refers to an existing chart and wants a different chart type. Include "chart_type" and "summary_sheet" (the sheet name from conversation history where the chart was created).

IMPORTANT: If the conversation history contains [ACTIONS PERFORMED] showing that a sheet was already created,
and the user asks to "add a column", "also include", "add another", "also show", etc.,
classify as "add_to_existing" — NOT as grouped_summary (which would recreate from scratch).

RESPOND IN EXACT JSON FORMAT:
{{
  "request_type": "grouped_summary_chart",
  "group_by_column": "D",
  "group_by_header": "Region",
  "value_columns": [["F", "Sales"], ["G", "Profit"]],
  "aggregation": "sum",
  "chart_type": "bar",
  "explanation": "User wants sales and profits grouped by region with a chart"
}}

For simple_question, include "answer" field with the response.
For complex, include "plan" field with step-by-step actions.

IMPORTANT:
- Use actual column letters from metadata (A, B, C, etc.)
- Use actual header names from metadata
- For chart_type, use: bar, line, pie, doughnut, scatter
- For aggregation, use: sum, count, avg, max, min

JSON RESPONSE:"""


# =============================================================================
# SMART EXECUTOR CLASS
# =============================================================================

class SmartExecutor:
    """
    Executes user requests efficiently using classification + templates.
    """

    def __init__(self, llm):
        """
        Initialize with an LLM instance.

        Args:
            llm: LangChain LLM instance (ChatOpenAI or similar)
        """
        self.llm = llm

    def classify_request(
        self,
        user_request: str,
        sheet_metadata: Dict,
        history: list = None,
        cells: Dict = None,
    ) -> ClassifiedRequest:
        """
        Classify user request in ONE LLM call (with Redis caching).

        Returns:
            ClassifiedRequest with type and extracted parameters
        """
        # --- Phase 1B: Check classifier cache ---
        headers = [c.get("header", "") for c in sheet_metadata.get("columns", [])]
        col_types = [c.get("type", "") for c in sheet_metadata.get("columns", [])]
        cache_key = _classifier_cache_key(user_request, headers, col_types)

        cached = _get_cached_classification(cache_key)
        if cached:
            result = self._parse_classification_from_dict(cached)
            logger.info(f"Classified request (CACHED) as: {result.request_type}")
            return result

        # Format metadata for prompt
        metadata_str = self._format_metadata(sheet_metadata)

        # Format conversation history (last 3 exchanges, 200 chars each)
        history_str = "No prior conversation."
        if history:
            recent = history[-6:]  # last 3 exchanges (6 messages)
            lines = []
            for msg in recent:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]
                lines.append(f"{role}: {content}")
            history_str = "\n".join(lines)

        # Build data sample from first 5 data rows
        data_sample_str = "No cell data available."
        if cells:
            data_sample_str = self._build_data_sample(cells, sheet_metadata)

        # Build prompt
        prompt = CLASSIFIER_PROMPT.format(
            sheet_metadata=metadata_str,
            user_request=user_request,
            history=history_str,
            data_sample=data_sample_str,
        )

        # Call LLM
        try:
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Parse JSON response
            result = self._parse_classification(response_text)
            logger.info(f"Classified request as: {result.request_type}")

            # Cache the result (only for non-complex, non-history-dependent types)
            if result.request_type not in (RequestType.COMPLEX, RequestType.ADD_TO_EXISTING, RequestType.CHANGE_CHART_TYPE):
                try:
                    json_match = re.search(r'\{[\s\S]*\}', response_text)
                    if json_match:
                        _set_cached_classification(cache_key, json.loads(json_match.group()))
                except Exception:
                    pass

            return result

        except Exception as e:
            logger.error(f"Classification failed: {e}", exc_info=True)
            # Fall back to complex type — uses more LLM calls but ensures a response
            logger.warning("Falling back to COMPLEX request type due to classification error")
            return ClassifiedRequest(request_type=RequestType.COMPLEX)

    def execute(
        self,
        user_request: str,
        sheet_metadata: Dict,
        cells: Dict = None,
        history: list = None,
    ) -> Dict[str, Any]:
        """
        Execute user request with minimal LLM calls.

        Returns:
            Dict with:
            - actions: List of sheet actions to execute
            - response: Text response for user
            - llm_calls: Number of LLM calls used
            - chart_config: Optional Chart.js config for inline display
        """
        # Step 1: Classify (1 LLM call)
        classified = self.classify_request(
            user_request, sheet_metadata,
            history=history, cells=cells,
        )

        llm_calls = 1
        actions = []
        response = ""
        chart_config = None

        # Step 2: Execute based on type
        if classified.request_type == RequestType.SIMPLE_QUESTION:
            # No actions needed, just return answer
            response = classified.answer or "I can help with that. What would you like to know?"

        elif classified.request_type == RequestType.GROUPED_SUMMARY:
            actions, chart_config = self._execute_grouped_summary(classified, sheet_metadata, cells or {})
            response = self._build_smart_response(classified, sheet_metadata, "summary")

        elif classified.request_type == RequestType.GROUPED_SUMMARY_CHART:
            actions, chart_config = self._execute_grouped_summary_chart(classified, sheet_metadata, cells or {})
            response = self._build_smart_response(classified, sheet_metadata, "summary_chart")

        elif classified.request_type == RequestType.ADD_TO_EXISTING:
            actions = self._execute_add_to_existing(classified, sheet_metadata, history)
            col_name = classified.new_column_header or classified.value_column or "new column"
            target = classified.target_sheet or "existing sheet"
            response = f"Added **{col_name}** column to **{target}**."

        elif classified.request_type == RequestType.CHANGE_CHART_TYPE:
            actions, chart_config = self._execute_change_chart_type(classified, sheet_metadata, cells or {})
            response = f"Changed chart to **{classified.chart_type or 'line'}**."

        elif classified.request_type == RequestType.FIND_DUPLICATES:
            actions, response, chart_config = self._execute_find_duplicates(classified, sheet_metadata, cells or {})

        elif classified.request_type == RequestType.COMPLEX:
            # Fall back to plan from classifier or generate new plan
            if classified.custom_plan:
                actions = classified.custom_plan
                response = "Executed custom plan."
            else:
                # Need one more LLM call for planning
                actions, response = self._generate_plan(user_request, sheet_metadata)
                llm_calls += 1

        else:
            # Other types - implement as needed
            response = f"Request type {classified.request_type} - implementing..."

        return {
            "actions": actions,
            "response": response,
            "llm_calls": llm_calls,
            "request_type": classified.request_type.value,
            "chart_config": chart_config,
        }

    def _build_smart_response(
        self,
        classified: ClassifiedRequest,
        metadata: Dict,
        response_type: str,
    ) -> str:
        """Build a meaningful response using actual header names instead of column letters."""
        # Resolve header names from metadata
        group_header = classified.group_by_column or "category"
        value_header = classified.value_column or "value"
        agg = (classified.aggregation or "sum").upper()

        for col in metadata.get("columns", []):
            if col.get("letter") == classified.group_by_column:
                group_header = col.get("header", group_header)
            if col.get("letter") == classified.value_column:
                value_header = col.get("header", value_header)

        if response_type == "summary":
            return f"Created a **{group_header} Summary** sheet with {agg} of **{value_header}** grouped by **{group_header}**."
        elif response_type == "summary_chart":
            chart = classified.chart_type or "bar"
            return (
                f"Created a **{group_header} Summary** sheet with {agg} of **{value_header}** "
                f"grouped by **{group_header}**, plus a **{chart} chart**."
            )
        return f"Created summary of {value_header} by {group_header}."

    def _parse_classification_from_dict(self, data: Dict) -> ClassifiedRequest:
        """Build a ClassifiedRequest from a cached dict (no JSON parsing needed)."""
        type_str = data.get("request_type", "complex")
        try:
            request_type = RequestType(type_str)
        except ValueError:
            request_type = RequestType.COMPLEX

        return ClassifiedRequest(
            request_type=request_type,
            group_by_column=data.get("group_by_column"),
            value_column=data.get("value_columns", [[]])[0][0] if data.get("value_columns") else data.get("value_column"),
            aggregation=data.get("aggregation", "sum"),
            chart_type=data.get("chart_type", "bar"),
            n_value=data.get("n_value"),
            filter_column=data.get("filter_column"),
            filter_value=data.get("filter_value"),
            duplicate_columns=data.get("duplicate_columns"),
            custom_plan=data.get("plan"),
            answer=data.get("answer"),
            summary_sheet=data.get("summary_sheet"),
            target_sheet=data.get("target_sheet"),
            new_column_header=data.get("new_column_header"),
            new_column_formula=data.get("new_column_formula"),
        )

    def _format_metadata(self, metadata: Dict) -> str:
        """Format sheet metadata for prompt."""
        if not metadata:
            return "No metadata available"

        lines = [
            f"Sheet: {metadata.get('sheet_name', 'Sheet1')}",
            f"Rows: {metadata.get('total_rows', 'unknown')} (data rows: {metadata.get('data_rows', 'unknown')})",
            f"Last row: {metadata.get('last_row', 'unknown')}",
            "",
            "Columns:"
        ]

        for col in metadata.get('columns', []):
            col_info = f"  {col.get('letter', '?')}: {col.get('header', 'Unknown')}"
            col_info += f" ({col.get('type', 'text')}"
            if col.get('unique_count'):
                col_info += f", {col['unique_count']} unique"
            if col.get('categories'):
                col_info += f": {', '.join(col['categories'][:5])}"
            col_info += ")"
            lines.append(col_info)

        if metadata.get('suggested_group_by'):
            lines.append(f"\nGood for grouping: {', '.join(metadata['suggested_group_by'])}")
        if metadata.get('suggested_aggregate'):
            lines.append(f"Good for SUM/AVG: {', '.join(metadata['suggested_aggregate'])}")

        return "\n".join(lines)

    def _build_data_sample(self, cells: Dict, metadata: Dict) -> str:
        """Build a table of the first 5 data rows for the classifier prompt."""
        if not cells:
            return "No cell data available."

        cell_pattern = re.compile(r"^([A-Z]+)(\d+)$")

        # Collect all columns and rows
        col_rows: Dict[str, Dict[int, str]] = {}  # col_letter -> {row -> value}
        for ref, val in cells.items():
            m = cell_pattern.match(ref)
            if not m:
                continue
            col = m.group(1)
            row = int(m.group(2))
            if col not in col_rows:
                col_rows[col] = {}
            col_rows[col][row] = str(val)

        if not col_rows:
            return "No cell data available."

        # Sort columns alphabetically
        sorted_cols = sorted(col_rows.keys())

        # Build header row (row 1) and first 5 data rows (rows 2-6)
        rows_to_show = [1, 2, 3, 4, 5, 6]
        lines = []
        header_parts = ["Row"]
        for col in sorted_cols:
            header_val = col_rows.get(col, {}).get(1, col)
            header_parts.append(f"{col}:{header_val}")
        lines.append(" | ".join(header_parts))
        lines.append("-" * len(lines[0]))

        for row in rows_to_show[1:]:  # skip row 1 (header)
            parts = [str(row)]
            has_data = False
            for col in sorted_cols:
                val = col_rows.get(col, {}).get(row, "")
                if val:
                    has_data = True
                parts.append(str(val)[:30])  # truncate long values
            if has_data:
                lines.append(" | ".join(parts))

        return "\n".join(lines) if len(lines) > 2 else "No cell data available."

    def _parse_classification(self, response_text: str) -> ClassifiedRequest:
        """Parse LLM classification response."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if not json_match:
                raise ValueError("No JSON found in response")

            data = json.loads(json_match.group())

            # Map to RequestType
            type_str = data.get('request_type', 'complex')
            try:
                request_type = RequestType(type_str)
            except ValueError:
                request_type = RequestType.COMPLEX

            return ClassifiedRequest(
                request_type=request_type,
                group_by_column=data.get('group_by_column'),
                value_column=data.get('value_columns', [[]])[0][0] if data.get('value_columns') else data.get('value_column'),
                aggregation=data.get('aggregation', 'sum'),
                chart_type=data.get('chart_type', 'bar'),
                n_value=data.get('n_value'),
                filter_column=data.get('filter_column'),
                filter_value=data.get('filter_value'),
                duplicate_columns=data.get('duplicate_columns'),
                custom_plan=data.get('plan'),
                answer=data.get('answer'),
                summary_sheet=data.get('summary_sheet'),
                target_sheet=data.get('target_sheet'),
                new_column_header=data.get('new_column_header'),
                new_column_formula=data.get('new_column_formula'),
            )

        except Exception as e:
            logger.error(f"Failed to parse classification: {e}")
            return ClassifiedRequest(request_type=RequestType.COMPLEX)

    def _execute_grouped_summary(
        self,
        classified: ClassifiedRequest,
        metadata: Dict,
        cells: Dict = None,
    ) -> tuple:
        """Execute grouped summary template. Returns (actions, chart_config)."""
        # Find column info — use metadata suggestions instead of hardcoded A/B
        suggested_group = metadata.get('suggested_group_by', [])
        suggested_agg = metadata.get('suggested_aggregate', [])
        group_col = classified.group_by_column or (suggested_group[0] if suggested_group else "A")
        value_col = classified.value_column or (suggested_agg[0] if suggested_agg else "B")

        # Get headers from metadata
        group_header = "Category"
        value_header = "Value"
        unique_count = 10

        for col in metadata.get('columns', []):
            if col.get('letter') == group_col:
                group_header = col.get('header', group_col)
                unique_count = col.get('unique_count', 10)
            if col.get('letter') == value_col:
                value_header = col.get('header', value_col)

        actions = template_grouped_summary(
            sheet_name=metadata.get('sheet_name', 'Sheet1'),
            last_row=metadata.get('last_row', 100),
            group_by_col=group_col,
            group_by_header=group_header,
            value_col=value_col,
            value_header=value_header,
            aggregation=classified.aggregation or 'sum',
            unique_count=unique_count
        )

        # Build inline chart from cell data
        chart_config = self._build_inline_chart_from_cells(
            cells or {}, group_col, value_col, value_header,
            classified.aggregation or 'sum',
        )

        return actions, chart_config

    def _execute_grouped_summary_chart(
        self,
        classified: ClassifiedRequest,
        metadata: Dict,
        cells: Dict = None,
    ) -> tuple:
        """Execute grouped summary with chart template. Returns (actions, chart_config)."""
        # Use metadata suggestions instead of hardcoded A/B
        suggested_group = metadata.get('suggested_group_by', [])
        suggested_agg = metadata.get('suggested_aggregate', [])
        group_col = classified.group_by_column or (suggested_group[0] if suggested_group else "A")
        value_col = classified.value_column or (suggested_agg[0] if suggested_agg else "B")

        group_header = "Category"
        value_header = "Value"
        unique_count = 10

        for col in metadata.get('columns', []):
            if col.get('letter') == group_col:
                group_header = col.get('header', group_col)
                unique_count = col.get('unique_count', 10)
            if col.get('letter') == value_col:
                value_header = col.get('header', value_col)

        actions = template_grouped_summary_chart(
            sheet_name=metadata.get('sheet_name', 'Sheet1'),
            last_row=metadata.get('last_row', 100),
            group_by_col=group_col,
            group_by_header=group_header,
            value_col=value_col,
            value_header=value_header,
            aggregation=classified.aggregation or 'sum',
            chart_type=classified.chart_type or 'bar',
            unique_count=unique_count
        )

        # Build inline chart from cell data
        chart_config = self._build_inline_chart_from_cells(
            cells or {}, group_col, value_col, value_header,
            classified.aggregation or 'sum',
            chart_type=classified.chart_type or 'bar',
        )

        return actions, chart_config

    def _execute_add_to_existing(
        self,
        classified: ClassifiedRequest,
        metadata: Dict,
        history: list = None,
    ) -> List[Dict]:
        """Add a column to an existing summary sheet. Returns actions list."""
        target_sheet = classified.target_sheet
        source_sheet = metadata.get('sheet_name', 'Sheet1')
        last_row = metadata.get('last_row', 100)

        # If no target sheet specified, try to extract from history
        if not target_sheet and history:
            target_sheet = self._extract_existing_sheet_from_history(history)

        if not target_sheet:
            logger.warning("add_to_existing: no target sheet found, falling back to complex")
            return []

        # Determine new column details
        value_col = classified.value_column
        new_header = classified.new_column_header
        aggregation = classified.aggregation or 'sum'

        # If value_column not specified, try to infer from metadata
        if not value_col and new_header:
            for col in metadata.get('columns', []):
                if col.get('header', '').lower() == new_header.lower():
                    value_col = col.get('letter')
                    break

        if not value_col:
            # Use first suggested aggregate column
            suggested = metadata.get('suggested_aggregate', [])
            if suggested:
                value_col = suggested[0]
            else:
                logger.warning("add_to_existing: no value column found")
                return []

        if not new_header:
            # Use the header of the value column
            for col in metadata.get('columns', []):
                if col.get('letter') == value_col:
                    new_header = col.get('header', value_col)
                    break
            if not new_header:
                new_header = value_col

        # Count existing columns in target sheet from history
        existing_col_count = self._count_existing_columns_from_history(history, target_sheet)

        # Get group_by column (column A in summary sheet references this)
        group_by_col = classified.group_by_column
        if not group_by_col:
            suggested_group = metadata.get('suggested_group_by', [])
            group_by_col = suggested_group[0] if suggested_group else 'A'

        # Get unique count for fill-down
        unique_count = 10
        for col in metadata.get('columns', []):
            if col.get('letter') == group_by_col:
                unique_count = col.get('unique_count', 10)
                break

        return template_add_column_to_existing(
            target_sheet=target_sheet,
            source_sheet=source_sheet,
            last_row=last_row,
            new_header=new_header,
            group_by_col=group_by_col,
            value_col=value_col,
            aggregation=aggregation,
            existing_col_count=existing_col_count,
            unique_count=unique_count,
        )

    def _extract_existing_sheet_from_history(self, history: list) -> Optional[str]:
        """Extract the name of a previously created sheet from conversation history."""
        if not history:
            return None

        # Look for [ACTIONS PERFORMED] markers in assistant messages (newest first)
        for msg in reversed(history):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            # Parse [ACTIONS PERFORMED: Created sheets: Region Summary | ...]
            match = re.search(r'\[ACTIONS PERFORMED:.*?Created sheets:\s*([^|^\]]+)', content)
            if match:
                sheet_name = match.group(1).strip().rstrip(',').strip()
                if sheet_name:
                    return sheet_name
        return None

    def _count_existing_columns_from_history(self, history: list, target_sheet: str) -> int:
        """Count how many columns exist in the target sheet based on history markers."""
        if not history:
            return 2  # default: assume group column + 1 value column

        for msg in reversed(history):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            # Parse headers info: "SheetName headers: ['Col1', 'Col2', ...]"
            pattern = re.escape(target_sheet) + r"\s+headers:\s*\[([^\]]+)\]"
            match = re.search(pattern, content)
            if match:
                headers_str = match.group(1)
                # Count comma-separated items
                headers = [h.strip().strip("'\"") for h in headers_str.split(",")]
                return len(headers)

        return 2  # default assumption

    def _execute_change_chart_type(
        self,
        classified: ClassifiedRequest,
        metadata: Dict,
        cells: Dict,
    ) -> tuple:
        """Change an existing chart's type without recreating summary data.
        Returns (actions, chart_config)."""
        summary_sheet = classified.summary_sheet

        # Fallback: derive summary sheet name from metadata columns
        if not summary_sheet:
            group_col = classified.group_by_column
            if group_col:
                for col in metadata.get('columns', []):
                    if col.get('letter') == group_col:
                        summary_sheet = col.get('header', 'Category') + " Summary"
                        break
            if not summary_sheet:
                summary_sheet = metadata.get('sheet_name', 'Sheet1') + " Summary"

        chart_type = classified.chart_type or "line"

        actions = [
            {"action": "deleteCharts", "sheet": summary_sheet},
            {
                "action": "createChart",
                "chartType": chart_type,
                "title": "Chart",
                "dataSheet": summary_sheet,
                "labelColumn": "A",
                "valueColumn": "B",
                "startRow": 2,
                "endRow": 100,
            },
        ]

        # Build inline chart from cells if we have context
        chart_config = None
        group_col = classified.group_by_column
        value_col = classified.value_column
        if group_col and value_col:
            chart_config = self._build_inline_chart_from_cells(
                cells, group_col, value_col, "Value",
                classified.aggregation or "sum",
                chart_type=chart_type,
            )

        return actions, chart_config

    def _build_inline_chart(self, labels, values, value_header, chart_type="bar"):
        """Build a Chart.js config for inline display in the chat message."""
        colors = [
            "#10B981", "#06B6D4", "#F59E0B", "#EF4444",
            "#8B5CF6", "#4F46E5", "#EC4899", "#F97316",
            "#14B8A6", "#6366F1", "#D946EF", "#84CC16",
        ]
        n = len(labels[:15])
        if not n:
            return None

        is_multi = chart_type in ("pie", "doughnut")
        return {
            "type": chart_type if chart_type in ("bar", "line", "pie", "doughnut") else "bar",
            "data": {
                "labels": labels[:15],
                "datasets": [{
                    "label": value_header,
                    "data": values[:15],
                    "backgroundColor": colors[:n] if is_multi else colors[0],
                    "borderColor": colors[0],
                    "borderWidth": 1,
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {"legend": {"display": is_multi}},
            },
        }

    def _build_inline_chart_from_cells(
        self, cells, group_col, value_col, value_header, aggregation, chart_type="bar"
    ):
        """Aggregate cell data and build an inline chart config."""
        if not cells:
            return None

        cell_pattern = re.compile(r"^([A-Z]+)(\d+)$")

        # Parse group and value columns from cells
        group_values = {}  # row -> group_value
        value_values = {}  # row -> numeric_value
        for ref, val in cells.items():
            m = cell_pattern.match(ref)
            if not m:
                continue
            col = m.group(1)
            row = int(m.group(2))
            if row < 2:
                continue
            if col == group_col:
                group_values[row] = str(val).strip()
            elif col == value_col:
                try:
                    value_values[row] = float(str(val).replace(",", "").replace("$", "").replace("%", ""))
                except (ValueError, TypeError):
                    pass

        if not group_values:
            return None

        # Aggregate by group
        aggregated = {}  # group -> [values]
        for row, group in group_values.items():
            if not group:
                continue
            if group not in aggregated:
                aggregated[group] = []
            if row in value_values:
                aggregated[group].append(value_values[row])

        if not aggregated:
            return None

        # Compute aggregation
        results = {}
        for group, vals in aggregated.items():
            if not vals:
                if aggregation == "count":
                    results[group] = len([r for r, g in group_values.items() if g == group])
                continue
            if aggregation == "sum":
                results[group] = sum(vals)
            elif aggregation == "count":
                results[group] = len([r for r, g in group_values.items() if g == group])
            elif aggregation == "avg":
                results[group] = sum(vals) / len(vals)
            elif aggregation == "max":
                results[group] = max(vals)
            elif aggregation == "min":
                results[group] = min(vals)
            else:
                results[group] = sum(vals)

        if not results:
            return None

        # Sort by value descending
        sorted_items = sorted(results.items(), key=lambda x: x[1], reverse=True)
        labels = [item[0] for item in sorted_items]
        values = [round(item[1], 2) for item in sorted_items]

        return self._build_inline_chart(labels, values, value_header, chart_type)

    def _execute_find_duplicates(
        self,
        classified: ClassifiedRequest,
        metadata: Dict,
        cells: Dict,
    ) -> tuple:
        """Execute find duplicates template. Returns (actions, response, chart_config)."""
        sheet_name = metadata.get('sheet_name', 'Sheet1')
        last_row = metadata.get('last_row', 100)

        # Build columns_info from metadata
        columns_info = []
        for col in metadata.get('columns', []):
            columns_info.append((col.get('letter', 'A'), col.get('header', 'Column')))

        # Filter to specific columns if requested
        if classified.duplicate_columns:
            requested = set(classified.duplicate_columns)
            columns_info = [(letter, header) for letter, header in columns_info if letter in requested]

        if not columns_info:
            return [], "No columns found to check for duplicates.", None

        actions, response, chart_data = template_find_duplicates(
            sheet_name=sheet_name,
            last_row=last_row,
            columns_info=columns_info,
            cells=cells,
        )

        # Build inline chart from duplicate data
        chart_config = None
        if chart_data:
            labels, values, header = chart_data
            chart_config = self._build_inline_chart(labels, values, header, "bar")

        return actions, response, chart_config

    def _generate_plan(
        self,
        user_request: str,
        metadata: Dict
    ) -> tuple[List[Dict], str]:
        """
        Generate custom plan for complex requests.
        This is the fallback when templates don't apply.
        """
        # This would be another LLM call to generate a complete plan
        # For now, return empty and let the old agent handle it
        logger.warning("Complex request - falling back to ReAct agent")
        return [], "This request requires the full agent. Processing..."


# =============================================================================
# HELPER FUNCTION
# =============================================================================

def create_smart_executor(llm) -> SmartExecutor:
    """Factory function to create SmartExecutor."""
    return SmartExecutor(llm)
