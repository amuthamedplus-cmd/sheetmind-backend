"""
Formula Knowledge Base for SheetMind.

Contains patterns for Google Sheets formulas with:
- Intent descriptions (what the user wants to do)
- Correct formula templates
- Examples with real syntax
- Common mistakes and warnings
- When to use vs when NOT to use each formula
"""

from typing import List, Dict, Optional
import re

# ---------------------------------------------------------------------------
# Formula Pattern Database
# ---------------------------------------------------------------------------

FORMULA_PATTERNS: List[Dict] = [
    # ==========================================================================
    # SUMIF - Simple conditional sum
    # ==========================================================================
    {
        "id": "sumif_basic",
        "name": "SUMIF",
        "intent": ["sum by category", "sum where", "total by group", "sum if matches", "sum values for each"],
        "description": "Sum values in one column where another column matches a criteria",
        "template": "=SUMIF(criteria_range, criteria, sum_range)",
        "example": "=SUMIF('{sheet}'!E2:E{lastRow}, A2, '{sheet}'!G2:G{lastRow})",
        "explanation": "Sums column G where column E matches the value in A2",
        "use_when": [
            "Summing a single column based on a condition",
            "Creating grouped totals (sum by category, region, etc.)",
            "The sum_range is a simple column reference"
        ],
        "do_not_use_when": [
            "You need to multiply columns before summing - use SUMPRODUCT instead",
            "You have multiple conditions - use SUMIFS instead",
            "The sum_range contains any arithmetic like A:A*B:B"
        ],
        "warning": "SUMIF sum_range must be a simple range. It CANNOT contain arithmetic operations like A2:A*B2:B",
        "common_mistakes": [
            {
                "wrong": "=SUMIF(E2:E, A2, C2:C*G2:G)",
                "why_wrong": "sum_range cannot contain multiplication",
                "correct": "Use SUMPRODUCT instead: =SUMPRODUCT((E2:E31=A2)*(C2:C31*G2:G31))"
            }
        ]
    },

    # ==========================================================================
    # SUMPRODUCT - Multiply and sum with conditions
    # ==========================================================================
    {
        "id": "sumproduct_multiply_sum",
        "name": "SUMPRODUCT",
        "intent": ["sum of multiplication", "sum product by category", "multiply columns and sum",
                   "sum of A times B", "total of price times quantity", "sum where with calculation",
                   "weighted sum", "sum of calculated values by group"],
        "description": "Multiply columns together and sum the results, optionally with conditions",
        "template": "=SUMPRODUCT((condition_range=criteria)*(value1_range*value2_range))",
        "example": "=SUMPRODUCT(('{sheet}'!E2:E{lastRow}=A2)*('{sheet}'!C2:C{lastRow}*'{sheet}'!G2:G{lastRow}))",
        "explanation": "Multiplies column C by column G, then sums only where column E matches A2",
        "use_when": [
            "Need to multiply two columns before summing (e.g., price * quantity)",
            "Need sum with arithmetic operations on columns",
            "SUMIF would require multiplication in sum_range (which is invalid)",
            "Multiple conditions with calculations"
        ],
        "do_not_use_when": [
            "Simple sum of one column with one condition - use SUMIF (simpler)",
        ],
        "patterns": [
            {
                "case": "Sum of A*B where C equals criteria",
                "formula": "=SUMPRODUCT((C2:C{lastRow}=criteria)*(A2:A{lastRow}*B2:B{lastRow}))"
            },
            {
                "case": "Sum of A*B where C equals X AND D equals Y",
                "formula": "=SUMPRODUCT((C2:C{lastRow}=\"X\")*(D2:D{lastRow}=\"Y\")*(A2:A{lastRow}*B2:B{lastRow}))"
            },
            {
                "case": "Sum of A*B (no condition)",
                "formula": "=SUMPRODUCT(A2:A{lastRow}*B2:B{lastRow})"
            }
        ],
        "warning": None,
        "common_mistakes": []
    },

    # ==========================================================================
    # SUMIFS - Multiple conditions
    # ==========================================================================
    {
        "id": "sumifs_multi",
        "name": "SUMIFS",
        "intent": ["sum with multiple conditions", "sum where A and B", "sum if both match",
                   "sum with two criteria", "sum where and where"],
        "description": "Sum values with multiple conditions (AND logic)",
        "template": "=SUMIFS(sum_range, criteria_range1, criteria1, criteria_range2, criteria2)",
        "example": "=SUMIFS('{sheet}'!G2:G{lastRow}, '{sheet}'!E2:E{lastRow}, A2, '{sheet}'!F2:F{lastRow}, B2)",
        "explanation": "Sums column G where column E matches A2 AND column F matches B2",
        "use_when": [
            "Multiple conditions that must ALL be true",
            "Filtering on two or more columns before summing"
        ],
        "do_not_use_when": [
            "Only one condition - use SUMIF instead",
            "Need to multiply columns - use SUMPRODUCT"
        ],
        "warning": "Like SUMIF, sum_range cannot contain arithmetic",
        "common_mistakes": []
    },

    # ==========================================================================
    # COUNTIF - Count matches
    # ==========================================================================
    {
        "id": "countif_basic",
        "name": "COUNTIF",
        "intent": ["count by category", "count where", "how many", "count if matches",
                   "number of items per group", "count occurrences"],
        "description": "Count cells that match a criteria",
        "template": "=COUNTIF(range, criteria)",
        "example": "=COUNTIF('{sheet}'!E2:E{lastRow}, A2)",
        "explanation": "Counts how many times the value in A2 appears in column E",
        "use_when": [
            "Counting occurrences of a value",
            "Getting count per category"
        ],
        "do_not_use_when": [
            "Multiple conditions - use COUNTIFS"
        ],
        "warning": None,
        "common_mistakes": []
    },

    # ==========================================================================
    # COUNTIFS - Count with multiple conditions
    # ==========================================================================
    {
        "id": "countifs_multi",
        "name": "COUNTIFS",
        "intent": ["count with multiple conditions", "count where A and B", "count if both"],
        "description": "Count cells that match multiple conditions",
        "template": "=COUNTIFS(range1, criteria1, range2, criteria2)",
        "example": "=COUNTIFS('{sheet}'!E2:E{lastRow}, A2, '{sheet}'!F2:F{lastRow}, \">10\")",
        "explanation": "Counts rows where column E matches A2 AND column F is greater than 10",
        "use_when": [
            "Counting with multiple conditions"
        ],
        "do_not_use_when": [
            "Single condition - use COUNTIF"
        ],
        "warning": None,
        "common_mistakes": []
    },

    # ==========================================================================
    # AVERAGEIF - Average with condition
    # ==========================================================================
    {
        "id": "averageif_basic",
        "name": "AVERAGEIF",
        "intent": ["average by category", "average where", "mean by group", "avg if matches"],
        "description": "Calculate average of values where condition matches",
        "template": "=AVERAGEIF(criteria_range, criteria, average_range)",
        "example": "=AVERAGEIF('{sheet}'!E2:E{lastRow}, A2, '{sheet}'!G2:G{lastRow})",
        "explanation": "Averages column G where column E matches A2",
        "use_when": [
            "Average of one column based on a condition",
            "Mean by category"
        ],
        "do_not_use_when": [
            "Need weighted average - use SUMPRODUCT divided by SUMPRODUCT"
        ],
        "warning": "Like SUMIF, average_range cannot contain arithmetic",
        "common_mistakes": []
    },

    # ==========================================================================
    # UNIQUE - Get unique values
    # ==========================================================================
    {
        "id": "unique_basic",
        "name": "UNIQUE",
        "intent": ["get unique values", "distinct values", "list of categories", "unique list",
                   "deduplicate", "remove duplicates from column"],
        "description": "Returns unique values from a range (auto-spills to multiple cells)",
        "template": "=UNIQUE(range)",
        "example": "=UNIQUE('{sheet}'!E2:E{lastRow})",
        "explanation": "Returns all unique values from column E, automatically filling down",
        "use_when": [
            "Getting list of unique categories for grouping",
            "Creating a distinct list from a column"
        ],
        "do_not_use_when": [],
        "warning": "UNIQUE auto-spills! Never use fillDown=true with UNIQUE formulas",
        "common_mistakes": [
            {
                "wrong": "Using fillDown=true with UNIQUE",
                "why_wrong": "UNIQUE automatically fills multiple cells (spill). fillDown overwrites the spilled values causing #REF! error",
                "correct": "Set UNIQUE formula once, it will auto-expand"
            }
        ]
    },

    # ==========================================================================
    # FILTER - Filter rows
    # ==========================================================================
    {
        "id": "filter_basic",
        "name": "FILTER",
        "intent": ["filter rows", "get rows where", "filter data", "extract matching rows"],
        "description": "Returns rows that match a condition (auto-spills)",
        "template": "=FILTER(range, condition)",
        "example": "=FILTER('{sheet}'!A2:G{lastRow}, '{sheet}'!E2:E{lastRow}=\"North\")",
        "explanation": "Returns all rows where column E equals 'North'",
        "use_when": [
            "Extracting subset of data",
            "Getting all rows matching a criteria"
        ],
        "do_not_use_when": [],
        "warning": "FILTER auto-spills! Never use fillDown with FILTER",
        "common_mistakes": []
    },

    # ==========================================================================
    # VLOOKUP - Lookup value
    # ==========================================================================
    {
        "id": "vlookup_basic",
        "name": "VLOOKUP",
        "intent": ["lookup value", "find value", "get value from another table", "vlookup",
                   "match and return"],
        "description": "Look up a value in the first column and return value from another column",
        "template": "=VLOOKUP(search_key, range, index, [is_sorted])",
        "example": "=VLOOKUP(A2, '{sheet}'!A2:G{lastRow}, 3, FALSE)",
        "explanation": "Finds A2 in column A and returns the value from column 3 (C)",
        "use_when": [
            "Looking up a value from a reference table",
            "Getting related data based on a key"
        ],
        "do_not_use_when": [
            "Need to look up based on multiple columns - use INDEX/MATCH or XLOOKUP"
        ],
        "warning": "Always use FALSE for exact match unless data is sorted",
        "common_mistakes": []
    },

    # ==========================================================================
    # MAX/MIN with IF
    # ==========================================================================
    {
        "id": "maxifs_basic",
        "name": "MAXIFS",
        "intent": ["max by category", "maximum where", "highest value per group"],
        "description": "Returns maximum value with conditions",
        "template": "=MAXIFS(max_range, criteria_range, criteria)",
        "example": "=MAXIFS('{sheet}'!G2:G{lastRow}, '{sheet}'!E2:E{lastRow}, A2)",
        "explanation": "Returns maximum of column G where column E matches A2",
        "use_when": ["Finding maximum value within a category"],
        "do_not_use_when": [],
        "warning": None,
        "common_mistakes": []
    },
    {
        "id": "minifs_basic",
        "name": "MINIFS",
        "intent": ["min by category", "minimum where", "lowest value per group"],
        "description": "Returns minimum value with conditions",
        "template": "=MINIFS(min_range, criteria_range, criteria)",
        "example": "=MINIFS('{sheet}'!G2:G{lastRow}, '{sheet}'!E2:E{lastRow}, A2)",
        "explanation": "Returns minimum of column G where column E matches A2",
        "use_when": ["Finding minimum value within a category"],
        "do_not_use_when": [],
        "warning": None,
        "common_mistakes": []
    },
]


# ---------------------------------------------------------------------------
# Lookup Functions
# ---------------------------------------------------------------------------

def find_formula_pattern(query: str) -> List[Dict]:
    """
    Find formula patterns that match the user's intent.

    Args:
        query: User's description of what they want to do

    Returns:
        List of matching formula patterns, ranked by relevance
    """
    query_lower = query.lower()
    results = []

    for pattern in FORMULA_PATTERNS:
        score = 0

        # Check intent keywords
        for intent in pattern.get("intent", []):
            if intent.lower() in query_lower:
                score += 10
            # Partial match
            intent_words = intent.lower().split()
            matching_words = sum(1 for w in intent_words if w in query_lower)
            score += matching_words * 2

        # Check formula name
        if pattern["name"].lower() in query_lower:
            score += 5

        # Check description
        desc_words = pattern.get("description", "").lower().split()
        matching_desc = sum(1 for w in desc_words if w in query_lower)
        score += matching_desc

        # Special boost for SUMPRODUCT when multiplication is mentioned
        if "multiply" in query_lower or "product" in query_lower or "*" in query_lower:
            if pattern["name"] == "SUMPRODUCT":
                score += 15

        # Special boost for grouped operations
        if ("by" in query_lower or "group" in query_lower or "category" in query_lower):
            if pattern["name"] in ["SUMIF", "COUNTIF", "AVERAGEIF", "SUMPRODUCT"]:
                score += 5

        if score > 0:
            results.append({
                "pattern": pattern,
                "score": score
            })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    return [r["pattern"] for r in results[:3]]  # Return top 3 matches


def get_formula_for_intent(intent: str, sheet_name: str, last_row: int) -> Dict:
    """
    Get the best formula pattern for a given intent with filled-in values.

    Args:
        intent: What the user wants to do
        sheet_name: Name of the source sheet
        last_row: Last row with data

    Returns:
        Dict with formula recommendation
    """
    patterns = find_formula_pattern(intent)

    if not patterns:
        return {
            "found": False,
            "message": "No matching formula pattern found. Please describe what you want to calculate."
        }

    best = patterns[0]

    # Fill in template values
    example = best.get("example", best.get("template", ""))
    example = example.replace("{sheet}", sheet_name)
    example = example.replace("{lastRow}", str(last_row))

    result = {
        "found": True,
        "formula_name": best["name"],
        "description": best["description"],
        "template": best["template"],
        "example": example,
        "use_when": best.get("use_when", []),
        "do_not_use_when": best.get("do_not_use_when", []),
    }

    if best.get("warning"):
        result["warning"] = best["warning"]

    if best.get("common_mistakes"):
        result["common_mistakes"] = best["common_mistakes"]

    if best.get("patterns"):
        result["additional_patterns"] = best["patterns"]

    # If there are alternatives, mention them
    if len(patterns) > 1:
        result["alternatives"] = [p["name"] for p in patterns[1:]]

    return result


def format_pattern_for_prompt(pattern: Dict) -> str:
    """Format a formula pattern for inclusion in the agent prompt."""
    lines = [
        f"**{pattern['name']}**",
        f"Description: {pattern['description']}",
        f"Template: {pattern['template']}",
        f"Example: {pattern.get('example', 'N/A')}",
    ]

    if pattern.get("use_when"):
        lines.append("Use when: " + "; ".join(pattern["use_when"][:2]))

    if pattern.get("do_not_use_when"):
        lines.append("Do NOT use when: " + "; ".join(pattern["do_not_use_when"][:2]))

    if pattern.get("warning"):
        lines.append(f"WARNING: {pattern['warning']}")

    return "\n".join(lines)


def get_all_patterns_summary() -> str:
    """Get a summary of all formula patterns for the prompt."""
    summaries = []
    for p in FORMULA_PATTERNS:
        intent_str = ", ".join(p.get("intent", [])[:3])
        summaries.append(f"- {p['name']}: {intent_str}")
    return "\n".join(summaries)
