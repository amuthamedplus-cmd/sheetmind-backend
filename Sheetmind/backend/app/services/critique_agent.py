"""
Critique Agent — Reviews AI responses before they reach the user.

This agent acts as a quality gate that:
1. Validates formulas in the action plan
2. Detects missing considerations (edge cases, empty rows, data type mismatches)
3. Suggests better alternatives (faster formulas, simpler approaches)
4. Generates proactive insights about the data
5. Adds smart follow-up suggestions

The critique runs in parallel with response assembly to avoid blocking.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Formula Critique Rules
# ---------------------------------------------------------------------------

_FORMULA_ISSUES = [
    {
        "pattern": re.compile(r"SUMIF\(.+?,\s*.+?,\s*.+?\*.+?\)", re.IGNORECASE),
        "issue": "SUMIF sum_range cannot contain arithmetic",
        "fix": "Use SUMPRODUCT((criteria_range=criteria)*(val1*val2)) instead",
        "severity": "error",
    },
    {
        "pattern": re.compile(r"[A-Z]+:[A-Z]+", re.IGNORECASE),
        "issue": "Full column references (e.g., A:A) are slow on large sheets",
        "fix": "Use bounded ranges like A2:A{last_row}",
        "severity": "warning",
    },
    {
        "pattern": re.compile(r"VLOOKUP\("),
        "issue": "VLOOKUP only searches left-to-right",
        "fix": "Consider INDEX/MATCH for more flexibility",
        "severity": "suggestion",
    },
    {
        "pattern": re.compile(r"fillDown.*true.*UNIQUE", re.IGNORECASE | re.DOTALL),
        "issue": "UNIQUE auto-spills — fillDown will cause errors",
        "fix": "Remove fillDown for UNIQUE/FILTER formulas",
        "severity": "error",
    },
    {
        "pattern": re.compile(r"CONCATENATE\("),
        "issue": "CONCATENATE is verbose",
        "fix": "Use & operator or TEXTJOIN for cleaner formulas",
        "severity": "suggestion",
    },
]

# ---------------------------------------------------------------------------
# Data Insight Patterns
# ---------------------------------------------------------------------------

_INSIGHT_TEMPLATES = [
    {
        "condition": lambda meta: meta.get("total_rows", 0) > 1000,
        "insight": "Large dataset ({total_rows} rows) — formulas using bounded ranges for speed.",
        "icon": "speed",
    },
    {
        "condition": lambda meta: any(
            c.get("null_count", 0) > c.get("unique_count", 1) * 0.1
            for c in meta.get("columns", [])
            if c.get("type") == "numeric"
        ),
        "insight": "Some numeric columns have empty cells — aggregation formulas will skip blanks automatically.",
        "icon": "info",
    },
    {
        "condition": lambda meta: any(
            c.get("unique_count", 0) == meta.get("data_rows", 0)
            for c in meta.get("columns", [])
        ),
        "insight": "Detected a column with all unique values (likely an ID column) — excluded from grouping suggestions.",
        "icon": "smart",
    },
    {
        "condition": lambda meta: any(
            c.get("type") == "date" for c in meta.get("columns", [])
        ),
        "insight": "Date column detected — you can ask for time-based analysis like monthly trends.",
        "icon": "calendar",
    },
    {
        "condition": lambda meta: len(meta.get("suggested_group_by", [])) >= 2,
        "insight": "Multiple categorical columns found — you can create cross-tabulations (pivot-style analysis).",
        "icon": "grid",
    },
]


# ---------------------------------------------------------------------------
# Critique Agent Class
# ---------------------------------------------------------------------------

class CritiqueAgent:
    """Reviews and enhances AI responses before delivery."""

    def __init__(self, metadata: Optional[Dict] = None):
        self.metadata = metadata or {}
        self.critiques: List[Dict] = []
        self.insights: List[Dict] = []
        self.suggestions: List[str] = []

    def critique_actions(self, actions: List[Dict]) -> "CritiqueResult":
        """
        Review a list of sheet actions for issues and improvements.

        Returns CritiqueResult with issues, fixes, and suggestions.
        """
        self.critiques = []
        issues_found = 0
        auto_fixes = []

        for i, action in enumerate(actions):
            act_type = action.get("action", "")
            formula = action.get("formula", "")

            # Check formulas in setFormula actions
            if act_type == "setFormula" and formula:
                for rule in _FORMULA_ISSUES:
                    if rule["pattern"].search(formula):
                        self.critiques.append({
                            "step": i + 1,
                            "severity": rule["severity"],
                            "issue": rule["issue"],
                            "fix": rule["fix"],
                            "action": act_type,
                        })
                        if rule["severity"] == "error":
                            issues_found += 1

            # Check for fillDown + UNIQUE conflict
            if act_type == "autoFillDown":
                source_cell = action.get("sourceCell", "")
                # Look back for the formula that was set in this cell
                for prev in actions[:i]:
                    if (prev.get("action") == "setFormula"
                            and prev.get("cell") == source_cell
                            and "UNIQUE" in prev.get("formula", "").upper()):
                        self.critiques.append({
                            "step": i + 1,
                            "severity": "error",
                            "issue": "autoFillDown on a UNIQUE formula will cause errors",
                            "fix": "Remove this autoFillDown — UNIQUE auto-spills",
                            "action": act_type,
                        })
                        auto_fixes.append({
                            "step": i,
                            "fix": "remove",
                            "reason": "UNIQUE auto-spills",
                        })
                        issues_found += 1

            # Check for duplicate createSheet actions
            if act_type == "createSheet":
                sheet_name = action.get("name", "")
                duplicates = [
                    j for j, a in enumerate(actions[:i])
                    if a.get("action") == "createSheet" and a.get("name") == sheet_name
                ]
                if duplicates:
                    self.critiques.append({
                        "step": i + 1,
                        "severity": "warning",
                        "issue": f"Sheet '{sheet_name}' created multiple times",
                        "fix": "Remove duplicate createSheet action",
                        "action": act_type,
                    })

            # Check for setValues overwriting formulas
            if act_type == "setValues":
                target_range = action.get("range", "")
                target_sheet = action.get("sheet", "")
                for prev in actions[:i]:
                    if (prev.get("action") == "setFormula"
                            and prev.get("sheet") == target_sheet):
                        prev_cell = prev.get("cell", "")
                        if prev_cell and prev_cell in _expand_range(target_range):
                            self.critiques.append({
                                "step": i + 1,
                                "severity": "warning",
                                "issue": f"setValues on {target_range} may overwrite formula in {prev_cell}",
                                "fix": "Adjust range to avoid overwriting formulas",
                                "action": act_type,
                            })

        return CritiqueResult(
            critiques=self.critiques,
            issues_found=issues_found,
            auto_fixes=auto_fixes,
        )

    def generate_insights(self) -> List[Dict]:
        """Generate proactive data insights based on sheet metadata."""
        self.insights = []

        if not self.metadata:
            return self.insights

        for template in _INSIGHT_TEMPLATES:
            try:
                if template["condition"](self.metadata):
                    insight_text = template["insight"].format(
                        total_rows=self.metadata.get("total_rows", "?"),
                        data_rows=self.metadata.get("data_rows", "?"),
                    )
                    self.insights.append({
                        "text": insight_text,
                        "icon": template["icon"],
                    })
            except (KeyError, TypeError, ValueError):
                continue

        return self.insights

    def suggest_followups(
        self,
        user_message: str,
        actions: List[Dict],
        ai_response: str,
    ) -> List[str]:
        """
        Generate smart follow-up suggestions based on what was just done.
        These are contextual — not generic "what else can I help with?" filler.
        """
        self.suggestions = []

        # Analyze what was created
        sheets_created = [a.get("name") for a in actions if a.get("action") == "createSheet"]
        has_chart = any(a.get("action") == "createChart" for a in actions)
        has_formulas = any(a.get("action") == "setFormula" for a in actions)
        has_summary = any("summary" in (a.get("name") or "").lower() for a in actions if a.get("action") == "createSheet")
        has_format = any(a.get("action") in ("formatRange", "conditionalFormat") for a in actions)

        # Contextual suggestions based on what was just done
        if has_summary and not has_chart:
            self.suggestions.append("Add a chart to visualize this summary")

        if has_chart:
            chart_types = [a.get("chartType", "") for a in actions if a.get("action") == "createChart"]
            if "bar" in chart_types:
                self.suggestions.append("Switch to a pie chart view")
            elif "pie" in chart_types:
                self.suggestions.append("Switch to a bar chart view")

        if has_summary:
            self.suggestions.append("Add another column to the summary")

        if has_formulas and not has_format:
            self.suggestions.append("Apply conditional formatting to highlight key values")

        # Data-driven suggestions from metadata
        if self.metadata:
            date_cols = [
                c.get("header") for c in self.metadata.get("columns", [])
                if c.get("type") == "date"
            ]
            if date_cols and "trend" not in user_message.lower():
                self.suggestions.append(f"Show trend over time using {date_cols[0]}")

            numeric_cols = self.metadata.get("suggested_aggregate", [])
            if len(numeric_cols) >= 2:
                self.suggestions.append("Compare multiple metrics side by side")

            group_cols = self.metadata.get("suggested_group_by", [])
            if len(group_cols) >= 2 and has_summary:
                used_groups = set()
                for a in actions:
                    formula = a.get("formula", "")
                    for gc in group_cols:
                        if f"!{gc}" in formula:
                            used_groups.add(gc)
                unused = [g for g in group_cols if g not in used_groups]
                if unused:
                    col_info = self.metadata.get("columns", [])
                    for uc in unused[:1]:
                        header = next(
                            (c.get("header") for c in col_info if c.get("letter") == uc),
                            uc,
                        )
                        self.suggestions.append(f"Group by {header} instead")

        # Limit to 3 most relevant
        return self.suggestions[:3]

    def critique_response_text(self, ai_response: str) -> List[Dict]:
        """
        Review the AI's text response for quality issues.
        """
        text_issues = []

        # Check for vague/unhelpful responses
        vague_patterns = [
            (r"I (?:can't|cannot|am unable to)", "AI refused to help — may need prompt adjustment"),
            (r"(?:I'm not sure|I don't know) (?:how|what|which)", "AI expressed uncertainty — may need more context"),
            (r"you (?:could|might|may) (?:want|need|try) to", "AI gave vague suggestion instead of direct action"),
        ]

        for pattern, issue in vague_patterns:
            if re.search(pattern, ai_response, re.IGNORECASE):
                text_issues.append({
                    "severity": "warning",
                    "issue": issue,
                    "context": re.search(pattern, ai_response, re.IGNORECASE).group(0),
                })

        # Check for formula in text that should be an action
        formula_in_text = re.findall(r'=\w+\([^)]+\)', ai_response)
        if formula_in_text and not any(
            a.get("action") == "setFormula"
            for a in []  # placeholder — caller should pass actions
        ):
            text_issues.append({
                "severity": "suggestion",
                "issue": f"Response contains formula(s) as text — consider executing them as actions",
                "context": formula_in_text[0][:80],
            })

        return text_issues


class CritiqueResult:
    """Result of critiquing an action plan."""

    def __init__(
        self,
        critiques: List[Dict],
        issues_found: int = 0,
        auto_fixes: List[Dict] = None,
    ):
        self.critiques = critiques
        self.issues_found = issues_found
        self.auto_fixes = auto_fixes or []

    @property
    def has_errors(self) -> bool:
        return self.issues_found > 0

    @property
    def has_warnings(self) -> bool:
        return any(c["severity"] == "warning" for c in self.critiques)

    def to_dict(self) -> Dict:
        return {
            "critiques": self.critiques,
            "issues_found": self.issues_found,
            "auto_fixes": self.auto_fixes,
            "has_errors": self.has_errors,
            "has_warnings": self.has_warnings,
        }

    def apply_auto_fixes(self, actions: List[Dict]) -> List[Dict]:
        """Apply auto-fixes and return corrected action list."""
        if not self.auto_fixes:
            return actions

        remove_indices = set()
        for fix in self.auto_fixes:
            if fix.get("fix") == "remove":
                remove_indices.add(fix["step"])

        if remove_indices:
            actions = [a for i, a in enumerate(actions) if i not in remove_indices]
            logger.info(f"Critique auto-fix: removed {len(remove_indices)} problematic actions")

        return actions


# ---------------------------------------------------------------------------
# Proactive Data Insights
# ---------------------------------------------------------------------------

def generate_proactive_insights(
    metadata: Dict,
    user_message: str,
    actions: List[Dict],
) -> Dict[str, Any]:
    """
    Generate proactive insights and smart suggestions.
    Called after the AI generates its response.

    Returns:
        {
            "insights": [...],      # Data observations
            "suggestions": [...],   # Follow-up action suggestions
            "data_warnings": [...], # Potential data quality issues
        }
    """
    agent = CritiqueAgent(metadata)

    insights = agent.generate_insights()
    suggestions = agent.suggest_followups(user_message, actions, "")

    # Data quality warnings
    data_warnings = []
    if metadata:
        for col in metadata.get("columns", []):
            null_pct = 0
            total = metadata.get("data_rows", 1)
            if total > 0:
                null_pct = (col.get("null_count", 0) / total) * 100

            if null_pct > 30:
                data_warnings.append({
                    "column": col.get("header", col.get("letter", "?")),
                    "issue": f"{null_pct:.0f}% empty values",
                    "impact": "Aggregation results may be incomplete",
                })

            if col.get("type") == "text" and col.get("unique_count", 0) == total:
                data_warnings.append({
                    "column": col.get("header", col.get("letter", "?")),
                    "issue": "All values are unique (likely an ID column)",
                    "impact": "Not useful for grouping or aggregation",
                })

    return {
        "insights": insights,
        "suggestions": suggestions,
        "data_warnings": data_warnings[:3],  # Limit warnings
    }


def critique_and_fix_actions(
    actions: List[Dict],
    metadata: Optional[Dict] = None,
) -> tuple:
    """
    Run critique on actions, auto-fix what we can, return fixed actions + report.

    Returns:
        (fixed_actions, critique_result)
    """
    agent = CritiqueAgent(metadata)
    result = agent.critique_actions(actions)

    if result.has_errors:
        logger.warning(
            f"Critique found {result.issues_found} error(s) in action plan — applying auto-fixes"
        )
        fixed_actions = result.apply_auto_fixes(actions)
        return fixed_actions, result

    return actions, result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _expand_range(range_str: str) -> set:
    """Expand a range like 'A1:C3' to a set of cell refs."""
    cells = set()
    match = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", range_str)
    if not match:
        return {range_str}

    start_col, start_row, end_col, end_row = match.groups()
    for col_ord in range(ord(start_col), ord(end_col) + 1):
        for row in range(int(start_row), int(end_row) + 1):
            cells.add(f"{chr(col_ord)}{row}")
    return cells
