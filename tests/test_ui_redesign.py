"""
Tests for Redesigned Frontend UI, Interactive Components, and API Workflows.
Covers 4-Tier Test Architecture:
  - Tier 1: Feature Coverage (Navbar badges, hero banner, 4 KPI cards, sparklines,
            Chart.js canvas elements, two-column workbench, score card, toggleable risk factors,
            3-column XAI layout, diverging SHAP canvas, policy pillar cards, risk band matrix,
            Talk-to-Data 2-column layout, floating chat button).
  - Tier 2: Boundary & Corner Cases (empty queries, malformed payloads, invalid types, extreme numbers).
  - Tier 3: Cross-Feature Combinations (Quick Load test applicants #100001, #100005, #100013, #100028,
            and data sync between Tab 2 Underwriting Simulator and Tab 3 Explainable AI).
  - Tier 4: Real-World Workflows (Full multi-step user journey across all 5 tabs and static asset HTTP 200 serving).
"""

import re
import pytest
from html.parser import HTMLParser
from typing import Dict, List, Optional
from src.ui.app import app


# ============================================================================
# Lightweight DOM Parser for Self-Contained HTML Structure Assertions
# ============================================================================

class DOMElement:
    """Represents an HTML tag with its attributes and inner text."""
    def __init__(self, tag: str, attrs: Dict[str, str]):
        self.tag = tag
        self.attrs = attrs
        self.classes = attrs.get("class", "").split()
        self.id = attrs.get("id", "")
        self.text_content: List[str] = []

    def has_class(self, cls: str) -> bool:
        return cls in self.classes

    @property
    def text(self) -> str:
        return " ".join(self.text_content).strip()


class SimpleDOMParser(HTMLParser):
    """Parses HTML into indexed elements for robust structural queries."""
    def __init__(self):
        super().__init__()
        self.elements: List[DOMElement] = []
        self.elements_by_id: Dict[str, DOMElement] = {}
        self.elements_by_tag: Dict[str, List[DOMElement]] = {}
        self._stack: List[DOMElement] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        elem = DOMElement(tag, attrs_dict)
        self.elements.append(elem)
        if elem.id:
            self.elements_by_id[elem.id] = elem
        self.elements_by_tag.setdefault(tag, []).append(elem)
        self._stack.append(elem)

    def handle_endtag(self, tag):
        if self._stack and self._stack[-1].tag == tag:
            self._stack.pop()

    def handle_data(self, data):
        cleaned = data.strip()
        if cleaned and self._stack:
            self._stack[-1].text_content.append(cleaned)

    def find_by_id(self, elem_id: str) -> Optional[DOMElement]:
        return self.elements_by_id.get(elem_id)

    def find_all_by_tag(self, tag: str) -> List[DOMElement]:
        return self.elements_by_tag.get(tag, [])

    def find_all_by_class(self, cls: str) -> List[DOMElement]:
        return [e for e in self.elements if e.has_class(cls)]


def parse_dom(html: str) -> SimpleDOMParser:
    """Helper to parse an HTML string into a queryable DOM tree."""
    parser = SimpleDOMParser()
    parser.feed(html)
    return parser


@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def index_html(client) -> str:
    """Cached index page HTML string."""
    res = client.get("/")
    assert res.status_code == 200
    return res.data.decode("utf-8")


# ============================================================================
# TIER 1: FEATURE COVERAGE
# ============================================================================

def test_tier1_navbar_branding_and_badges(index_html: str):
    """Verifies navbar branding, title, subtitle, and live status badges."""
    dom = parse_dom(index_html)

    # Brand Title and Subtitle
    assert "NeoStats Credit Risk Intelligence" in index_html
    assert "AI-Powered Credit Scoring, XAI & Talk-to-Data Platform" in index_html

    # Brand Logo pill
    logo_elems = dom.find_all_by_class("brand-logo")
    assert len(logo_elems) >= 1
    assert any("NS" in e.text for e in logo_elems)

    # Badges: LightGBM AUC and Groq/Ollama LLM status
    assert re.search(r"LightGBM\s*\(AUC\s*0\.7717\)", index_html) or "LightGBM (AUC 0.7717)" in index_html
    llm_badge = dom.find_by_id("llm-status-badge")
    assert llm_badge is not None
    assert "Groq" in llm_badge.text or "Ollama" in llm_badge.text
    assert "status-dot" in index_html or dom.find_all_by_class("status-dot")

    # Timestamp badge
    assert "Updated:" in index_html


def test_tier1_five_navigation_tabs_and_containers(index_html: str):
    """Verifies all 5 primary application tabs and their corresponding sections."""
    dom = parse_dom(index_html)

    expected_tabs = [
        "Executive EDA",
        "Underwriting Simulator",
        "Explainable AI",
        "Credit Policy Rules",
        "Talk-to-Data",
    ]
    for tab_name in expected_tabs:
        assert tab_name in index_html, f"Missing navigation tab: {tab_name}"

    # 5 Tab Content Containers by ID
    expected_ids = ["eda-tab", "underwriting-tab", "xai-tab", "policy-tab", "chat-tab"]
    for tab_id in expected_ids:
        section = dom.find_by_id(tab_id)
        assert section is not None, f"Missing section container with id '{tab_id}'"
        assert section.has_class("tab-content"), f"Section #{tab_id} missing 'tab-content' class"

    # Default active tab should be eda-tab
    eda_section = dom.find_by_id("eda-tab")
    assert eda_section.has_class("active")


def test_tier1_hero_banner(index_html: str):
    """Verifies the Hero Banner with headline, subtitle, wave motif, and slogan."""
    dom = parse_dom(index_html)

    # Hero Banner Container
    hero_banners = dom.find_all_by_class("hero-banner")
    assert len(hero_banners) >= 1, "Missing .hero-banner container"

    # Headline and Description
    assert "From data to smarter decisions" in index_html
    assert "307,511" in index_html

    # Three-part Slogan
    assert "BETTER DATA" in index_html
    assert "BETTER MODELS" in index_html
    assert "BETTER DECISIONS" in index_html

    # Embedded Wave SVG Motif
    wave_svgs = [e for e in dom.find_all_by_tag("svg") if e.has_class("hero-wave")]
    assert len(wave_svgs) >= 1, "Missing embedded hero-wave SVG motif"


def test_tier1_four_kpi_cards_and_sparklines(index_html: str):
    """Verifies the 4 primary KPI cards with exact values, trend badges, and sparklines."""
    dom = parse_dom(index_html)

    # Check for all 4 exact values in Tab 1
    assert "307,511" in index_html, "Missing 307,511 Total Applications"
    assert "8.07%" in index_html, "Missing 8.07% Portfolio Default Rate"
    assert "305,811" in index_html, "Missing 305,811 External Bureau Records"
    assert "40.67%" in index_html, "Missing 40.67% Separation Power (KS)"

    # Check KPI labels
    assert "TOTAL APPLICATIONS" in index_html
    assert "PORTFOLIO DEFAULT RATE" in index_html
    assert "EXTERNAL BUREAU RECORDS" in index_html
    assert "SEPARATION POWER" in index_html

    # Trend badges
    assert "+100% Coverage" in index_html
    assert "11.39:1 Imbalance" in index_html
    assert "99.4% Match" in index_html or "99.4% Coverage" in index_html
    assert "+0.67% vs Target" in index_html

    # Embedded SVG Sparklines
    sparklines = dom.find_all_by_class("kpi-sparkline")
    assert len(sparklines) >= 4, f"Expected at least 4 KPI sparklines, found {len(sparklines)}"


def test_tier1_three_column_analysis_row_and_charts(index_html: str):
    """Verifies the 3-column analysis row with Chart.js canvas elements and Key Insight."""
    dom = parse_dom(index_html)

    # Col 1: Bureau Tier Bar Chart Canvas
    bureau_canvas = dom.find_by_id("bureauTierChart")
    assert bureau_canvas is not None, "Missing <canvas id='bureauTierChart'>"
    assert bureau_canvas.tag == "canvas"
    assert "Default Rate by External Bureau Score Tier" in index_html
    assert "Critical" in index_html and "23.1%" in index_html
    assert "Subprime" in index_html and "12.2%" in index_html
    assert "Prime" in index_html and "5.9%" in index_html
    assert "Super-Prime" in index_html and "2.9%" in index_html

    # Col 2: Portfolio Composition Donut Chart Canvas
    donut_canvas = dom.find_by_id("portfolioDonutChart")
    assert donut_canvas is not None, "Missing <canvas id='portfolioDonutChart'>"
    assert donut_canvas.tag == "canvas"
    assert "Portfolio Composition" in index_html
    assert "91.9%" in index_html
    assert "282,686" in index_html

    # Col 3: Key Insight Card with Action Link
    assert "Key Insight: Monotonic Bureau Gradient" in index_html
    assert "Rank 1 Feature Driver" in index_html or "Rank 1" in index_html
    assert "7.96x" in index_html or "multiplier" in index_html.lower()
    assert "Explore in Underwriting Simulator" in index_html
    assert "switchTab('underwriting-tab')" in index_html


def test_tier1_bottom_summary_metrics_row(index_html: str):
    """Verifies the bottom summary metrics row in Tab 1."""
    assert "RISK SEGMENTATION" in index_html
    assert "3 Calibrated Bands" in index_html or "3 ML-Derived Tiers" in index_html
    assert "TOP RISK DRIVERS" in index_html or "TOP RISK DRIVER" in index_html
    assert "Bureau Mean" in index_html or "EXT_SOURCES_MEAN" in index_html
    assert "MODEL PERFORMANCE" in index_html
    assert "LightGBM" in index_html
    assert "DATA COVERAGE" in index_html
    assert "142" in index_html


def test_tier1_persistent_floating_chat_button(index_html: str):
    """Verifies the persistent floating chat launcher button."""
    dom = parse_dom(index_html)
    chat_btn = dom.find_by_id("floating-chat-widget")
    assert chat_btn is not None, "Missing #floating-chat-widget"
    assert chat_btn.has_class("floating-chat-btn"), "#floating-chat-widget must have .floating-chat-btn"
    assert "openFloatingChat" in chat_btn.attrs.get("onclick", "") or "switchTab('chat-tab')" in chat_btn.attrs.get("onclick", "")
    assert "chat-badge-pulse" in index_html


def test_tier1_underwriting_workbench_layout(index_html: str):
    """Verifies Tab 2 operational workbench two-column structure."""
    dom = parse_dom(index_html)
    uw_section = dom.find_by_id("underwriting-tab")
    assert uw_section is not None
    assert "Applicant Details" in index_html
    assert "Prediction Result" in index_html
    assert "workbench-layout" in index_html or "split-layout" in index_html


def test_tier1_underwriting_subtabs_and_grouped_inputs(index_html: str):
    """Verifies Tab 2 Manual/Quick Load sub-tabs, test applicant loaders, and inputs."""
    dom = parse_dom(index_html)

    # Sub-tabs
    assert dom.find_by_id("subtab-manual-btn") is not None
    assert dom.find_by_id("subtab-quickload-btn") is not None

    # Test applicant loader buttons
    for app_id in [100001, 100005, 100013, 100028]:
        assert str(app_id) in index_html, f"Missing test applicant button for #{app_id}"

    # Synthetic personas
    assert "Prime Borrower" in index_html
    assert "Borderline" in index_html
    assert "High Risk Default" in index_html

    # Form inputs
    expected_inputs = [
        "inp-age", "inp-education", "inp-family",
        "inp-income", "inp-employed", "inp-income-type",
        "inp-credit", "inp-annuity", "inp-goods",
        "inp-ext1", "inp-ext2", "inp-ext3", "inp-overdue"
    ]
    for inp_id in expected_inputs:
        elem = dom.find_by_id(inp_id)
        assert elem is not None, f"Missing input element with id '{inp_id}'"

    # Action buttons
    assert dom.find_by_id("predict-risk-btn") is not None or "Predict Risk" in index_html
    assert "Reset Form" in index_html or "resetForm()" in index_html


def test_underwriting_decimal_inputs_are_not_limited_to_fixed_steps(index_html: str):
    """Simulator fields must accept values such as 44.6 without browser step validation."""
    dom = parse_dom(index_html)
    for input_id in (
        "inp-age", "inp-income", "inp-employed", "inp-credit", "inp-annuity",
        "inp-goods", "inp-ext1", "inp-ext2", "inp-ext3", "inp-overdue",
    ):
        element = dom.find_by_id(input_id)
        assert element is not None
        assert element.attrs.get("step") == "any"


def test_tier1_underwriting_score_card_and_risk_factors_toggle(index_html: str):
    """Verifies Tab 2 executive score card elements and toggleable risk factor tabs."""
    dom = parse_dom(index_html)

    # Score Card elements
    assert dom.find_by_id("score-circle-color") is not None
    assert dom.find_by_id("res-score") is not None
    assert dom.find_by_id("res-band-badge") is not None
    assert dom.find_by_id("res-confidence-badge") is not None
    assert dom.find_by_id("res-decision") is not None
    assert dom.find_by_id("res-rationale") is not None
    assert dom.find_by_id("res-prob") is not None
    assert dom.find_by_id("res-policy-flag") is not None

    # Toggleable Risk Factor Tabs
    assert dom.find_by_id("tab-risk-incr-btn") is not None
    assert dom.find_by_id("tab-risk-decr-btn") is not None
    assert dom.find_by_id("risk-factors-container") is not None


def test_tier1_xai_three_column_layout(index_html: str):
    """Verifies Tab 3 Explainable AI 3-column layout, diverging SHAP canvas, and cards."""
    dom = parse_dom(index_html)

    # 3-Column Layout Container
    assert "xai-three-col-layout" in index_html or dom.find_all_by_class("xai-three-col-layout")

    # Left Column: Applicant selector & Structured Summary Sheet
    select_elem = dom.find_by_id("xai-applicant-select")
    assert select_elem is not None, "Missing #xai-applicant-select dropdown"
    for app_id in [100001, 100005, 100013, 100028]:
        assert str(app_id) in index_html

    for sheet_id in ["xai-sheet-id", "xai-sheet-age", "xai-sheet-income", "xai-sheet-credit", "xai-sheet-ext"]:
        assert dom.find_by_id(sheet_id) is not None, f"Missing summary sheet field '{sheet_id}'"

    # Middle Column: Top prediction metrics & Horizontal Diverging SHAP Chart
    assert dom.find_by_id("xai-score") is not None
    assert dom.find_by_id("xai-band") is not None
    assert dom.find_by_id("xai-prob") is not None
    assert dom.find_by_id("xai-base-val") is not None
    shap_canvas = dom.find_by_id("shapDivergingChart")
    assert shap_canvas is not None, "Missing <canvas id='shapDivergingChart'>"
    assert shap_canvas.tag == "canvas"
    assert "Reduces Default Hazard" in index_html
    assert "Increases Default Hazard" in index_html

    # Right Column: Plain-English Interpretation Cards
    assert dom.find_by_id("interp-strength-text") is not None
    assert dom.find_by_id("interp-vulnerability-text") is not None
    assert dom.find_by_id("interp-recommendation-text") is not None
    assert "Primary Credit Strength" in index_html
    assert "Primary Vulnerability" in index_html
    assert "Underwriting Recommendation" in index_html


def test_tier1_policy_pillars_and_risk_matrix(index_html: str):
    """Verifies Tab 4 policy pillar cards, risk matrix table, and amber governance callout."""
    dom = parse_dom(index_html)

    # 4 Policy Pillar Cards
    assert "3 Risk Bands" in index_html
    assert "Monotonic Default Rate" in index_html
    assert "Data-Driven Thresholds" in index_html
    assert "Decision Support" in index_html

    # Risk Bands & Actions Matrix
    assert "Low Risk" in index_html and "50.9%" in index_html and "2.67%" in index_html and "Fast-Track (STP)" in index_html
    assert "Medium Risk" in index_html and "35.7%" in index_html and "9.08%" in index_html and "Manual Review" in index_html
    assert "High Risk" in index_html and "13.4%" in index_html and "25.90%" in index_html and "Strict / Decline" in index_html

    # Defaulter Capture Metric
    assert "43.02%" in index_html

    # Amber Governance Callout Box
    assert "Regulatory Compliance & Decision-Support Notice" in index_html or "Regulatory Compliance" in index_html
    assert "ML-derived decision-support guardrails" in index_html

    # Active Policy Rules Audit Table
    assert dom.find_by_id("policy-rules-tbody") is not None


def test_tier1_talk_to_data_two_column_layout(index_html: str):
    """Verifies Tab 5 Talk-to-Data two-column workbench, dropdown, and example questions."""
    dom = parse_dom(index_html)

    # Left Column: "Try an example" dropdown, chat stream, input form
    assert dom.find_by_id("chat-example-select") is not None or dom.find_by_id("chat-preset-select") is not None
    assert dom.find_by_id("chat-history") is not None
    assert dom.find_by_id("chat-form") is not None
    assert dom.find_by_id("chat-input") is not None
    assert dom.find_by_id("chat-submit-btn") is not None

    # Right Column: 5 Interactive Example Questions Cards
    expected_questions = [
        "What is the default rate across different education levels?",
        "Show average credit amount and default rate by income type.",
        "How do external credit bureau scores impact default rates?",
        "Compare default rates for applicants with prior bureau overdue debt versus clean credit histories.",
        "Which demographic clusters by gender and family status have the highest default rates?",
    ]
    for q in expected_questions:
        assert q in index_html, f"Missing example inquiry question: '{q}'"


# ============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ============================================================================

def test_tier2_boundary_empty_chat_queries(client):
    """Verifies empty and whitespace queries return HTTP 400."""
    for empty_q in ["", "   ", "\t\n"]:
        res = client.post("/api/v1/query", json={"question": empty_q})
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data
        assert "Empty or invalid question" in data["error"]

    # Also test query key alias
    res = client.post("/api/v1/query", json={"query": ""})
    assert res.status_code == 400


def test_tier2_boundary_malformed_chat_payloads(client):
    """Verifies malformed data types in chat endpoints return HTTP 400."""
    invalid_payloads = [
        {"question": 12345},
        {"question": ["invalid", "list"]},
        {"question": None},
        {"invalid_key": "where is the data?"},
        {}
    ]
    for p in invalid_payloads:
        res = client.post("/api/v1/query", json=p)
        assert res.status_code == 400, f"Expected 400 for payload: {p}"


def test_tier2_boundary_predict_empty_and_malformed_payloads(client):
    """Verifies empty or non-dict payloads to /api/v1/predict return HTTP 400."""
    res = client.post("/api/v1/predict", data="", content_type="application/json")
    assert res.status_code == 400
    assert "Invalid or missing JSON payload" in res.get_json()["error"]

    res = client.post("/api/v1/predict", json={})
    assert res.status_code == 400
    assert "Invalid or missing JSON payload" in res.get_json()["error"]


def test_tier2_boundary_predict_invalid_data_types(client):
    """Verifies type validation errors in applicant numerical fields return HTTP 400."""
    invalid_cases = [
        {"AMT_INCOME_TOTAL": "invalid_string"},
        {"AMT_INCOME_TOTAL": None},
        {"EXT_SOURCE_1": [0.5, 0.6]}
    ]
    for case in invalid_cases:
        res = client.post("/api/v1/predict", json=case)
        assert res.status_code == 400
        assert "Invalid input format or type" in res.get_json()["error"]


def test_tier2_boundary_predict_extreme_numerical_inputs(client):
    """Verifies inference stability under extreme financial boundary conditions."""
    # Ultra-wealthy applicant
    res_wealthy = client.post("/api/v1/predict", json={
        "AMT_INCOME_TOTAL": 100000000.0,
        "AMT_CREDIT": 50000000.0,
        "AMT_ANNUITY": 500000.0,
        "EXT_SOURCE_1": 0.99,
        "EXT_SOURCE_2": 0.99,
        "EXT_SOURCE_3": 0.99,
        "BUREAU_TOTAL_OVERDUE": 0.0
    })
    assert res_wealthy.status_code == 200
    data_wealthy = res_wealthy.get_json()
    assert 0 <= data_wealthy["risk_score"] <= 100
    assert data_wealthy["risk_band"] == "Low Risk"
    assert data_wealthy["calibrated_default_prob"] < 0.05

    # Severe financial distress & massive delinquency
    res_distress = client.post("/api/v1/predict", json={
        "AMT_INCOME_TOTAL": 12000.0,
        "AMT_CREDIT": 600000.0,
        "AMT_ANNUITY": 45000.0,
        "EXT_SOURCE_1": 0.02,
        "EXT_SOURCE_2": 0.04,
        "EXT_SOURCE_3": 0.01,
        "BUREAU_TOTAL_OVERDUE": 2500000.0
    })
    assert res_distress.status_code == 200
    data_distress = res_distress.get_json()
    assert 0 <= data_distress["risk_score"] <= 100
    assert data_distress["risk_band"] == "High Risk"
    assert data_distress["policy_rules"]["flags"]["FLAG_PAST_DUE"] is True
    assert data_distress["policy_rules"]["flags"]["FLAG_HIGH_DTI"] is True
    assert data_distress["policy_rules"]["all_passed"] is False


# ============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# ============================================================================

def test_tier3_quick_load_applicant_100001(client):
    """Verifies scoring and XAI attributions for Prime Borrower #100001."""
    res = client.post("/api/v1/predict", json={
        "SK_ID_CURR": 100001,
        "AMT_INCOME_TOTAL": 135000.0,
        "AMT_CREDIT": 568800.0,
        "AMT_ANNUITY": 20560.5,
        "AMT_GOODS_PRICE": 450000.0,
        "DAYS_BIRTH": -19241,
        "DAYS_EMPLOYED": -2329,
        "EXT_SOURCE_1": 0.753,
        "EXT_SOURCE_2": 0.790,
        "EXT_SOURCE_3": 0.160,
        "BUREAU_TOTAL_OVERDUE": 0.0,
        "NAME_EDUCATION_TYPE": "Higher education",
        "NAME_INCOME_TYPE": "Working"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["applicant_id"] == 100001
    assert data["risk_band"] == "Low Risk"
    assert data["calibrated_default_prob"] < 0.05
    assert data["policy_rules"]["all_passed"] is True
    assert len(data["top_risk_reducers"]) > 0


def test_tier3_quick_load_applicant_100005(client):
    """Verifies scoring and policy checks for Medium Risk profile #100005."""
    res = client.post("/api/v1/predict", json={
        "SK_ID_CURR": 100005,
        "AMT_INCOME_TOTAL": 99000.0,
        "AMT_CREDIT": 222768.0,
        "AMT_ANNUITY": 17370.0,
        "AMT_GOODS_PRICE": 180000.0,
        "DAYS_BIRTH": -18064,
        "DAYS_EMPLOYED": -4469,
        "EXT_SOURCE_1": 0.565,
        "EXT_SOURCE_2": 0.292,
        "EXT_SOURCE_3": 0.433,
        "BUREAU_TOTAL_OVERDUE": 0.0,
        "NAME_EDUCATION_TYPE": "Secondary / secondary special",
        "NAME_INCOME_TYPE": "Working"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["applicant_id"] == 100005
    assert 0 <= data["risk_score"] <= 100
    assert "calibrated_default_prob" in data
    assert "policy_rules" in data


def test_tier3_quick_load_applicant_100013(client):
    """Verifies payment stress indicators for applicant #100013."""
    res = client.post("/api/v1/predict", json={
        "SK_ID_CURR": 100013,
        "AMT_INCOME_TOTAL": 202500.0,
        "AMT_CREDIT": 663264.0,
        "AMT_ANNUITY": 69777.0,
        "AMT_GOODS_PRICE": 630000.0,
        "DAYS_BIRTH": -20043,
        "DAYS_EMPLOYED": -4458,
        "EXT_SOURCE_1": 0.500,
        "EXT_SOURCE_2": 0.700,
        "EXT_SOURCE_3": 0.611,
        "BUREAU_TOTAL_OVERDUE": 0.0
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["applicant_id"] == 100013
    # Annuity is high (~$69.8k on $202.5k income, ~34.5% DTI), payment rate is ~10.5%
    assert len(data["top_risk_escalators"]) > 0


def test_tier3_quick_load_applicant_100028(client):
    """Verifies jumbo line underwriting evaluation for applicant #100028."""
    res = client.post("/api/v1/predict", json={
        "SK_ID_CURR": 100028,
        "AMT_INCOME_TOTAL": 315000.0,
        "AMT_CREDIT": 1575000.0,
        "AMT_ANNUITY": 49018.5,
        "AMT_GOODS_PRICE": 1575000.0,
        "DAYS_BIRTH": -13976,
        "DAYS_EMPLOYED": -1866,
        "EXT_SOURCE_1": 0.526,
        "EXT_SOURCE_2": 0.510,
        "EXT_SOURCE_3": 0.613,
        "BUREAU_TOTAL_OVERDUE": 0.0
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["applicant_id"] == 100028
    assert isinstance(data["shap_base_value"], (float, int))
    assert len(data["business_explanations"]) >= 1


def test_tier3_sync_between_tab2_score_and_tab3_shap(client):
    """
    Verifies that the /api/v1/predict response provides complete,
    synchronized payloads for both Tab 2 (Score Card) and Tab 3 (SHAP Divergence).
    """
    res = client.post("/api/v1/predict", json={
        "SK_ID_CURR": 100001,
        "AMT_INCOME_TOTAL": 135000.0,
        "AMT_CREDIT": 568800.0,
        "AMT_ANNUITY": 20560.5,
        "EXT_SOURCE_1": 0.753,
        "EXT_SOURCE_2": 0.790,
        "EXT_SOURCE_3": 0.160
    })
    assert res.status_code == 200
    data = res.get_json()

    # Data contract required by Tab 2 (Score Card & Factors)
    tab2_keys = [
        "risk_score", "risk_band", "calibrated_default_prob",
        "underwriting_decision", "decision_rationale", "policy_rules"
    ]
    for k in tab2_keys:
        assert k in data, f"Missing Tab 2 key: {k}"

    # Data contract required by Tab 3 (SHAP Explanations & Diverging Bar Chart)
    tab3_keys = [
        "shap_base_value", "top_risk_escalators", "top_risk_reducers", "business_explanations"
    ]
    for k in tab3_keys:
        assert k in data, f"Missing Tab 3 key: {k}"

    # Verify SHAP factor attributes for horizontal diverging chart
    for factor in data["top_risk_reducers"]:
        assert "feature" in factor
        assert "shap_value" in factor
        assert factor["shap_value"] <= 0  # Negative log-odds reduce risk (green bars left)

    for factor in data["top_risk_escalators"]:
        assert "feature" in factor
        assert "shap_value" in factor
        assert factor["shap_value"] >= 0  # Positive log-odds increase risk (red bars right)


# ============================================================================
# TIER 4: REAL-WORLD WORKFLOWS
# ============================================================================

def test_tier4_static_asset_serving(client):
    """Verifies that all redesigned static assets (CSS, JS) are served with HTTP 200."""
    css_res = client.get("/static/css/style.css")
    assert css_res.status_code == 200
    assert "text/css" in css_res.headers.get("Content-Type", "")
    assert len(css_res.data) > 5000, "style.css appears incomplete"

    js_res = client.get("/static/js/main.js")
    assert js_res.status_code == 200
    assert any(ct in js_res.headers.get("Content-Type", "") for ct in ["javascript", "text/plain"])
    assert len(js_res.data) > 5000, "main.js appears incomplete"


def test_tier4_full_user_journey(client):
    """
    Simulates a complete real-world credit risk analyst workflow across all 5 tabs:
    1. Loads the main dashboard (Tab 1 Executive EDA).
    2. Requests portfolio EDA metrics and empirical insights.
    3. Operates the Underwriting Simulator with applicant data (Tab 2).
    4. Explores the Explainable AI local SHAP factors (Tab 3).
    5. Reviews Credit Policy Rules and deterministic guardrail flags (Tab 4).
    6. Interacts with the Talk-to-Data conversational assistant via natural language (Tab 5).
    """
    # Step 1: Access Homepage (Tab 1)
    page_res = client.get("/")
    assert page_res.status_code == 200
    assert b"NeoStats Credit Risk Intelligence" in page_res.data
    assert b"From data to smarter decisions" in page_res.data

    # Step 2: Fetch EDA Portfolio Insights
    eda_res = client.get("/api/eda/insights")
    assert eda_res.status_code == 200
    eda_data = eda_res.get_json()
    assert eda_data["portfolio"]["total_applications"] == 307511
    assert eda_data["portfolio"]["overall_default_rate_pct"] == 8.07
    assert len(eda_data["insights_list"]) == 5

    # Step 3: Run Underwriting Simulator for Prime Applicant #100001 (Tab 2)
    score_res = client.post("/api/v1/predict", json={
        "SK_ID_CURR": 100001,
        "AMT_INCOME_TOTAL": 135000.0,
        "AMT_CREDIT": 568800.0,
        "AMT_ANNUITY": 20560.5,
        "AMT_GOODS_PRICE": 450000.0,
        "EXT_SOURCE_1": 0.753,
        "EXT_SOURCE_2": 0.790,
        "EXT_SOURCE_3": 0.160,
        "BUREAU_TOTAL_OVERDUE": 0.0
    })
    assert score_res.status_code == 200
    score_data = score_res.get_json()
    assert score_data["risk_band"] == "Low Risk"
    assert score_data["calibrated_default_prob"] < 0.05
    assert "Fast-Track" in score_data["underwriting_decision"]

    # Step 4: Examine Explainable AI SHAP Attribution (Tab 3)
    assert isinstance(score_data["shap_base_value"], (float, int))
    assert len(score_data["top_risk_reducers"]) > 0
    assert len(score_data["business_explanations"]) > 0

    # Step 5: Check Deterministic Policy Guardrails (Tab 4)
    rules_data = score_data["policy_rules"]
    assert rules_data["all_passed"] is True
    assert rules_data["failed_count"] == 0
    assert rules_data["flags"]["FLAG_PAST_DUE"] is False
    assert rules_data["flags"]["FLAG_HIGH_DTI"] is False

    # Step 6: Ask Conversational Question via Talk-to-Data (Tab 5)
    chat_res = client.post("/api/v1/query", json={
        "question": "What is the default rate across different education levels?"
    })
    assert chat_res.status_code == 200
    chat_data = chat_res.get_json()
    assert chat_data["success"] is True
    assert "SELECT" in chat_data["sql"].upper()
    assert len(chat_data["data"]) > 0
    assert chat_data["business_insight"] is not None
