"""
Critique Agent v2 — Reviews AI responses before they reach the user.

This agent acts as a quality gate that:
1. Validates formulas in the action plan
2. Detects missing considerations (edge cases, empty rows, data type mismatches)
3. Suggests better alternatives (faster formulas, simpler approaches)
4. Generates proactive insights about the data
5. Adds smart follow-up suggestions
6. [v2] Response quality checks (filler stripping, verbosity, terse responses)
7. [v2] Enhanced action validation (redundant actions, column refs, sheet refs)
8. [v2] Intent-match scoring
9. [v2] Self-critique via LLM (ReAct only, low scores)
"""

import hashlib
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
# Filler Phrases (compiled once)
# ---------------------------------------------------------------------------

_FILLER_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"^I'?d be happy to help[.!]?\s*",
        r"^Sure[!,]\s*",
        r"^Of course[!,]\s*",
        r"^Great question[!,]\s*",
        r"^Absolutely[!,]\s*",
        r"^Certainly[!,]\s*",
        r"^No problem[!,]\s*",
        r"^Let me help you with that[.!]?\s*",
        r"^I can help with that[.!]?\s*",
        r"^Here'?s what I (?:did|can do)[.!:]\s*",
    ]
]

_TRAILING_FILLER = re.compile(
    r"\s*(?:Is there anything else (?:you'?d like|I can help with|you need)\??|"
    r"Let me know if you (?:need|want) anything else[.!]?|"
    r"Feel free to ask if you have (?:any )?(?:more )?questions[.!]?|"
    r"Hope this helps[.!]?|"
    r"Happy to help further[.!]?)\s*$",
    re.IGNORECASE,
)


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

    def __init__(
        self,
        metadata: Optional[Dict] = None,
        existing_sheets: Optional[List[str]] = None,
    ):
        self.metadata = metadata or {}
        self.existing_sheets = existing_sheets or []
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

        # --- v2: Enhanced action validation ---
        self._check_redundant_actions(actions)
        self._check_column_references(actions)
        self._check_range_boundaries(actions)
        self._check_missing_sheet_references(actions)

        return CritiqueResult(
            critiques=self.critiques,
            issues_found=issues_found,
            auto_fixes=auto_fixes,
        )

    # --- v2: Enhanced action validation methods ---

    def _check_redundant_actions(self, actions: List[Dict]):
        """Detect redundant actions (same cell set then overwritten)."""
        cell_setters: Dict[str, int] = {}  # "sheet!cell" -> step index
        for i, action in enumerate(actions):
            act_type = action.get("action", "")
            if act_type in ("setFormula", "setValues"):
                sheet = action.get("sheet", "")
                cell = action.get("cell", "")
                if cell:
                    key = f"{sheet}!{cell}"
                    if key in cell_setters:
                        self.critiques.append({
                            "step": cell_setters[key] + 1,
                            "severity": "warning",
                            "issue": f"Cell {cell} is set in step {cell_setters[key]+1} but overwritten in step {i+1}",
                            "fix": "Remove the earlier action since it will be overwritten",
                            "action": act_type,
                        })
                    cell_setters[key] = i

    def _check_column_references(self, actions: List[Dict]):
        """Check if formula references columns beyond sheet boundaries."""
        if not self.metadata:
            return
        known_cols = {c.get("letter", "") for c in self.metadata.get("columns", [])}
        if not known_cols:
            return

        max_col = max(known_cols) if known_cols else "Z"

        for i, action in enumerate(actions):
            if action.get("action") != "setFormula":
                continue
            formula = action.get("formula", "")
            # Find column references like A2, Z100, etc. in the formula
            col_refs = re.findall(r"(?<![A-Z])([A-Z])(?=\d)", formula)
            for col in col_refs:
                if col > max_col:
                    self.critiques.append({
                        "step": i + 1,
                        "severity": "error",
                        "issue": f"Formula references column {col} but sheet only has columns up to {max_col}",
                        "fix": f"Check column reference — sheet columns are A-{max_col}",
                        "action": "setFormula",
                    })

    def _check_range_boundaries(self, actions: List[Dict]):
        """Warn if formula ranges extend far beyond actual data."""
        if not self.metadata:
            return
        last_row = self.metadata.get("last_row", 0)
        if last_row <= 0:
            return

        for i, action in enumerate(actions):
            if action.get("action") != "setFormula":
                continue
            formula = action.get("formula", "")
            # Find range endpoints like A1000, B5000
            range_ends = re.findall(r"[A-Z]+(\d+)\)", formula)
            for end_str in range_ends:
                end_row = int(end_str)
                if end_row > last_row * 10 and end_row > last_row + 100:
                    self.critiques.append({
                        "step": i + 1,
                        "severity": "warning",
                        "issue": f"Range extends to row {end_row} but data ends at row {last_row}",
                        "fix": f"Use row {last_row} as the range end for efficiency",
                        "action": "setFormula",
                    })

    def _check_missing_sheet_references(self, actions: List[Dict]):
        """Check if actions target sheets that don't exist and aren't created."""
        # Collect sheets created by actions
        created_sheets = set()
        for action in actions:
            if action.get("action") == "createSheet":
                created_sheets.add(action.get("name", ""))

        # Check if any action targets a non-existent sheet
        for i, action in enumerate(actions):
            target_sheet = action.get("sheet", "")
            if not target_sheet:
                continue
            # Skip if it's the current sheet (from metadata)
            current_sheet = self.metadata.get("sheet_name", "")
            if target_sheet == current_sheet:
                continue
            # Skip if sheet exists or is being created
            if target_sheet in created_sheets:
                continue
            if target_sheet in self.existing_sheets:
                continue
            self.critiques.append({
                "step": i + 1,
                "severity": "error",
                "issue": f"Action targets sheet '{target_sheet}' which doesn't exist and isn't created",
                "fix": f"Add a createSheet action for '{target_sheet}' or verify the sheet name",
                "action": action.get("action", ""),
            })

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

    def critique_response_text(
        self,
        ai_response: str,
        actions: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        Review the AI's text response for quality issues.

        Args:
            ai_response: The AI-generated text response.
            actions: The list of sheet actions (fixes bug where empty [] was used).
        """
        if actions is None:
            actions = []
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
            a.get("action") == "setFormula" for a in actions
        ):
            text_issues.append({
                "severity": "suggestion",
                "issue": "Response contains formula(s) as text — consider executing them as actions",
                "context": formula_in_text[0][:80],
            })

        return text_issues

    # --- v2: Response quality checker ---

    def critique_response_quality(
        self,
        ai_response: str,
        actions: List[Dict],
    ) -> str:
        """
        Rule-based response quality check and cleanup (0 LLM calls).

        - Strips filler phrases
        - Trims verbose action responses (only if content is repetitive)
        - Expands terse responses when actions exist
        - Detects formulas in text without corresponding actions

        Returns the cleaned response text.
        """
        text = ai_response

        # 1. Strip leading filler phrases
        for pat in _FILLER_PATTERNS:
            text = pat.sub("", text, count=1)

        # 2. Strip trailing filler
        text = _TRAILING_FILLER.sub("", text)

        text = text.strip()

        # 3. Terse check: if actions exist but response is too short, auto-generate
        if actions and len(text) < 15:
            summary = _build_action_text_summary(actions)
            if summary:
                text = summary

        # 4. Verbosity check: only truncate if response restates what actions convey
        #    AND exceeds 600 chars. Never truncate warnings/caveats.
        if actions and len(text) > 600:
            text = _smart_truncate(text, actions)

        return text

    # --- v2: Intent-match scoring ---

    def score_response(
        self,
        user_message: str,
        ai_response: str,
        actions: List[Dict],
        request_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Score response quality 0-10 based on intent matching (not keyword overlap).

        Scoring:
        - Relevance (3x): Does the response type match what was asked?
        - Completeness (3x): Are expected actions present?
        - Conciseness (2x): Shorter is better for sidebar
        - Actionability (2x): More actions relative to text = higher score

        Returns dict with score, breakdown, and flags.
        """
        scores = {}
        msg_lower = user_message.lower()

        # --- Relevance (0-10, weight 3x) ---
        relevance = 5  # baseline
        if actions:
            action_types = {a.get("action") for a in actions}
            # Check if action types match intent
            if any(w in msg_lower for w in ("sum", "total", "count", "average", "avg")):
                if "setFormula" in action_types:
                    relevance = 9
            if any(w in msg_lower for w in ("chart", "graph", "plot", "visuali")):
                if "createChart" in action_types:
                    relevance = 9
            if any(w in msg_lower for w in ("duplicate", "duplicates")):
                if "formatRange" in action_types or "createSheet" in action_types:
                    relevance = 9
            if any(w in msg_lower for w in ("highlight", "color", "format")):
                if "conditionalFormat" in action_types or "formatRange" in action_types:
                    relevance = 9
            if any(w in msg_lower for w in ("summary", "group", "by")):
                if "createSheet" in action_types:
                    relevance = 9
        elif not actions:
            # No actions — check if this was a question (expected no actions)
            if "?" in user_message or any(w in msg_lower for w in ("what", "how", "why", "explain", "tell me")):
                relevance = 7  # Q&A with no actions is fine
            elif any(w in msg_lower for w in ("create", "make", "add", "sum", "count")):
                relevance = 2  # User wanted actions but got none
        scores["relevance"] = relevance

        # --- Completeness (0-10, weight 3x) ---
        completeness = 5
        if actions:
            has_chart = any(a.get("action") == "createChart" for a in actions)
            has_formula = any(a.get("action") == "setFormula" for a in actions)
            has_create_sheet = any(a.get("action") == "createSheet" for a in actions)

            if any(w in msg_lower for w in ("chart", "graph", "plot")):
                completeness = 9 if has_chart else 3
            elif any(w in msg_lower for w in ("summary", "group")):
                completeness = 9 if (has_create_sheet and has_formula) else 5
            else:
                completeness = 7  # has actions, seems reasonable
        elif "?" in user_message:
            # Q&A — completeness depends on response length
            completeness = 7 if len(ai_response) > 30 else 4
        scores["completeness"] = completeness

        # --- Conciseness (0-10, weight 2x) ---
        resp_len = len(ai_response)
        if resp_len < 100:
            conciseness = 9
        elif resp_len < 300:
            conciseness = 8
        elif resp_len < 500:
            conciseness = 6
        elif resp_len < 800:
            conciseness = 4
        else:
            conciseness = 2
        scores["conciseness"] = conciseness

        # --- Actionability (0-10, weight 2x) ---
        if actions:
            ratio = len(actions) / max(resp_len / 100, 1)
            actionability = min(10, int(ratio * 3) + 4)
        else:
            actionability = 3 if "?" in user_message else 1
        scores["actionability"] = actionability

        # Weighted total (out of 10)
        total = (
            scores["relevance"] * 3 +
            scores["completeness"] * 3 +
            scores["conciseness"] * 2 +
            scores["actionability"] * 2
        ) / 10

        return {
            "score": round(total, 1),
            "breakdown": scores,
            "needs_critique": total < 7,
        }

    # --- v2: Self-critique via LLM ---

    def self_critique(
        self,
        user_message: str,
        ai_response: str,
        actions: List[Dict],
        score_result: Dict,
    ) -> Dict[str, Any]:
        """
        Single LLM call to critique the response (ReAct only, score < 7).

        Returns dict with:
        - critique_text: What's wrong (or "LGTM")
        - action: "suppress_actions" | "remove_action" | "add_note" | "lgtm"
        - removed_indices: List of action indices to remove (if action == "remove_action")
        - note: Text to append (if action == "add_note")
        """
        try:
            from app.core.config import settings
            if not settings.OPENROUTER_API_KEY:
                return {"critique_text": "LGTM", "action": "lgtm"}

            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model="google/gemini-2.0-flash-001",
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.0,
                max_tokens=512,
            )

            actions_summary = json.dumps(
                [{"action": a.get("action"), "cell": a.get("cell", ""), "formula": a.get("formula", "")[:80]}
                 for a in actions[:10]],
                indent=None,
            )

            prompt = f"""You are a quality reviewer for a Google Sheets AI assistant. Review this response.

USER REQUEST: "{user_message}"

AI RESPONSE: "{ai_response[:500]}"

ACTIONS: {actions_summary}

QUALITY SCORE: {score_result.get('score', 0)}/10

Issues to check:
1. Do the actions match what the user asked for?
2. Are there formula errors (wrong column, wrong function)?
3. Is the response misleading or incorrect?

Reply with EXACTLY one of:
- "LGTM" if the response is acceptable
- "NOTE: <tip>" if the response is okay but could use a helpful tip
- "SUPPRESS: <reason>" if the actions are wrong and should NOT be executed
- "REMOVE <step_numbers>: <reason>" if specific action steps should be removed

Reply:"""

            result = llm.invoke(prompt)
            critique_text = result.content.strip() if hasattr(result, "content") else str(result).strip()

            if critique_text.startswith("LGTM"):
                return {"critique_text": "LGTM", "action": "lgtm"}
            elif critique_text.startswith("SUPPRESS"):
                reason = critique_text.split(":", 1)[1].strip() if ":" in critique_text else "Quality check failed"
                return {
                    "critique_text": critique_text,
                    "action": "suppress_actions",
                    "note": f"Note: {reason}",
                }
            elif critique_text.startswith("REMOVE"):
                # Parse "REMOVE 3,5: reason"
                match = re.match(r"REMOVE\s+([\d,\s]+):\s*(.+)", critique_text)
                if match:
                    indices = [int(x.strip()) - 1 for x in match.group(1).split(",") if x.strip().isdigit()]
                    reason = match.group(2).strip()
                    return {
                        "critique_text": critique_text,
                        "action": "remove_action",
                        "removed_indices": indices,
                        "note": f"Removed step(s) {match.group(1).strip()}: {reason}",
                    }
                return {"critique_text": critique_text, "action": "lgtm"}
            elif critique_text.startswith("NOTE"):
                note = critique_text.split(":", 1)[1].strip() if ":" in critique_text else critique_text
                return {
                    "critique_text": critique_text,
                    "action": "add_note",
                    "note": note,
                }
            else:
                return {"critique_text": critique_text, "action": "lgtm"}

        except Exception as e:
            logger.warning(f"Self-critique failed: {e}")
            return {"critique_text": "LGTM", "action": "lgtm"}


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
    existing_sheets: Optional[List[str]] = None,
) -> tuple:
    """
    Run critique on actions, auto-fix what we can, return fixed actions + report.

    Returns:
        (fixed_actions, critique_result)
    """
    agent = CritiqueAgent(metadata, existing_sheets=existing_sheets)
    result = agent.critique_actions(actions)

    if result.has_errors:
        logger.warning(
            f"Critique found {result.issues_found} error(s) in action plan — applying auto-fixes"
        )
        fixed_actions = result.apply_auto_fixes(actions)
        return fixed_actions, result

    return actions, result


def critique_and_clean_response(
    ai_response: str,
    actions: List[Dict],
    user_message: str,
    metadata: Optional[Dict] = None,
    existing_sheets: Optional[List[str]] = None,
    is_react: bool = False,
) -> Dict[str, Any]:
    """
    Full critique v2 pipeline: quality check + scoring + optional self-critique.

    Returns:
        {
            "response": cleaned response text,
            "actions": potentially modified actions list,
            "critique_result": CritiqueResult from action validation,
            "score": quality score dict,
            "self_critique": self-critique result (if triggered),
        }
    """
    agent = CritiqueAgent(metadata, existing_sheets=existing_sheets)

    # 1. Critique actions (existing + new validations)
    critique_result = agent.critique_actions(actions)
    fixed_actions = actions
    if critique_result.has_errors:
        fixed_actions = critique_result.apply_auto_fixes(actions)

    # 2. Critique response quality (rule-based, 0 LLM calls)
    cleaned_response = agent.critique_response_quality(ai_response, fixed_actions)

    # 3. Critique response text for issues
    agent.critique_response_text(cleaned_response, fixed_actions)

    # 4. Score response
    score_result = agent.score_response(
        user_message, cleaned_response, fixed_actions,
    )

    # 5. Self-critique via LLM (ReAct only, score < 7)
    self_critique_result = None
    if is_react and score_result.get("needs_critique") and fixed_actions:
        self_critique_result = agent.self_critique(
            user_message, cleaned_response, fixed_actions, score_result,
        )

        # Apply self-critique actions
        if self_critique_result:
            sc_action = self_critique_result.get("action", "lgtm")
            if sc_action == "suppress_actions":
                # Remove all actions, keep only text + note
                fixed_actions = []
                note = self_critique_result.get("note", "")
                if note:
                    cleaned_response = cleaned_response + "\n\n" + note
            elif sc_action == "remove_action":
                indices = set(self_critique_result.get("removed_indices", []))
                if indices:
                    fixed_actions = [a for i, a in enumerate(fixed_actions) if i not in indices]
                note = self_critique_result.get("note", "")
                if note:
                    cleaned_response = cleaned_response + "\n\n" + note
            elif sc_action == "add_note":
                note = self_critique_result.get("note", "")
                if note:
                    cleaned_response = cleaned_response + "\n\n" + note

    return {
        "response": cleaned_response,
        "actions": fixed_actions,
        "critique_result": critique_result,
        "score": score_result,
        "self_critique": self_critique_result,
    }


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


def _build_action_text_summary(actions: List[Dict]) -> str:
    """Build a human-readable summary from actions for terse responses."""
    parts = []
    sheets = set()
    formulas = 0
    charts = 0

    for a in actions:
        act = a.get("action", "")
        if act == "createSheet":
            sheets.add(a.get("name", "new sheet"))
        elif act in ("setFormula", "autoFillDown"):
            formulas += 1
        elif act == "createChart":
            charts += 1
            parts.append(f"Created a {a.get('chartType', 'chart')} chart")
        elif act == "conditionalFormat":
            parts.append("Applied conditional formatting")

    if sheets:
        parts.insert(0, f"Created **{', '.join(sheets)}** sheet{'s' if len(sheets) > 1 else ''}")
    if formulas:
        parts.append(f"with {formulas} formula{'s' if formulas > 1 else ''}")

    return " ".join(parts) + "." if parts else ""


def _smart_truncate(text: str, actions: List[Dict]) -> str:
    """Truncate response text only if it contains repetitive content.

    Never truncate sentences containing warnings, caveats, or data quality notes.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) <= 3:
        return text

    # Build a set of action-related keywords to detect repetition
    action_keywords = set()
    for a in actions:
        if a.get("action") == "createSheet":
            action_keywords.add(a.get("name", "").lower())
        if a.get("formula"):
            # Extract function names
            funcs = re.findall(r"=(\w+)\(", a["formula"])
            action_keywords.update(f.lower() for f in funcs)

    # Classify sentences
    keep = []
    important_words = {"note", "warning", "caution", "empty", "null", "blank",
                       "missing", "error", "careful", "however", "but", "although",
                       "caveat", "important", "%"}

    for sent in sentences:
        sent_lower = sent.lower()
        # Always keep sentences with warnings/caveats
        if any(w in sent_lower for w in important_words):
            keep.append(sent)
            continue
        # Keep first 3 non-repetitive sentences
        if len(keep) < 3:
            keep.append(sent)

    return " ".join(keep)
