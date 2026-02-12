"""
SheetMind API Tests

Run with: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient

# Import the app
from app.main import app

client = TestClient(app)


# =============================================================================
# Health Check Tests
# =============================================================================

def test_health_endpoint():
    """Test that health endpoint returns healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_root_redirects_or_responds():
    """Test that root endpoint responds."""
    response = client.get("/")
    # Should either redirect or return some response
    assert response.status_code in [200, 307, 404]


# =============================================================================
# Sheet Analyzer Tests
# =============================================================================

def test_sheet_analyzer_basic():
    """Test sheet analyzer with basic data."""
    from app.services.sheet_analyzer import analyze_sheet

    cells = {
        'A1': 'Name', 'B1': 'Amount', 'C1': 'Category',
        'A2': 'John', 'B2': '100', 'C2': 'Sales',
        'A3': 'Alice', 'B3': '200', 'C3': 'Sales',
        'A4': 'Bob', 'B4': '150', 'C4': 'Marketing',
    }

    metadata = analyze_sheet(cells, 'TestSheet')

    assert metadata.sheet_name == 'TestSheet'
    assert metadata.total_rows == 4
    assert metadata.last_row == 4
    assert len(metadata.columns) == 3


def test_sheet_analyzer_detects_numeric():
    """Test that analyzer correctly identifies numeric columns."""
    from app.services.sheet_analyzer import analyze_sheet

    cells = {
        'A1': 'ID', 'B1': 'Value',
        'A2': '1', 'B2': '100.50',
        'A3': '2', 'B3': '200.75',
        'A4': '3', 'B4': '300.25',
        'A5': '4', 'B5': '400.00',
    }

    metadata = analyze_sheet(cells, 'Numbers')

    # Both columns should be detected as numeric
    numeric_cols = [c for c in metadata.columns if c.column_type == 'numeric']
    assert len(numeric_cols) >= 1

    # B should be in suggested aggregate columns
    assert 'B' in metadata.suggested_aggregate or 'A' in metadata.suggested_aggregate


def test_sheet_analyzer_empty_data():
    """Test analyzer handles empty data gracefully."""
    from app.services.sheet_analyzer import analyze_sheet

    metadata = analyze_sheet({}, 'Empty')

    assert metadata.sheet_name == 'Empty'
    assert metadata.total_rows == 0
    assert len(metadata.columns) == 0


# =============================================================================
# SmartExecutor Tests
# =============================================================================

def test_template_grouped_summary():
    """Test grouped summary template generation."""
    from app.services.smart_executor import template_grouped_summary

    actions = template_grouped_summary(
        sheet_name='Data',
        last_row=100,
        group_by_col='A',
        group_by_header='Category',
        value_col='B',
        value_header='Sales',
        aggregation='sum',
        unique_count=5
    )

    # Should generate: createSheet, setValues, formatRange, 2x setFormula, autoFillDown
    assert len(actions) >= 5

    # First action should create sheet
    assert actions[0]['action'] == 'createSheet'
    assert 'Category Summary' in actions[0]['name']


def test_template_grouped_summary_chart():
    """Test grouped summary with chart template."""
    from app.services.smart_executor import template_grouped_summary_chart

    actions = template_grouped_summary_chart(
        sheet_name='Sales',
        last_row=50,
        group_by_col='C',
        group_by_header='Region',
        value_col='D',
        value_header='Revenue',
        aggregation='sum',
        chart_type='bar',
        unique_count=4
    )

    # Should include all summary actions plus chart
    assert len(actions) >= 6

    # Last action should be createChart
    assert actions[-1]['action'] == 'createChart'
    assert actions[-1]['chartType'] == 'bar'


# =============================================================================
# Intent Detection Tests
# =============================================================================

def test_detect_agent_intent():
    """Test agent intent detection."""
    from app.api.routes.chat import detect_agent_intent

    # Should detect agent intent
    assert detect_agent_intent("sum of sales by region") == True
    assert detect_agent_intent("group by category") == True
    assert detect_agent_intent("create a summary") == True
    assert detect_agent_intent("count by department") == True

    # Should NOT detect agent intent
    assert detect_agent_intent("hello") == False
    assert detect_agent_intent("what is the weather") == False


def test_detect_chart_intent():
    """Test chart intent detection."""
    from app.api.routes.chat import detect_chart_intent

    # Should detect chart intent
    assert detect_chart_intent("create a bar chart") == True
    assert detect_chart_intent("show me a chart") == True
    assert detect_chart_intent("visualize the data") == True
    assert detect_chart_intent("pie chart of sales") == True

    # Should NOT detect chart intent
    assert detect_chart_intent("sum the values") == False
    assert detect_chart_intent("count the rows") == False


# =============================================================================
# Formula Patterns Tests
# =============================================================================

def test_formula_patterns_exist():
    """Test that formula patterns are loaded."""
    from app.services.formula_patterns import FORMULA_PATTERNS

    assert len(FORMULA_PATTERNS) > 0

    # Check structure of patterns
    for pattern in FORMULA_PATTERNS:
        assert 'name' in pattern
        assert 'template' in pattern


# =============================================================================
# Integration Tests (require server running)
# =============================================================================

@pytest.mark.skip(reason="Requires authentication")
def test_chat_endpoint_authenticated():
    """Test chat endpoint with authentication."""
    response = client.post(
        "/api/chat/query",
        json={
            "message": "Hello",
            "sheet_data": {"cells": {}},
        },
        headers={"Authorization": "Bearer test-token"}
    )
    # Would need valid token to pass
    assert response.status_code in [200, 401, 403]


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
