"""
Confidence Score Algorithm for SheetMind.

Calculates a 0-100 score based on multiple factors and maps it to a tier:
  - Green (90-100): High confidence — trust this output
  - Yellow (70-89): Medium confidence — recommend verification
  - Red (<70): Low confidence — manual review required
"""


def _data_completeness_score(sheet_data: dict | None) -> float:
    """Score based on how complete the provided data is (0-100)."""
    if not sheet_data:
        return 30.0  # No data context = low confidence

    total_cells = 0
    filled_cells = 0

    rows = sheet_data.get("rows", [])
    values = sheet_data.get("values", [])

    # Ensure we actually have a list (callers may pass dicts or strings)
    if not isinstance(rows, list):
        rows = []
    if not isinstance(values, list):
        values = []

    data = rows if rows else values
    if not data:
        return 40.0

    for row in data:
        if isinstance(row, list):
            total_cells += len(row)
            filled_cells += sum(1 for cell in row if cell is not None and str(cell).strip() != "")
        else:
            total_cells += 1
            if row is not None and str(row).strip() != "":
                filled_cells += 1

    if total_cells == 0:
        return 40.0

    completeness = filled_cells / total_cells
    return 40.0 + (completeness * 60.0)  # Range: 40-100


def _data_volume_score(sheet_data: dict | None) -> float:
    """Score based on how much data was provided (more data = higher confidence)."""
    if not sheet_data:
        return 30.0

    rows = sheet_data.get("rows", [])
    values = sheet_data.get("values", [])
    if not isinstance(rows, list):
        rows = []
    if not isinstance(values, list):
        values = []
    row_count = len(rows) if rows else len(values)

    if row_count == 0:
        return 30.0
    elif row_count <= 3:
        return 50.0
    elif row_count <= 10:
        return 70.0
    elif row_count <= 50:
        return 85.0
    else:
        return 95.0


def _query_complexity_score(message: str) -> float:
    """Score based on query complexity (simpler = more confident)."""
    message_lower = message.lower()

    # Simple lookups / direct questions = high confidence
    simple_keywords = ["what is", "show me", "list", "count", "sum", "average", "total"]
    if any(kw in message_lower for kw in simple_keywords):
        return 90.0

    # Moderate analysis
    moderate_keywords = ["compare", "trend", "change", "growth", "difference", "breakdown"]
    if any(kw in message_lower for kw in moderate_keywords):
        return 75.0

    # Complex analysis / predictions = lower confidence
    complex_keywords = ["predict", "forecast", "why", "cause", "recommend", "suggest", "should"]
    if any(kw in message_lower for kw in complex_keywords):
        return 55.0

    return 70.0  # Default for unclassified queries


def _response_quality_score(response: str) -> float:
    """Score based on response characteristics."""
    if not response or len(response.strip()) < 10:
        return 40.0

    # Cap input to avoid expensive regex on huge responses
    sample = response[:10_000]

    score = 70.0

    # Contains specific numbers = better
    import re
    numbers = re.findall(r'\d+\.?\d*', sample)
    if numbers:
        score += 10.0

    # Contains row/cell references = better (verifiable)
    ref_patterns = [r'[Rr]ow\s*\d+', r'[Cc]ell\s*[A-Z]+\d+', r'[A-Z]+\d+:[A-Z]+\d+']
    has_references = any(re.search(p, sample) for p in ref_patterns)
    if has_references:
        score += 10.0

    # Very short response for a complex query might be suspect
    if len(response) < 50:
        score -= 10.0

    return max(min(score, 100.0), 0.0)


def calculate_confidence(
    message: str,
    response: str,
    sheet_data: dict | None = None,
) -> dict:
    """
    Calculate confidence score for an AI response.

    Returns:
        {
            "score": float (0-100),
            "tier": "green" | "yellow" | "red",
            "factors": { ... breakdown ... }
        }
    """
    completeness = _data_completeness_score(sheet_data)
    volume = _data_volume_score(sheet_data)
    complexity = _query_complexity_score(message)
    quality = _response_quality_score(response)

    # Weighted average
    score = (
        completeness * 0.25
        + volume * 0.20
        + complexity * 0.30
        + quality * 0.25
    )

    score = round(min(max(score, 0), 100), 1)

    if score >= 90:
        tier = "green"
    elif score >= 70:
        tier = "yellow"
    else:
        tier = "red"

    return {
        "score": score,
        "tier": tier,
        "factors": {
            "data_completeness": round(completeness, 1),
            "data_volume": round(volume, 1),
            "query_complexity": round(complexity, 1),
            "response_quality": round(quality, 1),
        },
    }
