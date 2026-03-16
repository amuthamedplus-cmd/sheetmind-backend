"""
Response Enhancer — Adds polish and intelligence to AI responses.

Features:
1. Smart follow-up suggestions (context-aware, not generic)
2. Performance tips for heavy operations
3. Data quality callouts
4. Response timing badges ("Fast", "Thorough")
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def enhance_response(
    ai_response: str,
    actions: List[Dict],
    metadata: Optional[Dict],
    timing: Optional[Dict],
    user_message: str,
) -> Dict[str, Any]:
    """
    Enhance an AI response with additional context and suggestions.

    Returns dict of enhancements to merge into the ChatResponse.
    """
    enhancements: Dict[str, Any] = {}

    # 1. Performance badge
    if timing:
        total_ms = timing.get("total_ms", 0)
        if total_ms < 2000:
            enhancements["speed_badge"] = "instant"
        elif total_ms < 5000:
            enhancements["speed_badge"] = "fast"
        elif total_ms < 10000:
            enhancements["speed_badge"] = "normal"
        else:
            enhancements["speed_badge"] = "thorough"

    # 2. Action summary for the user (human-readable)
    if actions:
        summary = _build_human_summary(actions)
        if summary:
            enhancements["action_summary"] = summary

    # 3. Smart follow-up suggestions
    suggestions = _generate_smart_suggestions(
        user_message, actions, metadata, ai_response
    )
    if suggestions:
        enhancements["followup_suggestions"] = suggestions

    # 4. Data insights (only on first interaction or when new patterns detected)
    if metadata:
        insights = _detect_interesting_patterns(metadata, user_message)
        if insights:
            enhancements["data_insights"] = insights

    return enhancements


def _build_human_summary(actions: List[Dict]) -> Optional[str]:
    """Build a concise, human-friendly summary of what actions will do."""
    if not actions:
        return None

    parts = []
    sheets = set()
    formulas = 0
    charts = 0
    formats = 0

    for a in actions:
        act = a.get("action", "")
        if act == "createSheet":
            sheets.add(a.get("name", "new sheet"))
        elif act in ("setFormula", "autoFillDown"):
            formulas += 1
        elif act == "createChart":
            charts += 1
            chart_type = a.get("chartType", "chart")
            parts.append(f"Created a {chart_type} chart")
        elif act in ("formatRange", "conditionalFormat"):
            formats += 1

    if sheets:
        parts.insert(0, f"Created {'sheet' if len(sheets) == 1 else 'sheets'}: {', '.join(sheets)}")
    if formulas:
        parts.append(f"Set up {formulas} formula{'s' if formulas > 1 else ''}")
    if formats:
        parts.append(f"Applied {formats} formatting rule{'s' if formats > 1 else ''}")

    return " · ".join(parts) if parts else None


def _generate_smart_suggestions(
    user_message: str,
    actions: List[Dict],
    metadata: Optional[Dict],
    ai_response: str,
) -> List[Dict]:
    """Generate contextual follow-up suggestions based on what just happened."""
    suggestions = []

    has_summary = any(
        a.get("action") == "createSheet" and "summary" in (a.get("name") or "").lower()
        for a in actions
    )
    has_chart = any(a.get("action") == "createChart" for a in actions)
    has_formulas = any(a.get("action") == "setFormula" for a in actions)
    has_conditional = any(a.get("action") == "conditionalFormat" for a in actions)

    # Context-aware suggestions
    if has_summary and not has_chart:
        suggestions.append({
            "label": "Visualize this",
            "prompt": "Create a chart from this summary",
            "icon": "chart",
        })

    if has_summary:
        suggestions.append({
            "label": "Add more data",
            "prompt": "Add another column to the summary",
            "icon": "plus",
        })

    if has_chart:
        chart_types = [a.get("chartType") for a in actions if a.get("action") == "createChart"]
        alt_type = "pie" if "bar" in chart_types else "bar"
        suggestions.append({
            "label": f"Try {alt_type} chart",
            "prompt": f"Change the chart to {alt_type}",
            "icon": "swap",
        })

    if has_formulas and not has_conditional:
        suggestions.append({
            "label": "Highlight outliers",
            "prompt": "Highlight the top and bottom values with colors",
            "icon": "palette",
        })

    # Metadata-driven suggestions
    if metadata:
        date_cols = [
            c for c in metadata.get("columns", [])
            if c.get("type") == "date"
        ]
        if date_cols and "trend" not in user_message.lower() and "time" not in user_message.lower():
            col_name = date_cols[0].get("header", "date")
            suggestions.append({
                "label": "Show trends",
                "prompt": f"Show trends over time using {col_name}",
                "icon": "trending",
            })

        # If there are multiple group-by columns, suggest a different grouping
        group_cols = metadata.get("suggested_group_by", [])
        if len(group_cols) >= 2 and has_summary:
            col_info = metadata.get("columns", [])
            for gc in group_cols:
                header = next(
                    (c.get("header") for c in col_info if c.get("letter") == gc),
                    gc,
                )
                if header.lower() not in user_message.lower():
                    suggestions.append({
                        "label": f"Group by {header}",
                        "prompt": f"Create a summary grouped by {header}",
                        "icon": "layers",
                    })
                    break

    if not actions and not has_formulas:
        # Pure Q&A response — suggest actionable follow-ups
        suggestions.append({
            "label": "Create from this",
            "prompt": "Create a summary sheet based on this analysis",
            "icon": "sparkle",
        })

    # Deduplicate and limit
    seen = set()
    unique = []
    for s in suggestions:
        key = s["prompt"]
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique[:3]


def _detect_interesting_patterns(
    metadata: Dict,
    user_message: str,
) -> List[Dict]:
    """Detect interesting data patterns worth surfacing to the user."""
    insights = []

    if not metadata:
        return insights

    columns = metadata.get("columns", [])
    total_rows = metadata.get("data_rows", 0)

    for col in columns:
        col_type = col.get("type", "")
        header = col.get("header", col.get("letter", "?"))
        unique = col.get("unique_count", 0)

        # High cardinality detection (likely ID)
        if total_rows > 0 and unique == total_rows and col_type != "date":
            insights.append({
                "type": "info",
                "text": f"'{header}' has all unique values — likely an ID column",
            })

        # Low cardinality categorical (great for grouping)
        if col_type == "categorical" and unique <= 5 and unique >= 2:
            insights.append({
                "type": "tip",
                "text": f"'{header}' has only {unique} categories — perfect for grouping",
            })

        # Numeric outlier detection
        if col_type == "numeric":
            col_min = col.get("min")
            col_max = col.get("max")
            col_avg = col.get("avg")
            if col_min is not None and col_max is not None and col_avg is not None:
                spread = col_max - col_min
                if col_avg != 0 and spread / abs(col_avg) > 10:
                    insights.append({
                        "type": "warning",
                        "text": f"'{header}' has extreme spread (min={col_min}, max={col_max}) — may contain outliers",
                    })

        # Empty column warning
        null_count = col.get("null_count", 0)
        if total_rows > 0 and null_count / total_rows > 0.5:
            pct = int(null_count / total_rows * 100)
            insights.append({
                "type": "warning",
                "text": f"'{header}' is {pct}% empty — may affect analysis accuracy",
            })

    return insights[:4]  # Limit to avoid info overload
