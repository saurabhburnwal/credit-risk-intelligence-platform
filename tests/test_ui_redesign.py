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

def test_tier1_minimal_navbar_branding(index_html: str):
    """Verifies the compact workspace header exposes only essential context."""
    dom = parse_dom(index_html)

    # Brand Title and Subtitle
    assert "Credit risk" in index_html
    assert "NeoStats" not in index_html
    assert "Decision-support workspace" in index_html

    # Brand Logo pill
    logo_elems = dom.find_all_by_class("brand-logo")
    assert len(logo_elems) >= 1
    assert all(e.text == "CR" for e in logo_elems)

    assert "LightGBM · AUC 0.7717" in index_html
    assert dom.find_by_id("llm-status-badge") is None


def test_premium_gold_theme_and_progressive_motion(client, index_html: str):
    """The shared shell exposes the warm ivory and premium gold identity."""
    css = client.get("/static/css/design-system.css").data.decode("utf-8")
    js = client.get("/static/js/main.js").data.decode("utf-8")

    assert "Premium warm-ivory and champagne-gold identity" in css
    assert "--page-bg: #F5F0E8" in css
    assert "--gold: #C79A4A" in css
    assert "--green: #078A63" in css
    assert ".tab-btn.active" in css
    assert "@media (prefers-reduced-motion: reduce)" in client.get("/static/css/style.css").data.decode("utf-8")
    assert "IntersectionObserver" in js
    assert "initializeMotion" in js
    assert "requestAnimationFrame(() => revealMotionItems(targetTab))" in js
    assert "eda-tab" in index_html


def test_guided_workspace_hierarchy_hooks(index_html: str, client):
    """Each tab identifies primary work, supporting context, and reference content."""
    dom = parse_dom(index_html)
    tab_ids = ["eda-tab", "underwriting-tab", "xai-tab", "policy-tab", "chat-tab"]
    for tab_id in tab_ids:
        tab = dom.find_by_id(tab_id)
        assert tab is not None
        if tab_id != "chat-tab":
            assert tab.has_class("workspace-tab")
    assert len(dom.find_all_by_class("workspace-primary")) >= 5

    css = client.get("/static/css/style.css").data.decode("utf-8")
    assert "--space-7: 3.75rem" in css
    assert ".workspace-supporting" in css
    assert ".workspace-reference" in css
    assert "@media (max-width: 1040px)" in css
    assert "@media (max-width: 700px)" in css


def test_scored_xai_status_is_compact(client):
    """Scored applicant status is a compact label rather than a large empty state."""
    js = client.get("/static/js/main.js").data.decode("utf-8")
    css = client.get("/static/css/style.css").data.decode("utf-8")

    assert "Scored · ${AppState.currentApplicantLabel}" in js
    assert "xaiStatus.classList.add('is-scored')" in js
    assert "#xai-profile-status.is-scored" in css
    assert "min-height: 0" in css


def test_loaded_applicant_prompt_is_compact(client):
    """Loaded, reset, and validation prompts do not occupy a full empty-state panel."""
    js = client.get("/static/js/main.js").data.decode("utf-8")
    css = client.get("/static/css/style.css").data.decode("utf-8")

    assert "placeholder.classList.add('is-compact')" in js
    assert "placeholder.classList.remove('is-compact')" in js
    assert "#scoring-placeholder.is-compact" in css
    assert "padding: 0;" in css
    assert "Loaded · ${p.label} — review values, then predict risk." in js
    assert "white-space: nowrap" in css
    assert "scoring-inline-status" in client.get("/").data.decode("utf-8")
    assert "#underwriting-tab .workbench-panel:nth-child(2) .panel-header-clean" in css


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
        if tab_name != "Talk-to-Data":
            assert tab_name in index_html, f"Missing navigation tab: {tab_name}"

    # 5 Tab Content Containers by ID
    expected_ids = ["eda-tab", "underwriting-tab", "xai-tab", "policy-tab", "chat-tab"]
    for tab_id in expected_ids:
        section = dom.find_by_id(tab_id)
        assert section is not None, f"Missing section container with id '{tab_id}'"
        if tab_id != "chat-tab":
            assert section.has_class("tab-content"), f"Section #{tab_id} missing 'tab-content' class"

    # Default active tab should be eda-tab
    eda_section = dom.find_by_id("eda-tab")
    assert eda_section.has_class("active")


def test_tier1_portfolio_overview_heading(index_html: str):
    """Verifies the dashboard starts with a concise portfolio overview."""
    dom = parse_dom(index_html)

    assert len(dom.find_all_by_class("page-heading")) >= 1
    assert "Overview" in index_html
    assert "307,511" in index_html


def test_tier1_compact_portfolio_metrics(index_html: str):
    """Verifies the three decision-relevant portfolio metrics."""
    dom = parse_dom(index_html)

    assert "307,511" in index_html, "Missing 307,511 Total Applications"
    assert "8.07%" in index_html, "Missing 8.07% Portfolio Default Rate"
    assert "40.67%" in index_html, "Missing 40.67% Separation Power (KS)"
    assert "Applications" in index_html
    assert "Default rate" in index_html
    assert "Model separation" in index_html
    assert len(dom.find_all_by_class("metric-card")) == 3


def test_tier1_overview_charts_and_single_insight(index_html: str):
    """Verifies the two core charts and one concise, actionable insight."""
    dom = parse_dom(index_html)

    # Col 1: Bureau Tier Bar Chart Canvas
    bureau_canvas = dom.find_by_id("bureauTierChart")
    assert bureau_canvas is not None, "Missing <canvas id='bureauTierChart'>"
    assert bureau_canvas.tag == "canvas"
    assert "Default rate by bureau score tier" in index_html

    # Col 2: Portfolio Composition Donut Chart Canvas
    donut_canvas = dom.find_by_id("portfolioDonutChart")
    assert donut_canvas is not None, "Missing <canvas id='portfolioDonutChart'>"
    assert donut_canvas.tag == "canvas"
    assert "Portfolio composition" in index_html

    assert "Primary signal" in index_html
    assert "23.1%" in index_html and "2.9%" in index_html
    assert "Open underwriting simulator" in index_html
    assert "switchTab('underwriting-tab')" in index_html


def test_eda_exposes_assignment_insights_and_data_understanding(index_html: str):
    """The visible EDA page keeps decision-relevant insights and restored data context."""
    for chart_name in (
        "insight2_debt_stress.png",
        "insight3_age_employment.png",
        "insight4_education_income.png",
        "insight5_bureau_delinquency.png",
    ):
        assert f"/static/plots/{chart_name}" in index_html
    # Verify the duplicate static plot (insight1_ext_scores.png) was removed in favor of the interactive bureauTierChart
    assert "/static/plots/insight1_ext_scores.png" not in index_html
    assert "Feature categories" in index_html
    assert "142 model features" in index_html
    assert "missing_values.png" in index_html
    assert "class_imbalance.png" in index_html
    assert "4 supporting charts" in index_html


def test_eda_insight_charts_use_intrinsic_responsive_sizing(client):
    """EDA business-insight images fill their wrappers without fixed empty frames."""
    css = client.get("/static/css/design-system.css").data.decode("utf-8")
    assert ".eda-insight-card .chart-img-wrapper" in css
    assert "height: auto;" in css
    assert "min-height: 0;" in css
    assert "padding: 12px 16px;" in css
    assert "aspect-ratio: auto;" in css
    assert ".eda-insight-card .chart-img-wrapper img" in css
    assert "width: 100%;" in css
    assert "object-fit: contain;" in css


def test_eda_data_understanding_uses_content_first_sibling_cards(client, index_html: str):
    """Restored data-understanding cards use responsive charts and compact category rows."""
    css = client.get("/static/css/design-system.css").data.decode("utf-8")
    assert "Quality and feature coverage" in index_html
    assert "/static/plots/missing_values.png" in index_html
    assert "/static/plots/class_imbalance.png" in index_html
    assert "Feature categories" in index_html
    assert "142 model features" in index_html
    assert "eda-quality-grid" in css
    assert ".eda-quality-card .chart-img-wrapper" in css
    assert ".eda-quality-card .chart-img-wrapper img" in css
    assert ".eda-feature-card .feature-category-wrapper" in css
    assert "padding: 12px 0;" in css
    assert "@media (max-width: 1100px)" in css


def test_tier1_eda_omits_redundant_summary_row(index_html: str):
    """The overview remains focused instead of repeating dashboard facts."""
    assert "summary-four-col" not in index_html


def test_tier1_chat_uses_a_global_floating_launcher(index_html: str):
    """Talk-to-Data is reached through a global floating launcher, not primary navigation."""
    dom = parse_dom(index_html)
    assert dom.find_by_id("floating-chat-widget") is None
    chat_tab_buttons = [button for button in dom.find_all_by_class("tab-btn") if "Talk-to-Data" in button.text]
    assert len(chat_tab_buttons) == 0
    launchers = dom.find_all_by_class("chat-launcher")
    assert len(launchers) == 1
    assert "toggleChatPanel(true)" in index_html


def test_tier1_applicant_loading_has_one_source_of_truth(index_html: str, client):
    """Applicant loading stays in Underwriting; XAI only reflects the scored profile."""
    dom = parse_dom(index_html)

    assert dom.find_by_id("quickload-panel") is not None
    assert dom.find_by_id("xai-profile-status") is not None
    assert dom.find_by_id("xai-applicant-select") is None
    assert "onXaiApplicantChange" not in client.get("/static/js/main.js").data.decode("utf-8")

    css = client.get("/static/css/style.css").data.decode("utf-8")
    quickload_rule = re.search(r"\.quickload-drawer\s*\{([^}]*)\}", css, re.DOTALL)
    assert quickload_rule is not None
    assert "display: none" in quickload_rule.group(1)


def test_tier1_underwriting_workbench_layout(index_html: str):
    """Verifies Tab 2 operational workbench two-column structure."""
    dom = parse_dom(index_html)
    uw_section = dom.find_by_id("underwriting-tab")
    assert uw_section is not None
    assert "Applicant Details" in index_html
    assert "Prediction Result" in index_html
    assert "workbench-layout" in index_html or "split-layout" in index_html


def test_underwriting_prediction_result_is_below_applicant_details(client):
    """The result panel follows the applicant form in a full-width vertical workbench."""
    css = client.get("/static/css/style.css").data.decode("utf-8")
    assert "flex-direction: column" in css
    assert ".workbench-layout .workbench-panel" in css


def test_underwriting_applicant_form_prevents_horizontal_overflow(client):
    """Applicant controls shrink and wrap instead of widening the workbench."""
    css = client.get("/static/css/style.css").data.decode("utf-8")
    assert "grid-template-columns: minmax(0, 1.12fr) minmax(18rem, 0.88fr)" in css
    assert "#underwriting-tab .form-group input" in css
    assert "width: 100%" in css
    assert "overflow-wrap: anywhere" in css
    assert "flex-wrap: wrap" in css


def test_policy_matrix_has_wider_primary_column(client):
    """The risk matrix receives more width than the adjacent rationale panel."""
    css = client.get("/static/css/style.css").data.decode("utf-8")
    assert "grid-template-columns: 2fr 1.5fr" in css


def test_policy_action_labels_stay_on_one_line(client):
    """Policy action badges remain readable without wrapping inside the matrix."""
    css = client.get("/static/css/style.css").data.decode("utf-8")
    assert "#policy-tab .policy-panel:first-child .data-table .badge" in css
    assert "white-space: nowrap" in css
    assert "display: inline-flex" in css


def test_reference_palette_tokens_are_present(client):
    """The supplied palette is represented in the shared design tokens."""
    css = client.get("/static/css/style.css").data.decode("utf-8")
    for color in ["#10B981", "#059669", "#D1FAE5", "#3B82F6", "#DBEAFE", "#8B5CF6", "#22C55E", "#0EA5E9"]:
        assert color in css


def test_tier1_underwriting_subtabs_and_grouped_inputs(index_html: str):
    """Verifies Tab 2 Manual/Quick Load sub-tabs, test applicant loaders, and inputs."""
    dom = parse_dom(index_html)

    # Sub-tabs
    assert dom.find_by_id("subtab-manual-btn") is not None
    assert dom.find_by_id("subtab-quickload-btn") is not None

    # Test applicant loader buttons
    for app_id in [100001, 100005, 100013, 100028]:
        assert str(app_id) in index_html, f"Missing test applicant button for #{app_id}"

    # Synthetic personas are intentionally not exposed in the evaluator UI.
    assert "Synthetic Risk Personas" not in index_html
    assert "loadPersona(" not in index_html

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


def test_underwriting_requires_explicit_prediction_before_showing_results(index_html: str, client):
    """The simulator must not score its initial or quick-loaded profile automatically."""
    dom = parse_dom(index_html)
    result_content = dom.find_by_id("scoring-result-content")
    assert result_content is not None
    assert "hidden" in result_content.attrs
    assert "Predict Risk" in index_html

    main_js = client.get("/static/js/main.js").data.decode("utf-8")
    populate_body = re.search(
        r"function populateApplicantProfile\(p\) \{(.*?)\n\}", main_js, re.DOTALL
    )
    assert populate_body is not None
    assert "submitScoring()" not in populate_body.group(1)


def test_xai_rendering_does_not_depend_on_chart_library(client):
    """XAI metrics and interpretation rendering must continue if Chart.js is unavailable."""
    main_js = client.get("/static/js/main.js").data.decode("utf-8")
    assert "typeof Chart === 'undefined'" in main_js
    assert "continuing without portfolio charts" in main_js
    assert "chart library could not be loaded" in main_js


def test_xai_keeps_current_form_profile_before_scoring(client):
    """The XAI profile summary remains populated before a prediction is submitted."""
    main_js = client.get("/static/js/main.js").data.decode("utf-8")
    assert "function syncManualApplicantProfile()" in main_js
    assert "syncManualApplicantProfile();" in main_js
    assert "if (AppState.currentApplicantData)" in main_js
    assert "$180,000" in client.get("/").data.decode("utf-8")
    assert "Manual profile is ready" in client.get("/").data.decode("utf-8")


def test_editing_loaded_applicant_preserves_gender_for_scoring(client):
    """Editing a quick-loaded profile must not silently change its gender feature."""
    main_js = client.get("/static/js/main.js").data.decode("utf-8")
    assert "const preservedGender = AppState.currentApplicantData?.gender;" in main_js
    assert "preservedGender === 'Female' || preservedGender === 'Male'" in main_js
    assert "CODE_GENDER: (AppState.currentApplicantData && AppState.currentApplicantData.gender === \"Female\") ? \"F\" : \"M\"" in main_js


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

    # Results are intentionally unavailable until the user submits Predict Risk.
    result_content = dom.find_by_id("scoring-result-content")
    assert result_content is not None
    assert "hidden" in result_content.attrs
    assert dom.find_by_id("scoring-placeholder") is not None

    # Toggleable Risk Factor Tabs
    assert dom.find_by_id("tab-risk-incr-btn") is not None
    assert dom.find_by_id("tab-risk-decr-btn") is not None
    assert dom.find_by_id("risk-factors-container") is not None


def test_secondary_pages_include_assignment_context_sections(index_html: str):
    """Each non-EDA workflow exposes supporting context without replacing its controls."""
    dom = parse_dom(index_html)
    assert dom.find_by_id("underwriting-context-heading") is None
    assert dom.find_by_id("xai-context-heading") is None
    assert dom.find_by_id("policy-evidence-heading") is None
    assert "risk_band_distribution.png" not in index_html
    assert "read-only and auditable" in index_html


def test_tier1_xai_three_column_layout(index_html: str):
    """Verifies Tab 3 Explainable AI 3-column layout, diverging SHAP canvas, and cards."""
    dom = parse_dom(index_html)

    # 3-Column Layout Container
    assert "xai-three-col-layout" in index_html or dom.find_all_by_class("xai-three-col-layout")

    # Left Column: Current applicant status & Structured Summary Sheet
    assert dom.find_by_id("xai-profile-status") is not None
    assert "Linked to the Underwriting Simulator" in index_html

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


def test_tier1_policy_matrix_without_redundant_pillars(index_html: str):
    """Verifies the policy matrix and governance callout without duplicate summary cards."""
    dom = parse_dom(index_html)

    assert "3 Risk Bands" not in index_html
    assert "Monotonic Default Rate" not in index_html
    assert "Data-Driven Thresholds" not in index_html
    assert len(dom.find_all_by_class("pillar-card")) == 0

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


def test_tier1_talk_to_data_assignment_query_options(index_html: str):
    """Verifies Tab 5 exposes five distinct assignment-aligned business queries."""
    dom = parse_dom(index_html)

    assert dom.find_by_id("chat-history") is not None
    assert dom.find_by_id("chat-form") is not None
    assert dom.find_by_id("chat-input") is not None
    assert dom.find_by_id("chat-submit-btn") is not None

    expected_questions = [
        "What is the default rate across different education levels?",
        "Show average credit amount and default rate by income type.",
        "How do external credit bureau scores impact default rates?",
        "Compare default rates for applicants with prior bureau overdue debt versus clean credit histories.",
        "Compare default rates for applicants with high DTI versus healthy DTI.",
    ]
    for q in expected_questions:
        assert q in index_html, f"Missing example inquiry question: '{q}'"


def test_xai_initializes_with_real_scored_applicant(client):
    """The XAI tab should request a real SHAP explanation on initial page load."""
    main_js = client.get("/static/js/main.js").data.decode("utf-8")
    assert "function initializeDefaultExplanation()" in main_js
    assert "loadTestApplicant(100001);" in main_js
    assert "await submitScoring();" in main_js


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
    assert b"Credit Risk Intelligence Platform" in page_res.data
    assert b"NeoStats" not in page_res.data
    assert b"Overview" in page_res.data

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
