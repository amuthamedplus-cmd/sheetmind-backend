"""
Google Sheets formula syntax validator.

Catches structural errors before formulas reach the spreadsheet:
- Unmatched parentheses / quotes
- Unknown function names
- Wrong argument counts for common functions
- Malformed cell/range references
"""

import re
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Known Google Sheets functions with (min_args, max_args)
#   None for max = unlimited
# ---------------------------------------------------------------------------

KNOWN_FUNCTIONS = {
    # Math
    "SUM": (1, None), "SUMIF": (2, 3), "SUMIFS": (3, None),
    "SUMPRODUCT": (1, None), "AVERAGE": (1, None), "AVERAGEIF": (2, 3),
    "AVERAGEIFS": (3, None), "COUNT": (1, None), "COUNTA": (1, None),
    "COUNTBLANK": (1, 1), "COUNTIF": (2, 2), "COUNTIFS": (2, None),
    "MAX": (1, None), "MAXIFS": (3, None), "MIN": (1, None),
    "MINIFS": (3, None), "ABS": (1, 1), "ROUND": (1, 2),
    "ROUNDUP": (2, 2), "ROUNDDOWN": (2, 2), "INT": (1, 1),
    "MOD": (2, 2), "POWER": (2, 2), "SQRT": (1, 1),
    "PRODUCT": (1, None), "MEDIAN": (1, None), "LARGE": (2, 2),
    "SMALL": (2, 2), "RANK": (2, 3), "PERCENTILE": (2, 2),
    "RAND": (0, 0), "RANDBETWEEN": (2, 2),

    # Lookup
    "VLOOKUP": (3, 4), "HLOOKUP": (3, 4), "INDEX": (2, 3),
    "MATCH": (2, 3), "XLOOKUP": (3, 6), "OFFSET": (3, 5),
    "INDIRECT": (1, 2), "ROW": (0, 1), "COLUMN": (0, 1),
    "ROWS": (1, 1), "COLUMNS": (1, 1), "CHOOSE": (2, None),
    "ADDRESS": (2, 5),

    # Text
    "LEFT": (1, 2), "RIGHT": (1, 2), "MID": (3, 3),
    "LEN": (1, 1), "TRIM": (1, 1), "CLEAN": (1, 1),
    "UPPER": (1, 1), "LOWER": (1, 1), "PROPER": (1, 1),
    "SUBSTITUTE": (3, 4), "REPLACE": (4, 4), "FIND": (2, 3),
    "SEARCH": (2, 3), "CONCATENATE": (1, None), "CONCAT": (1, None),
    "TEXTJOIN": (3, None), "TEXT": (2, 2), "VALUE": (1, 1),
    "REPT": (2, 2), "EXACT": (2, 2), "T": (1, 1),

    # Date
    "TODAY": (0, 0), "NOW": (0, 0), "DATE": (3, 3),
    "YEAR": (1, 1), "MONTH": (1, 1), "DAY": (1, 1),
    "HOUR": (1, 1), "MINUTE": (1, 1), "SECOND": (1, 1),
    "DATEVALUE": (1, 1), "DATEDIF": (3, 3), "EDATE": (2, 2),
    "EOMONTH": (2, 2), "WEEKDAY": (1, 2), "WEEKNUM": (1, 2),
    "NETWORKDAYS": (2, 3), "WORKDAY": (2, 3),

    # Logical
    "IF": (2, 3), "IFS": (2, None), "AND": (1, None),
    "OR": (1, None), "NOT": (1, 1), "IFERROR": (2, 2),
    "IFNA": (2, 2), "SWITCH": (3, None), "TRUE": (0, 0),
    "FALSE": (0, 0),

    # Array / Dynamic
    "UNIQUE": (1, 3), "FILTER": (2, 3), "SORT": (1, 4),
    "SORTN": (1, None), "SEQUENCE": (1, 4), "ARRAYFORMULA": (1, 1),
    "FLATTEN": (1, None), "TRANSPOSE": (1, 1),
    "IMPORTRANGE": (2, 2),

    # Statistical
    "STDEV": (1, None), "VAR": (1, None), "CORREL": (2, 2),
    "FORECAST": (3, 3), "TREND": (1, 4), "GROWTH": (1, 4),
    "PERCENTRANK": (2, 3),

    # Info
    "ISBLANK": (1, 1), "ISERROR": (1, 1), "ISNA": (1, 1),
    "ISNUMBER": (1, 1), "ISTEXT": (1, 1), "TYPE": (1, 1),
    "CELL": (1, 2), "N": (1, 1),

    # Misc
    "HYPERLINK": (1, 2), "IMAGE": (1, 4), "SPARKLINE": (1, 2),
    "QUERY": (2, 3), "REGEXMATCH": (2, 2), "REGEXEXTRACT": (2, 2),
    "REGEXREPLACE": (3, 3), "SPLIT": (2, 4), "JOIN": (2, None),
}

# Cell reference pattern: A1, $A$1, A$1, $A1, Sheet1!A1, 'Sheet Name'!A1
_CELL_REF = re.compile(
    r"(?:'[^']*'!)?\$?[A-Z]{1,3}\$?\d+"
)

# Range pattern: A1:B10, $A$1:$B$10, Sheet1!A1:B10
_RANGE_REF = re.compile(
    r"(?:'[^']*'!)?\$?[A-Z]{1,3}\$?\d+:\$?[A-Z]{1,3}\$?\d+"
)


def validate_formula(formula: str) -> Tuple[bool, List[str]]:
    """
    Validate a Google Sheets formula for syntax correctness.

    Returns:
        (is_valid, list_of_errors)
        is_valid is True when there are no errors (warnings may still exist).
    """
    errors: List[str] = []

    if not formula:
        return False, ["Empty formula"]

    # 1. Must start with =
    if not formula.startswith("="):
        errors.append("Formula must start with '='")
        return False, errors

    body = formula[1:]  # Strip leading =
    if not body.strip():
        errors.append("Formula is empty after '='")
        return False, errors

    # 2. Balanced parentheses
    depth = 0
    in_string = False
    string_char = None
    for i, ch in enumerate(body):
        if in_string:
            if ch == string_char:
                in_string = False
            continue
        if ch in ('"', "'"):
            # Check if this is a sheet name quote like 'Sheet Name'!
            # Don't count single quotes that are part of sheet references
            if ch == "'" and i + 1 < len(body):
                # Look ahead to see if this ends with '!
                closing = body.find("'", i + 1)
                if closing != -1 and closing + 1 < len(body) and body[closing + 1] == "!":
                    # Skip this sheet reference entirely
                    continue
            if ch == '"':
                in_string = True
                string_char = ch
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                errors.append(f"Unexpected closing parenthesis at position {i + 2}")

    if depth > 0:
        errors.append(f"Missing {depth} closing parenthesis(es)")
    elif depth < 0:
        errors.append(f"{abs(depth)} extra closing parenthesis(es)")

    # 3. Balanced double quotes
    quote_count = 0
    for i, ch in enumerate(body):
        if ch == '"':
            quote_count += 1
    if quote_count % 2 != 0:
        errors.append("Unmatched double quote")

    # 4. Check function names
    func_pattern = re.compile(r"([A-Z_][A-Z_0-9]*)\s*\(", re.IGNORECASE)
    for m in func_pattern.finditer(body):
        func_name = m.group(1).upper()
        if func_name not in KNOWN_FUNCTIONS:
            errors.append(f"Unknown function: {func_name}")

    # 5. Argument count check (best-effort, skip nested formulas)
    _check_arg_counts(body, errors)

    return len(errors) == 0, errors


def _count_top_level_args(args_str: str) -> int:
    """Count comma-separated arguments at the top level (not inside nested parens/quotes)."""
    if not args_str.strip():
        return 0

    count = 1
    depth = 0
    in_string = False

    for ch in args_str:
        if in_string:
            if ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1

    return count


def _check_arg_counts(body: str, errors: List[str]) -> None:
    """Check argument counts for top-level function calls."""
    func_pattern = re.compile(r"([A-Z_][A-Z_0-9]*)\s*\(", re.IGNORECASE)

    for m in func_pattern.finditer(body):
        func_name = m.group(1).upper()
        if func_name not in KNOWN_FUNCTIONS:
            continue

        min_args, max_args = KNOWN_FUNCTIONS[func_name]

        # Extract the argument string for this function
        start = m.end()  # position right after the opening (
        depth = 1
        pos = start
        in_str = False

        while pos < len(body) and depth > 0:
            ch = body[pos]
            if in_str:
                if ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            pos += 1

        if depth != 0:
            continue  # Unbalanced, already caught above

        args_str = body[start:pos - 1]  # Everything between ( and )
        arg_count = _count_top_level_args(args_str)

        if arg_count < min_args:
            errors.append(
                f"{func_name} requires at least {min_args} argument(s), got {arg_count}"
            )
        if max_args is not None and arg_count > max_args:
            errors.append(
                f"{func_name} accepts at most {max_args} argument(s), got {arg_count}"
            )
