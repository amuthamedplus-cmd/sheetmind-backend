"""
PII (Personally Identifiable Information) detector for sheet data.

Scans cell values for common PII patterns and returns warnings.
Does NOT redact data — the user may legitimately need to query it.
Instead, surfaces a warning so the user knows sensitive data will be
sent to third-party LLM APIs.
"""

import re
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# PII Patterns
# ---------------------------------------------------------------------------

PII_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    (
        "SSN",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "Social Security Numbers",
    ),
    (
        "credit_card",
        re.compile(
            r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))"
            r"[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{3,4}\b"
        ),
        "credit card numbers",
    ),
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "email addresses",
    ),
    (
        "phone",
        re.compile(
            r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        "phone numbers",
    ),
    (
        "ip_address",
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
        ),
        "IP addresses",
    ),
]

# Columns whose headers strongly suggest PII
SENSITIVE_HEADERS = {
    "ssn", "social security", "social_security",
    "password", "passwd", "pwd",
    "credit card", "credit_card", "card number", "card_number",
    "cvv", "cvc", "security code",
    "dob", "date of birth", "date_of_birth", "birthdate",
    "passport", "passport number", "passport_number",
    "driver license", "drivers license", "dl number",
    "bank account", "account number", "routing number",
    "tax id", "tin", "ein",
}


def scan_cells(cells: Dict[str, str], sample_limit: int = 200) -> Dict:
    """
    Scan sheet cells for potential PII.

    Args:
        cells: Cell reference → value mapping (e.g. {"A1": "Name", "A2": "john@example.com"})
        sample_limit: Max number of cells to scan (for performance on large sheets)

    Returns:
        Dict with:
            - has_pii: bool
            - types_found: list of PII type labels detected
            - warning: human-readable warning string (empty if no PII)
            - sensitive_columns: list of column letters with suspicious headers
    """
    types_found: Dict[str, int] = {}
    sensitive_columns: List[str] = []

    # Check headers (row 1) for sensitive column names
    cell_pattern = re.compile(r"^([A-Z]+)(\d+)$")
    for ref, value in cells.items():
        match = cell_pattern.match(ref)
        if not match:
            continue
        col, row = match.group(1), int(match.group(2))
        if row == 1:
            header_lower = str(value).lower().strip()
            if header_lower in SENSITIVE_HEADERS:
                sensitive_columns.append(f"{col} ({value})")

    # Sample cell values for pattern matching
    sampled = 0
    for ref, value in cells.items():
        if sampled >= sample_limit:
            break
        val_str = str(value)
        if len(val_str) < 5:  # Skip very short values
            continue
        sampled += 1

        for pii_type, pattern, label in PII_PATTERNS:
            if pattern.search(val_str):
                types_found[pii_type] = types_found.get(pii_type, 0) + 1

    # Build result
    has_pii = bool(types_found) or bool(sensitive_columns)

    warning_parts = []
    if types_found:
        labels = []
        for pii_type, count in types_found.items():
            label = next(
                (l for t, _, l in PII_PATTERNS if t == pii_type),
                pii_type,
            )
            labels.append(f"{label} ({count} found)")
        warning_parts.append(
            "Detected potential PII in your sheet data: " + ", ".join(labels) + "."
        )

    if sensitive_columns:
        warning_parts.append(
            "Columns with sensitive headers: " + ", ".join(sensitive_columns) + "."
        )

    if warning_parts:
        warning_parts.append(
            "This data will be sent to an external AI service for processing."
        )

    return {
        "has_pii": has_pii,
        "types_found": list(types_found.keys()),
        "sensitive_columns": sensitive_columns,
        "warning": " ".join(warning_parts),
    }
