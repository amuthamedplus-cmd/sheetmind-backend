import json
import logging
import re

from app.services.ai_provider import generate_chart_config

logger = logging.getLogger(__name__)

MAX_ROWS = 100

DEFAULT_COLORS = [
    "#4F46E5", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#06B6D4", "#F97316", "#EC4899",
]


def detect_chart_type(data: dict) -> str:
    """Heuristic chart-type detection based on the data shape.

    - Pie/doughnut for small categorical data (≤ 8 categories, single numeric column).
    - Line for time-series (first column looks like dates).
    - Bar as the default fallback.
    """
    headers = data.get("headers", [])
    rows = data.get("rows", [])

    if not rows or not headers:
        return "bar"

    # Check if first column looks like dates/time-series
    date_pattern = re.compile(
        r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}"  # 2024-01-15 or 2024/1/15
        r"|^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"  # 01-15-2024
        r"|^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
        re.IGNORECASE,
    )

    first_col_values = [str(row[0]) for row in rows if row]
    date_matches = sum(1 for v in first_col_values if date_pattern.match(v))
    if date_matches > len(first_col_values) * 0.6:
        return "line"

    # Small categorical → pie
    if len(rows) <= 8 and len(headers) == 2:
        return "pie"

    return "bar"


def _build_fallback_config(
    data: dict,
    chart_type: str,
    title: str | None = None,
) -> dict:
    """Build a minimal Chart.js config without AI when AI output is unparsable."""
    headers = data.get("headers", [])
    rows = data.get("rows", [])

    labels = [str(row[0]) for row in rows if row] if rows else []

    datasets = []
    for col_idx in range(1, len(headers)):
        values = []
        for row in rows:
            if col_idx < len(row):
                try:
                    values.append(float(row[col_idx]))
                except (ValueError, TypeError):
                    values.append(0)
            else:
                values.append(0)

        ds = {
            "label": headers[col_idx] if col_idx < len(headers) else f"Series {col_idx}",
            "data": values,
        }

        if chart_type in ("pie", "doughnut"):
            ds["backgroundColor"] = DEFAULT_COLORS[: len(values)]
        else:
            ds["backgroundColor"] = DEFAULT_COLORS[(col_idx - 1) % len(DEFAULT_COLORS)]

        datasets.append(ds)

    return {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": datasets,
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": bool(title),
                    "text": title or "",
                },
            },
        },
    }


def generate_chart(
    data: dict,
    chart_type: str | None = None,
    title: str | None = None,
) -> dict:
    """Generate a Chart.js config from spreadsheet data via AI, with fallback.

    Returns a dict containing the Chart.js configuration.
    """
    # Truncate to MAX_ROWS
    truncated = dict(data)
    if "rows" in truncated and len(truncated["rows"]) > MAX_ROWS:
        truncated["rows"] = truncated["rows"][:MAX_ROWS]

    resolved_type = chart_type or detect_chart_type(truncated)

    try:
        raw = generate_chart_config(truncated, chart_type=resolved_type, title=title)
    except RuntimeError:
        logger.warning("AI chart generation failed, using fallback config")
        return _build_fallback_config(truncated, resolved_type, title)

    # Parse AI response
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        config = json.loads(cleaned)
        # Ensure the type field is set
        if "type" not in config:
            config["type"] = resolved_type
        return config
    except (json.JSONDecodeError, IndexError):
        logger.warning("Could not parse AI chart response, using fallback config")
        return _build_fallback_config(truncated, resolved_type, title)
