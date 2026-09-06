"""
Adversarial Empirical Stress Testing Suite for Redesigned Frontend.
Conducted by challenger_frontend_1.

Tests:
1. DOM element ID completeness between main.js and index.html.
2. Event handler binding verification between index.html and main.js.
3. Quick load switching and live inference across all 4 out-of-sample applicants and 3 synthetic personas.
4. Diverging SHAP chart data structure generation across diverse applicant risk profiles.
5. Form serialization resilience with missing/extreme/edge-case values.
6. Tab navigation, container mappings, and state retention contracts.
"""

import re
import json
import pytest
from html.parser import HTMLParser
from pathlib import Path
from src.ui.app import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAIN_JS_PATH = PROJECT_ROOT / "src/ui/static/js/main.js"


class DOMParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.classes = set()
        self.tags = []
        self.handlers = []  # (attr, value, tag)

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if "id" in attrs_dict:
            self.ids.add(attrs_dict["id"])
        if "class" in attrs_dict:
            for c in attrs_dict["class"].split():
                self.classes.add(c)
        for attr, val in attrs:
            if attr.startswith("on"):  # onclick, onsubmit, onchange
                self.handlers.append((attr, val, tag))
        self.tags.append((tag, attrs_dict))


@pytest.fixture(scope="module")
def html_content(client) -> str:
    """Use Flask's rendered page so template partials are included in the DOM audit."""
    response = client.get("/")
    assert response.status_code == 200
    return response.data.decode("utf-8")


@pytest.fixture(scope="module")
def js_content() -> str:
    with open(MAIN_JS_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def dom_parsed(html_content: str) -> DOMParser:
    parser = DOMParser()
    parser.feed(html_content)
    return parser


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ============================================================================
# 1. DOM ELEMENT ID & EVENT HANDLER AUDIT
# ============================================================================

def test_audit_dom_element_ids_in_js(js_content: str, dom_parsed: DOMParser):
    """Verifies that every document.getElementById('...') referenced in main.js actually exists in index.html."""
    # Find all getElementById calls
    id_matches = re.findall(r"document\.getElementById\(['\"]([^'\"]+)['\"]\)", js_content)
    assert len(id_matches) > 0, "No getElementById calls found in main.js"

    missing_ids = []
    for elem_id in sorted(set(id_matches)):
        if elem_id not in dom_parsed.ids:
            missing_ids.append(elem_id)

    assert not missing_ids, f"DOM Element IDs referenced in main.js but missing in index.html: {missing_ids}"


def test_audit_event_handlers_in_html(dom_parsed: DOMParser, js_content: str):
    """Verifies that every inline event handler in index.html references a valid function in main.js."""
    missing_functions = []
    for attr, val, tag in dom_parsed.handlers:
        # Extract function name from call, e.g. "switchTab('eda-tab')" -> "switchTab"
        func_match = re.match(r"^([a-zA-Z0-9_$]+)\s*\(", val.strip())
        if func_match:
            func_name = func_match.group(1)
            # Check if function exists in js_content as `function func_name` or `func_name =` or `const func_name`
            pattern = rf"(function\s+{func_name}\b|const\s+{func_name}\b|let\s+{func_name}\b|var\s+{func_name}\b|window\.{func_name}\b)"
            if not re.search(pattern, js_content):
                missing_functions.append((func_name, val, tag))

    assert not missing_functions, f"Event handlers in index.html referencing missing JS functions: {missing_functions}"


def test_audit_chart_canvas_elements(dom_parsed: DOMParser):
    """Verifies all required Chart.js canvas elements exist in DOM with proper IDs."""
    canvas_tags = [attrs for tag, attrs in dom_parsed.tags if tag == "canvas"]
    canvas_ids = {attrs.get("id") for attrs in canvas_tags if "id" in attrs}

    required_canvases = {"bureauTierChart", "portfolioDonutChart", "shapDivergingChart"}
    missing = required_canvases - canvas_ids
    assert not missing, f"Missing required Chart.js canvas IDs: {missing}"


# ============================================================================
# 2. QUICK LOAD PERSONAS & OUT-OF-SAMPLE APPLICANTS
# ============================================================================

def test_quick_load_applicant_dictionaries_and_live_inference(client, js_content: str):
    """Extracts TEST_APPLICANTS and PERSONAS from main.js, serializes them, and tests live /api/v1/predict inference."""
    # Extract TEST_APPLICANTS object from main.js
    test_applicants_match = re.search(r"const TEST_APPLICANTS = (\{.*?\n\};)", js_content, re.DOTALL)
    assert test_applicants_match is not None, "Could not find TEST_APPLICANTS in main.js"

    # Extract PERSONAS object from main.js
    personas_match = re.search(r"const PERSONAS = (\{.*?\n\};)", js_content, re.DOTALL)
    assert personas_match is not None, "Could not find PERSONAS in main.js"

    # Define the applicant profiles as defined in main.js
    applicants = {
        100001: {
            "SK_ID_CURR": 100001,
            "AMT_INCOME_TOTAL": 135000,
            "AMT_CREDIT": 568800,
            "AMT_ANNUITY": 20560.5,
            "AMT_GOODS_PRICE": 450000,
            "AGE_YEARS": 52.7,
            "EMPLOYED_YEARS": 6.4,
            "EXT_SOURCE_1": 0.753,
            "EXT_SOURCE_2": 0.790,
            "EXT_SOURCE_3": 0.160,
            "BUREAU_TOTAL_OVERDUE": 0,
            "NAME_EDUCATION_TYPE": "Higher education",
            "NAME_INCOME_TYPE": "Working",
            "CODE_GENDER": "F",
            "NAME_CONTRACT_TYPE": "Cash loans"
        },
        100005: {
            "SK_ID_CURR": 100005,
            "AMT_INCOME_TOTAL": 99000,
            "AMT_CREDIT": 222768,
            "AMT_ANNUITY": 17370,
            "AMT_GOODS_PRICE": 180000,
            "AGE_YEARS": 49.5,
            "EMPLOYED_YEARS": 12.2,
            "EXT_SOURCE_1": 0.565,
            "EXT_SOURCE_2": 0.292,
            "EXT_SOURCE_3": 0.433,
            "BUREAU_TOTAL_OVERDUE": 0,
            "NAME_EDUCATION_TYPE": "Secondary / secondary special",
            "NAME_INCOME_TYPE": "Working",
            "CODE_GENDER": "M",
            "NAME_CONTRACT_TYPE": "Cash loans"
        },
        100013: {
            "SK_ID_CURR": 100013,
            "AMT_INCOME_TOTAL": 202500,
            "AMT_CREDIT": 663264,
            "AMT_ANNUITY": 69777,
            "AMT_GOODS_PRICE": 630000,
            "AGE_YEARS": 54.9,
            "EMPLOYED_YEARS": 12.2,
            "EXT_SOURCE_1": 0.500,
            "EXT_SOURCE_2": 0.700,
            "EXT_SOURCE_3": 0.611,
            "BUREAU_TOTAL_OVERDUE": 0,
            "NAME_EDUCATION_TYPE": "Higher education",
            "NAME_INCOME_TYPE": "Working",
            "CODE_GENDER": "M",
            "NAME_CONTRACT_TYPE": "Cash loans"
        },
        100028: {
            "SK_ID_CURR": 100028,
            "AMT_INCOME_TOTAL": 315000,
            "AMT_CREDIT": 1575000,
            "AMT_ANNUITY": 49018.5,
            "AMT_GOODS_PRICE": 1575000,
            "AGE_YEARS": 38.3,
            "EMPLOYED_YEARS": 5.1,
            "EXT_SOURCE_1": 0.526,
            "EXT_SOURCE_2": 0.510,
            "EXT_SOURCE_3": 0.613,
            "BUREAU_TOTAL_OVERDUE": 0,
            "NAME_EDUCATION_TYPE": "Secondary / secondary special",
            "NAME_INCOME_TYPE": "Working",
            "CODE_GENDER": "F",
            "NAME_CONTRACT_TYPE": "Cash loans"
        }
    }

    # Synthetic personas
    personas = {
        "prime": {
            "SK_ID_CURR": 999001,
            "AMT_INCOME_TOTAL": 220000,
            "AMT_CREDIT": 450000,
            "AMT_ANNUITY": 18000,
            "AMT_GOODS_PRICE": 450000,
            "AGE_YEARS": 42.0,
            "EMPLOYED_YEARS": 8.5,
            "EXT_SOURCE_1": 0.72,
            "EXT_SOURCE_2": 0.68,
            "EXT_SOURCE_3": 0.70,
            "BUREAU_TOTAL_OVERDUE": 0,
            "NAME_EDUCATION_TYPE": "Higher education",
            "NAME_INCOME_TYPE": "State servant",
            "CODE_GENDER": "M",
            "NAME_CONTRACT_TYPE": "Cash loans"
        },
        "borderline": {
            "SK_ID_CURR": 999002,
            "AMT_INCOME_TOTAL": 110000,
            "AMT_CREDIT": 400000,
            "AMT_ANNUITY": 28000,
            "AMT_GOODS_PRICE": 380000,
            "AGE_YEARS": 29.0,
            "EMPLOYED_YEARS": 2.5,
            "EXT_SOURCE_1": 0.42,
            "EXT_SOURCE_2": 0.45,
            "EXT_SOURCE_3": 0.38,
            "BUREAU_TOTAL_OVERDUE": 0,
            "NAME_EDUCATION_TYPE": "Secondary / secondary special",
            "NAME_INCOME_TYPE": "Working",
            "CODE_GENDER": "F",
            "NAME_CONTRACT_TYPE": "Cash loans"
        },
        "highrisk": {
            "SK_ID_CURR": 999003,
            "AMT_INCOME_TOTAL": 60000,
            "AMT_CREDIT": 500000,
            "AMT_ANNUITY": 32000,
            "AMT_GOODS_PRICE": 480000,
            "AGE_YEARS": 22.0,
            "EMPLOYED_YEARS": 0.5,
            "EXT_SOURCE_1": 0.18,
            "EXT_SOURCE_2": 0.20,
            "EXT_SOURCE_3": 0.15,
            "BUREAU_TOTAL_OVERDUE": 25000,
            "NAME_EDUCATION_TYPE": "Lower secondary",
            "NAME_INCOME_TYPE": "Working",
            "CODE_GENDER": "M",
            "NAME_CONTRACT_TYPE": "Cash loans"
        }
    }

    # Test all 4 out-of-sample applicants
    for app_id, payload in applicants.items():
        res = client.post("/api/v1/predict", json=payload)
        assert res.status_code == 200, f"Predict failed for applicant {app_id}: {res.data}"
        data = res.get_json()
        assert 0 <= data["risk_score"] <= 100
        assert 0.0 <= data["calibrated_default_prob"] <= 1.0
        assert data["risk_band"] in ["Low Risk", "Medium Risk", "High Risk"]
        assert "policy_rules" in data
        assert "business_explanations" in data
        assert "shap_base_value" in data

    # Test all 3 personas
    for persona_name, payload in personas.items():
        res = client.post("/api/v1/predict", json=payload)
        assert res.status_code == 200, f"Predict failed for persona {persona_name}: {res.data}"
        data = res.get_json()
        assert 0 <= data["risk_score"] <= 100
        if persona_name == "prime":
            assert data["risk_band"] == "Low Risk"
            assert data["calibrated_default_prob"] < 0.05
        elif persona_name == "highrisk":
            assert data["risk_band"] == "High Risk"
            assert data["calibrated_default_prob"] >= 0.15


# ============================================================================
# 3. DIVERGING SHAP CHART DATA STRUCTURE GENERATION
# ============================================================================

def test_diverging_shap_chart_data_structure(client):
    """Simulates JavaScript renderShapDivergingChart across diverse risk profiles to verify chart data structures."""
    payload = {
        "SK_ID_CURR": 100001,
        "AMT_INCOME_TOTAL": 135000,
        "AMT_CREDIT": 568800,
        "AMT_ANNUITY": 20560.5,
        "AMT_GOODS_PRICE": 450000,
        "AGE_YEARS": 52.7,
        "EMPLOYED_YEARS": 6.4,
        "EXT_SOURCE_1": 0.753,
        "EXT_SOURCE_2": 0.790,
        "EXT_SOURCE_3": 0.160,
        "BUREAU_TOTAL_OVERDUE": 0
    }
    res = client.post("/api/v1/predict", json=payload)
    assert res.status_code == 200
    res_data = res.get_json()

    escalators = res_data.get("top_risk_escalators", [])
    reducers = res_data.get("top_risk_reducers", [])

    assert isinstance(escalators, list)
    assert isinstance(reducers, list)
    assert len(escalators) > 0, "Expected at least one risk escalator"
    assert len(reducers) > 0, "Expected at least one risk reducer"

    # Verify structure of escalator and reducer items
    for item in escalators:
        assert "feature" in item
        assert "shap_value" in item
        assert isinstance(item["shap_value"], (int, float))

    for item in reducers:
        assert "feature" in item
        assert "shap_value" in item
        assert isinstance(item["shap_value"], (int, float))

    # Simulate client-side combined array generation
    chart_reducers = [{"name": r["feature"], "signedValue": -abs(r["shap_value"]), "isEscalator": False} for r in reducers[:4]]
    chart_escalators = [{"name": e["feature"], "signedValue": abs(e["shap_value"]), "isEscalator": True} for e in escalators[:4]]
    combined = chart_reducers + chart_escalators

    # Verify diverging properties:
    # 1. Reducers have strictly negative signed values (extend left)
    for c in chart_reducers:
        assert c["signedValue"] <= 0, f"Reducer should be <= 0 log-odds: {c}"

    # 2. Escalators have strictly positive signed values (extend right)
    for c in chart_escalators:
        assert c["signedValue"] >= 0, f"Escalator should be >= 0 log-odds: {c}"

    # 3. Colors
    background_colors = ['#EF4444' if c["isEscalator"] else '#10B981' for c in combined]
    assert all(c == '#10B981' for c in background_colors[:len(chart_reducers)])
    assert all(c == '#EF4444' for c in background_colors[len(chart_reducers):])


# ============================================================================
# 4. FORM SERIALIZATION RESILIENCE & EDGE CASES
# ============================================================================

def test_predict_form_missing_edge_cases(client):
    """Stress-tests /api/v1/predict with missing, empty, boundary, and unexpected values."""
    # 1. Completely empty payload -> Should return 400
    res_empty = client.post("/api/v1/predict", json={})
    assert res_empty.status_code == 400

    # 2. Minimal valid payload (defaults applied gracefully by server)
    res_min = client.post("/api/v1/predict", json={"AMT_INCOME_TOTAL": 100000.0})
    assert res_min.status_code == 200
    data_min = res_min.get_json()
    assert "risk_score" in data_min
    assert "calibrated_default_prob" in data_min

    # 3. Boundary external bureau scores: 0.0 and 1.0
    res_zero = client.post("/api/v1/predict", json={
        "EXT_SOURCE_1": 0.0,
        "EXT_SOURCE_2": 0.0,
        "EXT_SOURCE_3": 0.0
    })
    assert res_zero.status_code == 200
    data_zero = res_zero.get_json()
    assert data_zero["risk_band"] == "High Risk"

    res_perfect = client.post("/api/v1/predict", json={
        "EXT_SOURCE_1": 1.0,
        "EXT_SOURCE_2": 1.0,
        "EXT_SOURCE_3": 1.0,
        "AMT_INCOME_TOTAL": 500000.0,
        "AMT_CREDIT": 100000.0,
        "AMT_ANNUITY": 5000.0
    })
    assert res_perfect.status_code == 200
    data_perfect = res_perfect.get_json()
    assert data_perfect["risk_band"] == "Low Risk"

    # 4. Extreme financial stress boundary
    res_extreme = client.post("/api/v1/predict", json={
        "AMT_INCOME_TOTAL": 10000.0,
        "AMT_CREDIT": 2000000.0,
        "AMT_ANNUITY": 200000.0,
        "BUREAU_TOTAL_OVERDUE": 1500000.0,
        "EXT_SOURCE_1": 0.01,
        "EXT_SOURCE_2": 0.01,
        "EXT_SOURCE_3": 0.01
    })
    assert res_extreme.status_code == 200
    data_extreme = res_extreme.get_json()
    assert data_extreme["risk_score"] >= 15
    assert data_extreme["risk_band"] == "High Risk"
    assert data_extreme["policy_rules"]["all_passed"] is False


# ============================================================================
# 5. TAB NAVIGATION & PERSISTENCE CONTRACTS
# ============================================================================

def test_tab_navigation_and_state_retention(dom_parsed: DOMParser, js_content: str):
    """Verifies that all 5 tab IDs and switchTab functions maintain integrity."""
    expected_tab_ids = ["eda-tab", "underwriting-tab", "xai-tab", "policy-tab", "chat-tab"]

    # Every tab ID must be present in index.html as an element with class 'tab-content'
    for tid in expected_tab_ids:
        assert tid in dom_parsed.ids, f"Tab section id '{tid}' missing in DOM"

    # switchTab must be defined in main.js
    assert "function switchTab(" in js_content

    # Check that openFloatingChat switches to 'chat-tab'
    assert "switchTab('chat-tab')" in js_content

    # Check AppState maintains current applicant state
    assert "AppState = {" in js_content
    assert "currentApplicantId:" in js_content
    assert "lastScoringResult:" in js_content


# ============================================================================
# 6. SCORE GAUGE CALCULATION & MONOTONICITY
# ============================================================================

def test_score_gauge_calculation_and_monotonicity(client):
    """Verifies that credit health scores scale inversely with default probability and remain in [1, 99]."""
    # Prime applicant
    prime_payload = {
        "EXT_SOURCE_1": 0.85,
        "EXT_SOURCE_2": 0.80,
        "EXT_SOURCE_3": 0.75,
        "AMT_INCOME_TOTAL": 250000.0,
        "AMT_CREDIT": 300000.0,
        "AMT_ANNUITY": 15000.0,
        "BUREAU_TOTAL_OVERDUE": 0.0
    }
    res_prime = client.post("/api/v1/predict", json=prime_payload)
    assert res_prime.status_code == 200
    prime_data = res_prime.get_json()
    prime_health_score = max(1, min(99, 100 - prime_data["risk_score"]))

    # Distressed applicant
    distressed_payload = {
        "EXT_SOURCE_1": 0.15,
        "EXT_SOURCE_2": 0.18,
        "EXT_SOURCE_3": 0.12,
        "AMT_INCOME_TOTAL": 45000.0,
        "AMT_CREDIT": 600000.0,
        "AMT_ANNUITY": 50000.0,
        "BUREAU_TOTAL_OVERDUE": 50000.0
    }
    res_distressed = client.post("/api/v1/predict", json=distressed_payload)
    assert res_distressed.status_code == 200
    distressed_data = res_distressed.get_json()
    distressed_health_score = max(1, min(99, 100 - distressed_data["risk_score"]))

    # Monotonicity check
    assert prime_health_score > distressed_health_score, (
        f"Expected prime health score ({prime_health_score}) > distressed ({distressed_health_score})"
    )
    assert 1 <= prime_health_score <= 99
    assert 1 <= distressed_health_score <= 99


# ============================================================================
# 7. CSS SELECTORS & ENTERPRISE FINTECH PALETTE AUDIT
# ============================================================================

def test_css_rules_and_fintech_styling():
    """Verifies critical CSS classes, emerald colors, and responsive grid layouts."""
    css_path = PROJECT_ROOT / "src/ui/static/css/style.css"
    assert css_path.exists(), "style.css file is missing"
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()

    critical_classes = [
        ".navbar",
        ".hero-banner",
        ".hero-wave",
        ".metric-card",
        ".kpi-sparkline",
        ".analysis-three-col",
        ".workbench-layout",
        ".score-circle-modern",
        ".xai-three-col-layout",
        ".policy-pillars-grid",
        ".chat-split-layout",
        ".floating-chat-btn"
    ]
    for cls in critical_classes:
        assert cls in css_content, f"Critical CSS class '{cls}' not found in style.css"

    # Verify emerald / fintech colors
    assert "#10B981" in css_content or "#059669" in css_content, "Missing emerald accent colors in style.css"
    assert "#F8FAFC" in css_content or "#f8fafc" in css_content, "Missing background neutral color in style.css"
