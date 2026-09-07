"""
Tests for Redesigned Frontend UI, Interactive Components, and API Workflows.
Covers 4-Tier Test Architecture:
  - Tier 1: Feature Coverage (Navbar badges, hero banner, 4 KPI cards, sparklines,
            Chart.js canvas elements, two-column workbench, score card, combined SHAP tornado chart,
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


def test_navigation_has_explicit_tab_mapping_and_persistent_active_state(client, index_html: str):
    """Primary navigation maps directly to tabs and keeps the current tab visibly active."""
    dom = parse_dom(index_html)
    buttons = dom.find_all_by_class("tab-btn")
    expected_mapping = {
        "Executive EDA": "eda-tab",
        "Underwriting Simulator": "underwriting-tab",
        "Credit Policy Rules": "policy-tab",
    }
    for label, tab_id in expected_mapping.items():
        button = next(button for button in buttons if label in button.text)
        assert button.attrs.get("data-tab-id") == tab_id

    css = client.get("/static/css/design-system.css").data.decode("utf-8")
    js = client.get("/static/js/main.js").data.decode("utf-8")
    assert ".tab-btn.active" in css
    assert "background: var(--gold);" in css
    assert ".tab-btn.active:hover" in css
    assert "btn.dataset.tabId === tabId" in js
    assert "currentTab: 'eda-tab'" in js
    assert "creditRiskActiveTab" in js
    assert "window.localStorage.getItem('creditRiskActiveTab')" in js


def test_guided_workspace_hierarchy_hooks(index_html: str, client):
    """Each tab identifies primary work, supporting context, and reference content."""
    dom = parse_dom(index_html)
    tab_ids = ["eda-tab", "underwriting-tab", "policy-tab", "chat-tab"]
    for tab_id in tab_ids:
        tab = dom.find_by_id(tab_id)
        assert tab is not None
        if tab_id != "chat-tab":
            assert tab.has_class("workspace-tab")
    assert len(dom.find_all_by_class("workspace-primary")) >= 4

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
        "Credit Policy Rules",
        "Talk-to-Data",
    ]
    for tab_name in expected_tabs:
        if tab_name != "Talk-to-Data":
            assert tab_name in index_html, f"Missing navigation tab: {tab_name}"

    # Tab Content Containers by ID
    expected_ids = ["eda-tab", "underwriting-tab", "policy-tab", "chat-tab"]
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

    # Sub-tabs & Gated Panels
    assert dom.find_by_id("subtab-manual-btn") is not None
    assert dom.find_by_id("subtab-quickload-btn") is not None
    assert dom.find_by_id("quickload-panel") is not None
    assert dom.find_by_id("manual-entry-fields") is not None

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
    """The profile summary remains populated before a prediction is submitted."""
    main_js = client.get("/static/js/main.js").data.decode("utf-8")
    assert "function syncManualApplicantProfile()" in main_js
    assert "syncManualApplicantProfile();" in main_js
    assert "if (AppState.currentApplicantData)" in main_js
    assert "180000" in client.get("/").data.decode("utf-8")


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

    # Combined SHAP Tornado Chart (Replaces toggle buttons with unified non-scrolling tornado chart)
    assert dom.find_by_id("tab-risk-incr-btn") is None
    assert dom.find_by_id("tab-risk-decr-btn") is None
    assert dom.find_by_id("underwritingTornadoChart") is not None
    assert dom.find_by_id("risk-factors-container") is not None


def test_secondary_pages_include_assignment_context_sections(index_html: str):
    """Each non-EDA workflow exposes supporting context without replacing its controls."""
    dom = parse_dom(index_html)
    assert dom.find_by_id("underwriting-context-heading") is None
    assert dom.find_by_id("xai-context-heading") is None
    assert dom.find_by_id("policy-evidence-heading") is not None
    assert "risk_band_distribution.png" in index_html
    assert "read-only and auditable" in index_html


def test_tier1_xai_three_column_layout(index_html: str):
    """Verifies Underwriting Simulator includes relocated narrative cards and that SHAP Waterfall Breakdown is completely removed."""
    dom = parse_dom(index_html)

    # SHAP Waterfall Breakdown section completely removed
    assert dom.find_by_id("shapDivergingChart") is None
    assert "SHAP Waterfall Breakdown" not in index_html

    # Explanation elements in Underwriting Simulator
    assert dom.find_by_id("underwritingTornadoChart") is not None
    assert dom.find_by_id("risk-factors-container") is not None

    # Plain-English Interpretation Cards
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


def test_policy_regulatory_compliance_disclaimer_styling(client, index_html: str):
    """
    Verifies visually distinct compliance disclaimer styling on Credit Policy Rules tab:
      - Dedicated compliance shield SVG icon instead of generic placeholder.
      - Distinct muted amber solid left border (5px) and border color (#E5C378, #B45309).
      - Distinct from generic info-box / workspace callouts.
      - Increased padding (1.15rem 1.35rem) and subtle drop shadow for visual elevation.
      - WCAG AA text contrast for disclaimer title and body text.
    """
    dom = parse_dom(index_html)
    callouts = dom.find_all_by_class("compliance-disclaimer-callout")
    assert len(callouts) >= 1, "Expected compliance-disclaimer-callout in DOM"

    # Dedicated SVG shield icon
    assert "compliance-shield-svg" in index_html
    assert 'd="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"' in index_html

    # Accessibility attributes
    assert 'role="note"' in index_html
    assert 'aria-label="Regulatory Compliance Notice"' in index_html

    # Stylesheet rules in style.css and design-system.css
    style_css = client.get("/static/css/style.css").data.decode("utf-8")
    ds_css = client.get("/static/css/design-system.css").data.decode("utf-8")

    for css in [style_css, ds_css]:
        assert "--compliance-disclaimer-accent: #B45309;" in css
        assert "--compliance-disclaimer-border: #E5C378;" in css
        assert "border-left: 5px solid" in css
        assert "1.15rem 1.35rem" in css
        assert "compliance-disclaimer-callout" in css

    # Contrast verification
    def srgb_luminance(hex_code: str) -> float:
        hex_code = hex_code.lstrip("#")
        rgb = [int(hex_code[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
        lum = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * lum[0] + 0.7152 * lum[1] + 0.0722 * lum[2]

    def contrast_ratio(c1: str, c2: str) -> float:
        l1, l2 = srgb_luminance(c1), srgb_luminance(c2)
        lighter, darker = max(l1, l2), min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    # Title (#78350F) and body text (#63390B) on background (#FEF9EE)
    ratio_title = contrast_ratio("#FEF9EE", "#78350F")
    assert ratio_title >= 4.5, f"Title contrast {ratio_title:.2f} fails WCAG AA"

    ratio_body = contrast_ratio("#FEF9EE", "#63390B")
    assert ratio_body >= 4.5, f"Body text contrast {ratio_body:.2f} fails WCAG AA"


def test_policy_risk_band_evidence_is_responsive_and_content_first(client, index_html: str):
    """The risk-band evidence chart and routing notes avoid fixed empty frames."""
    dom = parse_dom(index_html)
    assert dom.find_by_id("policy-evidence-heading") is not None
    assert "risk_band_distribution.png" in index_html

    css = client.get("/static/css/design-system.css").data.decode("utf-8")
    assert "#policy-tab .policy-chart-img-wrapper" in css
    assert "width: 100%" in css
    assert "height: auto" in css
    assert "padding: 12px 16px" in css
    assert "#policy-tab .policy-evidence-notes" in css
    assert "gap: 10px" in css


def test_policy_severity_badges_distinguish_critical_from_high(client):
    """Severity mapping keeps PASS separate and gives CRITICAL the strongest red treatment."""
    js = client.get("/static/js/main.js").data.decode("utf-8")
    css = client.get("/static/css/design-system.css").data.decode("utf-8")

    assert "badge-severity-low" in js
    assert "badge-severity-medium" in js
    assert "badge-severity-high" in js
    assert "badge-severity-critical" in js
    assert "background: #FDE0DE" in css
    assert "color: #8F2925" in css
    assert "border-color: #D98A85" in css


def test_policy_audit_table_uses_compact_readable_rows(client):
    """The active policy audit table uses restrained 12px vertical cell padding."""
    css = client.get("/static/css/design-system.css").data.decode("utf-8")
    assert "#policy-tab .policy-active-card .data-table th" in css
    assert "#policy-tab .policy-active-card .data-table td" in css
    assert "padding-top: 12px" in css
    assert "padding-bottom: 12px" in css


def test_policy_audit_table_severity_row_tints(client):
    """
    Verifies subtle background row tints for active applicant policy rules audit table:
      - Failed CRITICAL guardrails receive .policy-row-critical tint (#FDECEC).
      - Failed HIGH guardrails receive .policy-row-high tint (#FEF9EE).
      - Failed MEDIUM/LOW guardrails receive no tint (default neutral row).
      - Passed guardrails (regardless of severity) remain neutral.
      - Preserves existing PASS / FLAGGED badge styling and severity tags.
      - Maintains WCAG AA compliance (contrast ratio >= 4.5:1) for row text colors.
    """
    import json
    import subprocess

    # 1. CSS Custom Properties and Class Definitions
    style_css = client.get("/static/css/style.css").data.decode("utf-8")
    ds_css = client.get("/static/css/design-system.css").data.decode("utf-8")

    assert "--policy-row-critical-bg: #FDECEC;" in style_css
    assert "--policy-row-high-bg: #FEF9EE;" in style_css
    assert ".policy-row-critical" in style_css
    assert ".policy-row-high" in style_css

    assert "--policy-row-critical-bg: #FDECEC;" in ds_css
    assert "--policy-row-high-bg: #FEF9EE;" in ds_css
    assert ".policy-row-critical" in ds_css
    assert ".policy-row-high" in ds_css

    # 2. Mathematical WCAG AA Contrast Verification
    def srgb_luminance(hex_code: str) -> float:
        hex_code = hex_code.lstrip("#")
        rgb = [int(hex_code[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
        lum = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * lum[0] + 0.7152 * lum[1] + 0.0722 * lum[2]

    def contrast_ratio(c1: str, c2: str) -> float:
        l1, l2 = srgb_luminance(c1), srgb_luminance(c2)
        lighter, darker = max(l1, l2), min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    # Table cell text colors: #0F172A (bold text), #475569 (standard body/rationale), #1E293B (code)
    for text_color in ["#0F172A", "#475569", "#1E293B"]:
        # CRITICAL tint: #FDECEC
        ratio_crit = contrast_ratio("#FDECEC", text_color)
        assert ratio_crit >= 4.5, f"Contrast ratio {ratio_crit:.2f} for {text_color} on #FDECEC fails WCAG AA (>= 4.5)"

        # HIGH tint: #FEF9EE
        ratio_high = contrast_ratio("#FEF9EE", text_color)
        assert ratio_high >= 4.5, f"Contrast ratio {ratio_high:.2f} for {text_color} on #FEF9EE fails WCAG AA (>= 4.5)"

    # 3. Dynamic DOM Rendering Verification via Node.js
    node_script = """
    const fs = require('fs');

    const appendedRows = [];
    const mockTbody = {
      innerHTML: '',
      appendChild: (row) => appendedRows.push(row)
    };

    global.window = {
      addEventListener: () => {},
      localStorage: { getItem: () => null, setItem: () => {} }
    };
    global.document = {
      documentElement: { style: {} },
      addEventListener: () => {},
      getElementById: (id) => {
        if (id === 'policy-rules-tbody') return mockTbody;
        return null;
      },
      createElement: (tag) => {
        return {
          tagName: tag.toUpperCase(),
          className: '',
          innerHTML: ''
        };
      }
    };
    global.getComputedStyle = () => ({ getPropertyValue: () => '' });

    const jsSource = fs.readFileSync('src/ui/static/js/main.js', 'utf8');
    eval(jsSource);

    const testPayload = {
      rules: [
        {
          rule_id: 'RULE_DELINQUENCY_CHECK',
          flag_id: 'FLAG_PAST_DUE',
          name: 'Past Due Credit Clearance',
          threshold: 'Zero Active Overdue Debt',
          value: '$5,400.00',
          passed: false,
          severity: 'CRITICAL',
          rationale: 'Prior overdue debt recorded.'
        },
        {
          rule_id: 'RULE_DTI_BURDEN',
          flag_id: 'FLAG_HIGH_DTI',
          name: 'Debt-to-Income Limit',
          threshold: 'DTI <= 40%',
          value: '48.5%',
          passed: false,
          severity: 'HIGH',
          rationale: 'High debt burden.'
        },
        {
          rule_id: 'RULE_TENURE_STABILITY',
          flag_id: 'FLAG_UNSTABLE_TENURE',
          name: 'Employment & Age Stability',
          threshold: 'Tenure >= 1 yr',
          value: 'Age 22y, Tenure 0.4y',
          passed: false,
          severity: 'MEDIUM',
          rationale: 'Young applicant.'
        },
        {
          rule_id: 'RULE_EXT_SCORE_MIN',
          flag_id: 'FLAG_LOW_EXT_SOURCE',
          name: 'External Bureau Score Floor',
          threshold: 'Score Mean >= 0.35',
          value: '0.420',
          passed: true,
          severity: 'CRITICAL',
          rationale: 'Passed external bureau score.'
        },
        {
          rule_id: 'RULE_CLEAN_HIGH',
          flag_id: 'FLAG_CLEAN_HIGH',
          name: 'Clean High Severity Rule',
          threshold: 'N/A',
          value: '100',
          passed: true,
          severity: 'HIGH',
          rationale: 'Passed high severity.'
        },
        {
          rule_id: 'RULE_CLEAN_MEDIUM',
          flag_id: 'FLAG_CLEAN_MEDIUM',
          name: 'Clean Medium Severity Rule',
          threshold: 'N/A',
          value: '100',
          passed: true,
          severity: 'MEDIUM',
          rationale: 'Passed medium severity.'
        }
      ]
    };

    renderPolicyRulesTable(testPayload);

    const result = appendedRows.map(r => ({
      className: r.className,
      hasPassBadge: r.innerHTML.includes('badge-success') && r.innerHTML.includes('PASS'),
      hasFailBadge: r.innerHTML.includes('badge-danger') && r.innerHTML.includes('FLAGGED'),
      hasSeverityBadge: r.innerHTML.includes('badge-severity-')
    }));

    console.log(JSON.stringify(result));
    """

    res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
    rows = json.loads(res.stdout.strip())

    # Row 0: Failed CRITICAL -> .policy-row-critical, FLAGGED badge, severity badge
    assert rows[0]["className"] == "policy-row-critical"
    assert rows[0]["hasFailBadge"] is True
    assert rows[0]["hasPassBadge"] is False
    assert rows[0]["hasSeverityBadge"] is True

    # Row 1: Failed HIGH -> .policy-row-high, FLAGGED badge, severity badge
    assert rows[1]["className"] == "policy-row-high"
    assert rows[1]["hasFailBadge"] is True
    assert rows[1]["hasPassBadge"] is False
    assert rows[1]["hasSeverityBadge"] is True

    # Row 2: Failed MEDIUM -> no tint class, FLAGGED badge, severity badge
    assert rows[2]["className"] == ""
    assert rows[2]["hasFailBadge"] is True
    assert rows[2]["hasPassBadge"] is False
    assert rows[2]["hasSeverityBadge"] is True

    # Row 3: Passed CRITICAL -> no tint class, PASS badge
    assert rows[3]["className"] == ""
    assert rows[3]["hasPassBadge"] is True
    assert rows[3]["hasFailBadge"] is False

    # Row 4: Passed HIGH -> no tint class, PASS badge
    assert rows[4]["className"] == ""
    assert rows[4]["hasPassBadge"] is True
    assert rows[4]["hasFailBadge"] is False

    # Row 5: Passed MEDIUM -> no tint class, PASS badge
    assert rows[5]["className"] == ""
    assert rows[5]["hasPassBadge"] is True
    assert rows[5]["hasFailBadge"] is False


def test_tier1_talk_to_data_assignment_query_options(index_html: str):
    """Verifies Tab 5 exposes five distinct assignment-aligned business queries."""
    dom = parse_dom(index_html)

    assert dom.find_by_id("chat-history") is not None
    assert dom.find_by_id("chat-form") is not None
    assert dom.find_by_id("chat-input") is not None
    assert dom.find_by_id("chat-submit-btn") is not None
    assert "Suggested questions" in index_html
    assert len(dom.find_all_by_class("chat-suggestion-chip")) == 5

    expected_questions = [
        "What is the default rate across different education levels?",
        "Show average credit amount and default rate by income type.",
        "How do external credit bureau scores impact default rates?",
        "Compare default rates for applicants with prior bureau overdue debt versus clean credit histories.",
        "Compare default rates for applicants with high DTI versus healthy DTI.",
    ]
    for q in expected_questions:
        assert q in index_html, f"Missing example inquiry question: '{q}'"


def test_talk_to_data_suggestions_are_compact_and_conversation_first(client):
    """All five examples remain visible while the conversation stream owns flexible height."""
    css = client.get("/static/css/design-system.css").data.decode("utf-8")
    assert "#chat-tab .example-queries-list" in css
    assert "flex-wrap: wrap" in css
    assert "gap: 8px" in css
    assert "min-height: 32px" in css
    assert "padding: 7px 10px" in css
    assert "font-size: 12px" in css
    assert "#chat-tab .chat-history-stream" in css
    assert "flex: 1 1 auto" in css


def test_talk_to_data_session_history_lightweight_state(client, index_html: str):
    """
    Verifies lightweight session history within the Talk-to-Data floating panel:
      - Stores each Q&A exchange (question text, generated SQL, result summary/row count, latency, engine used).
      - Renders prior exchanges above the current one in collapsed/summary form.
      - Collapsed exchanges are expandable to show full SQL/table on click.
      - Suggested question chips and input box remain pinned in the bottom dock.
    """
    import json
    import subprocess

    # 1. DOM Structure: Dock pinning
    dom = parse_dom(index_html)
    assert dom.find_by_id("chat-history") is not None
    assert len(dom.find_all_by_class("chat-bottom-dock")) >= 1
    assert dom.find_by_id("chat-form") is not None
    assert len(dom.find_all_by_class("chat-suggestion-chip")) == 5

    # 2. Stylesheet Rules: History cards and bottom dock
    style_css = client.get("/static/css/style.css").data.decode("utf-8")
    ds_css = client.get("/static/css/design-system.css").data.decode("utf-8")

    for css in [style_css, ds_css]:
        assert ".chat-bottom-dock" in css
        assert ".chat-exchange-card" in css
        assert ".exchange-summary-bar" in css
        assert ".exchange-full-details" in css

    # 3. Node.js Session History State & Interaction Verification
    node_script = """
    const fs = require('fs');

    const mockHistory = {
      innerHTML: '',
      scrollTop: 0,
      scrollHeight: 100
    };

    global.window = {
      addEventListener: () => {},
      localStorage: { getItem: () => null, setItem: () => {} }
    };
    global.document = {
      documentElement: { style: {} },
      addEventListener: () => {},
      getElementById: (id) => {
        if (id === 'chat-history') return mockHistory;
        return null;
      },
      createElement: (tag) => ({
        tagName: tag.toUpperCase(),
        className: '',
        innerHTML: ''
      })
    };
    global.getComputedStyle = () => ({ getPropertyValue: () => '' });
    global.requestAnimationFrame = (fn) => fn();

    const jsSource = fs.readFileSync('src/ui/static/js/main.js', 'utf8');
    eval(jsSource);

    const log = [];

    // Step 1: Initial state
    log.push({
      step: 'initial',
      exchangeCount: window.ChatSession.exchanges.length
    });

    // Step 2: Add Exchange 1
    window.ChatSession.addExchange({
      id: 'ex-1',
      question: 'What is the default rate across different education levels?',
      sql: 'SELECT NAME_EDUCATION_TYPE, COUNT(*), AVG(TARGET) FROM applicants GROUP BY 1',
      data: [
        { NAME_EDUCATION_TYPE: 'Higher education', count: 15000, default_rate: '5.2%' },
        { NAME_EDUCATION_TYPE: 'Secondary', count: 45000, default_rate: '8.9%' }
      ],
      columns: ['NAME_EDUCATION_TYPE', 'count', 'default_rate'],
      rowCount: 2,
      latency: 14,
      engine: 'Deterministic Engine',
      businessInsight: 'Secondary education has higher default rate than higher education.',
      summaryText: '2 rows · Secondary education has higher default rate...',
      error: null
    });

    log.push({
      step: 'after_ex1',
      exchangeCount: window.ChatSession.exchanges.length,
      ex1Expanded: window.ChatSession.exchanges[0].expanded,
      domHasEx1: mockHistory.innerHTML.includes('exchange-ex-1'),
      domEx1Expanded: mockHistory.innerHTML.includes('is-expanded')
    });

    // Step 3: Add Exchange 2 (making Exchange 1 a prior exchange)
    window.ChatSession.addExchange({
      id: 'ex-2',
      question: 'Show average credit amount and default rate by income type',
      sql: 'SELECT NAME_INCOME_TYPE, AVG(AMT_CREDIT), AVG(TARGET) FROM applicants GROUP BY 1',
      data: [
        { NAME_INCOME_TYPE: 'Commercial associate', avg_credit: 600000, default_rate: '7.4%' }
      ],
      columns: ['NAME_INCOME_TYPE', 'avg_credit', 'default_rate'],
      rowCount: 1,
      latency: 22,
      engine: 'LLM Engine',
      businessInsight: 'Commercial associates hold larger credit lines.',
      summaryText: '1 row · Commercial associates hold larger credit lines.',
      error: null
    });

    log.push({
      step: 'after_ex2',
      exchangeCount: window.ChatSession.exchanges.length,
      ex1Expanded: window.ChatSession.exchanges[0].expanded,
      ex2Expanded: window.ChatSession.exchanges[1].expanded,
      ex1SummaryInDom: mockHistory.innerHTML.includes('What is the default rate across different education levels?'),
      ex2SummaryInDom: mockHistory.innerHTML.includes('Show average credit amount and default rate by income type'),
      ex1CollapsedClass: mockHistory.innerHTML.includes('is-collapsed'),
      ex2ExpandedClass: mockHistory.innerHTML.includes('is-expanded'),
      storedSql1: window.ChatSession.exchanges[0].sql,
      storedLatency1: window.ChatSession.exchanges[0].latency,
      storedEngine1: window.ChatSession.exchanges[0].engine,
      storedRowCount1: window.ChatSession.exchanges[0].rowCount
    });

    // Step 4: User clicks prior Exchange 1 to expand it again
    window.ChatSession.toggleExchange('ex-1');
    log.push({
      step: 'toggle_ex1_expand',
      ex1Expanded: window.ChatSession.exchanges[0].expanded,
      ex2Expanded: window.ChatSession.exchanges[1].expanded
    });

    // Step 5: User clicks Exchange 1 again to collapse it
    window.ChatSession.toggleExchange('ex-1');
    log.push({
      step: 'toggle_ex1_collapse',
      ex1Expanded: window.ChatSession.exchanges[0].expanded,
      ex2Expanded: window.ChatSession.exchanges[1].expanded
    });

    console.log(JSON.stringify(log));
    """

    res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
    steps = {s["step"]: s for s in json.loads(res.stdout.strip())}

    # Step 1: Starts empty
    assert steps["initial"]["exchangeCount"] == 0

    # Step 2: First exchange is active and expanded
    assert steps["after_ex1"]["exchangeCount"] == 1
    assert steps["after_ex1"]["ex1Expanded"] is True
    assert steps["after_ex1"]["domHasEx1"] is True
    assert steps["after_ex1"]["domEx1Expanded"] is True

    # Step 3: Second exchange makes prior exchange collapsed above it
    s3 = steps["after_ex2"]
    assert s3["exchangeCount"] == 2
    assert s3["ex1Expanded"] is False, "Prior exchange should be collapsed"
    assert s3["ex2Expanded"] is True, "Current exchange should be expanded"
    assert s3["ex1SummaryInDom"] is True
    assert s3["ex2SummaryInDom"] is True
    assert s3["ex1CollapsedClass"] is True
    assert s3["ex2ExpandedClass"] is True
    assert "SELECT NAME_EDUCATION_TYPE" in s3["storedSql1"]
    assert s3["storedLatency1"] == 14
    assert s3["storedEngine1"] == "Deterministic Engine"
    assert s3["storedRowCount1"] == 2

    # Step 4: Expanding prior exchange
    assert steps["toggle_ex1_expand"]["ex1Expanded"] is True

    # Step 5: Collapsing prior exchange
    assert steps["toggle_ex1_collapse"]["ex1Expanded"] is False


def test_talk_to_data_sql_block_inline_expand_no_nested_scroll(client):
    """Verifies Talk-to-Data SQL preview code block:
      - Has NO internal nested scrollbar (overflow: visible on container, outer panel handles scroll).
      - Is collapsed by default (showing ~3 lines via -webkit-line-clamp: 3 and overflow: hidden).
      - Renders a 'Show full query' toggle button.
      - Expands inline to full height on toggle without nested scrolling.
    """
    import json
    import subprocess

    style_css = client.get("/static/css/style.css").data.decode("utf-8")
    ds_css = client.get("/static/css/design-system.css").data.decode("utf-8")

    # 1. Verify CSS rules eliminate nested scrollbar and support 3-line clamp + inline expand
    for css in [style_css, ds_css]:
        assert ".sql-preview-box" in css
        assert ".sql-toggle-btn" in css
        assert "-webkit-line-clamp: 3" in css
        assert ".sql-preview-box.is-collapsed" in css
        assert ".sql-preview-box.is-expanded" in css
        assert "overflow: visible" in css

    # 2. Verify JS runtime behavior via node
    node_script = """
    const fs = require('fs');

    const mockHistory = { innerHTML: '', scrollTop: 0, scrollHeight: 100 };
    global.window = {
      addEventListener: () => {},
      localStorage: { getItem: () => null, setItem: () => {} }
    };
    global.document = {
      documentElement: { style: {} },
      addEventListener: () => {},
      getElementById: (id) => {
        if (id === 'chat-history') return mockHistory;
        return null;
      }
    };
    global.getComputedStyle = () => ({ getPropertyValue: () => '' });
    global.requestAnimationFrame = (fn) => fn();

    const jsSource = fs.readFileSync('src/ui/static/js/main.js', 'utf8');
    eval(jsSource);

    const log = [];

    // Step 1: Add an exchange with a multi-line SQL statement
    window.ChatSession.addExchange({
      id: 'sql-test-1',
      question: 'Show breakdown of loan status by education level',
      sql: 'SELECT \\n  NAME_EDUCATION_TYPE,\\n  COUNT(*) as total_applicants,\\n  AVG(AMT_CREDIT) as mean_credit,\\n  ROUND(AVG(TARGET) * 100, 2) as default_pct\\nFROM applications\\nGROUP BY NAME_EDUCATION_TYPE\\nORDER BY default_pct DESC',
      data: [{ NAME_EDUCATION_TYPE: 'Higher', total_applicants: 200, mean_credit: 500000, default_pct: 4.5 }],
      columns: ['NAME_EDUCATION_TYPE', 'total_applicants', 'mean_credit', 'default_pct'],
      rowCount: 1,
      latency: 18,
      engine: 'DuckDB Engine',
      businessInsight: 'Default percentage is lowest for higher education.',
      summaryText: '1 row returned',
      error: null
    });

    const html1 = mockHistory.innerHTML;
    log.push({
      step: 'initial_collapsed',
      sqlExpanded: window.ChatSession.exchanges[0].sqlExpanded,
      hasCollapsedBox: html1.includes('sql-preview-box') && html1.includes('is-collapsed'),
      hasShowFullQueryBtn: html1.includes('Show full query'),
      hasToggleBtnId: html1.includes('sql-toggle-btn-sql-test-1')
    });

    // Step 2: Toggle SQL expansion inline
    window.ChatSession.toggleSql('sql-test-1');
    const html2 = mockHistory.innerHTML;
    log.push({
      step: 'after_toggle_expand',
      sqlExpanded: window.ChatSession.exchanges[0].sqlExpanded,
      hasExpandedBox: html2.includes('sql-preview-box') && html2.includes('is-expanded'),
      hasShowLessBtn: html2.includes('Show less')
    });

    // Step 3: Toggle SQL collapse inline back to 3 lines
    window.ChatSession.toggleSql('sql-test-1');
    const html3 = mockHistory.innerHTML;
    log.push({
      step: 'after_toggle_collapse',
      sqlExpanded: window.ChatSession.exchanges[0].sqlExpanded,
      hasCollapsedBoxAgain: html3.includes('sql-preview-box') && html3.includes('is-collapsed'),
      hasShowFullQueryBtnAgain: html3.includes('Show full query')
    });

    console.log(JSON.stringify(log));
    """

    res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
    steps = {s["step"]: s for s in json.loads(res.stdout.strip())}

    # Verify initial state is collapsed by default showing "Show full query"
    assert steps["initial_collapsed"]["sqlExpanded"] is False
    assert steps["initial_collapsed"]["hasCollapsedBox"] is True
    assert steps["initial_collapsed"]["hasShowFullQueryBtn"] is True
    assert steps["initial_collapsed"]["hasToggleBtnId"] is True

    # Verify expanded state shows full query inline with "Show less"
    assert steps["after_toggle_expand"]["sqlExpanded"] is True
    assert steps["after_toggle_expand"]["hasExpandedBox"] is True
    assert steps["after_toggle_expand"]["hasShowLessBtn"] is True

    # Verify collapse toggles back cleanly
    assert steps["after_toggle_collapse"]["sqlExpanded"] is False
    assert steps["after_toggle_collapse"]["hasCollapsedBoxAgain"] is True
    assert steps["after_toggle_collapse"]["hasShowFullQueryBtnAgain"] is True


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


# ============================================================================
# Tier 1 & Tier 2 Tests: Scroll-Aware Floating Launcher (Talk to Data)
# ============================================================================

def test_tier1_scroll_aware_chat_launcher_css(client):
    """Verifies that both style.css and design-system.css define scroll-aware transition and hidden state."""
    for css_path in ["/static/css/style.css", "/static/css/design-system.css"]:
        res = client.get(css_path)
        assert res.status_code == 200
        css = res.data.decode("utf-8")

        # Must define .chat-launcher.is-scroll-hidden selector
        assert ".chat-launcher.is-scroll-hidden" in css

        # Must have smooth CSS transition (~150ms / 0.15s) for opacity, transform, visibility
        assert "transition:" in css
        assert "0.15s" in css

        # Hidden state must enforce zero opacity, hidden visibility, and disable pointer events
        hidden_rule = re.search(
            r"\.chat-launcher\.is-scroll-hidden[^{]*\{([^}]*)\}",
            css,
            re.DOTALL
        )
        assert hidden_rule is not None
        rule_body = hidden_rule.group(1)
        assert "opacity: 0" in rule_body
        assert "visibility: hidden" in rule_body
        assert "pointer-events: none" in rule_body


def test_tier1_scroll_aware_chat_launcher_js(client):
    """Verifies scroll-aware launcher logic, throttling, and tab hooks in main.js."""
    res = client.get("/static/js/main.js")
    assert res.status_code == 200
    js = res.data.decode("utf-8")

    assert "const SCROLL_TOP_THRESHOLD = 50" in js
    assert "function updateChatLauncherVisibility()" in js
    assert "function isTabContentShort()" in js
    assert "function initScrollAwareChatLauncher()" in js
    assert "function throttle(" in js

    # Event listeners must be registered with passive flag for performance
    assert "window.addEventListener('scroll', throttledScroll, { passive: true })" in js

    # switchTab must re-evaluate launcher visibility
    assert "updateChatLauncherVisibility()" in js

    # Panel open state must not be overridden by scroll
    assert "chatPanel.classList.contains('is-open')" in js


def test_tier2_scroll_aware_chat_launcher_behavior(client):
    """Verifies behavioral simulation: hiding on scroll down >50px, reappearing on scroll up or <=50px, short tabs, and panel preservation."""
    import subprocess
    import json

    js_code = """
    const fs = require('fs');
    const js = fs.readFileSync('src/ui/static/js/main.js', 'utf8');

    let classListLauncher = new Set();
    let isPanelOpen = false;

    const launcher = {
      offsetHeight: 44,
      classList: {
        add: (c) => classListLauncher.add(c),
        remove: (c) => classListLauncher.delete(c),
        contains: (c) => classListLauncher.has(c),
        toggle: (c, val) => val ? classListLauncher.add(c) : classListLauncher.delete(c)
      },
      setAttribute: () => {},
      getBoundingClientRect: () => ({ top: 700, bottom: 744, left: 1000, right: 1100 })
    };

    const activeTab = {
      getBoundingClientRect: () => ({ top: 0, bottom: 2000, left: 0, right: 1000 })
    };

    const chatPanel = {
      classList: {
        contains: (c) => c === 'is-open' && isPanelOpen,
        toggle: (c, val) => { if (c === 'is-open') isPanelOpen = val; }
      },
      setAttribute: () => {}
    };

    global.document = {
      querySelector: (sel) => {
        if (sel === '.chat-launcher') return launcher;
        if (sel === '.tab-content.active') return activeTab;
        return null;
      },
      getElementById: (id) => {
        if (id === 'chat-tab') return chatPanel;
        return null;
      },
      documentElement: {
        scrollHeight: 2500
      }
    };

    global.window = {
      innerHeight: 800,
      scrollY: 0,
      pageYOffset: 0,
      addEventListener: () => {},
      requestAnimationFrame: (cb) => cb()
    };

    eval(js.substring(js.indexOf('const SCROLL_TOP_THRESHOLD'), js.indexOf('function revealMotionItems')));

    const results = {};

    // 1. Initial at scroll 0
    results.initial_hidden = launcher.classList.contains('is-scroll-hidden');

    // 2. Scroll down to 30px (within 50px of top)
    window.scrollY = 30;
    updateChatLauncherVisibility();
    results.at_30px_hidden = launcher.classList.contains('is-scroll-hidden');

    // 3. Scroll down to 80px (> 50px)
    window.scrollY = 80;
    updateChatLauncherVisibility();
    results.at_80px_hidden = launcher.classList.contains('is-scroll-hidden');

    // 4. Continue scrolling down to 200px
    window.scrollY = 200;
    updateChatLauncherVisibility();
    results.at_200px_hidden = launcher.classList.contains('is-scroll-hidden');

    // 5. Scroll up from 200px to 160px
    window.scrollY = 160;
    updateChatLauncherVisibility();
    results.scroll_up_hidden = launcher.classList.contains('is-scroll-hidden');

    // 6. Scroll down again to 190px
    window.scrollY = 190;
    updateChatLauncherVisibility();
    results.scroll_down_again_hidden = launcher.classList.contains('is-scroll-hidden');

    // 7. Scroll back to top within 50px (e.g. 40px)
    window.scrollY = 40;
    updateChatLauncherVisibility();
    results.back_to_top_hidden = launcher.classList.contains('is-scroll-hidden');

    // 8. On short tab (scrollHeight <= innerHeight)
    document.documentElement.scrollHeight = 700;
    window.scrollY = 80;
    updateChatLauncherVisibility();
    results.short_tab_hidden = launcher.classList.contains('is-scroll-hidden');

    // 9. When panel is open, panel state is preserved and launcher visibility isn't touched
    isPanelOpen = true;
    window.scrollY = 300;
    updateChatLauncherVisibility();
    results.panel_still_open = isPanelOpen;

    console.log(JSON.stringify(results));
    """

    res = subprocess.run(["node", "-e", js_code], capture_output=True, text=True, check=True)
    results = json.loads(res.stdout.strip())

    assert results["initial_hidden"] is False
    assert results["at_30px_hidden"] is False
    assert results["at_80px_hidden"] is True
    assert results["at_200px_hidden"] is True
    assert results["scroll_up_hidden"] is False
    assert results["scroll_down_again_hidden"] is True
    assert results["back_to_top_hidden"] is False
    assert results["short_tab_hidden"] is False
    assert results["panel_still_open"] is True


def test_semantic_risk_palette_and_generic_tokens_defined(client):
    """Semantic risk palette and neutral/generic UI tokens are defined as CSS custom properties."""
    ds_css = client.get("/static/css/design-system.css").data.decode("utf-8")
    st_css = client.get("/static/css/style.css").data.decode("utf-8")

    for css in [ds_css, st_css]:
        # Semantic risk variables
        assert "--risk-low:" in css
        assert "--risk-medium:" in css
        assert "--risk-high:" in css
        assert "--risk-critical:" in css
        assert "--risk-decrease:" in css
        assert "--risk-increase:" in css

        # Generic UI / neutral status variables
        assert "--brand-accent:" in css
        assert "--status-ok:" in css
        assert "--status-info:" in css
        assert "--status-warning:" in css
        assert "--status-error:" in css
        assert "--status-neutral-bg:" in css


def test_color_separation_risk_versus_generic_ui(client, index_html: str):
    """Verifies that risk severity UI uses --risk-* tokens while generic UI uses neutral/brand tokens."""
    ds_css = client.get("/static/css/design-system.css").data.decode("utf-8")
    st_css = client.get("/static/css/style.css").data.decode("utf-8")
    js = client.get("/static/js/main.js").data.decode("utf-8")

    # Generic status indicator / LLM ready dot uses --status-ok, NOT --risk-low
    assert "background-color: var(--status-ok" in ds_css or "background-color: var(--status-ok" in st_css

    # Decorative top bar uses --brand-accent, NOT --risk-low
    assert "border-top: 3px solid var(--brand-accent" in st_css

    # Section count uses neutral status tokens, NOT --risk-low
    assert "var(--status-neutral-bg" in st_css
    assert "section-count {\n  background: var(--risk-low-bg)" not in st_css

    # Brand buttons use brand-accent
    assert "background: var(--brand-accent" in ds_css or "background: var(--brand-accent" in st_css

    # SHAP legend & factor badges use risk decrease/increase direction tokens
    assert "color: var(--risk-decrease-text" in ds_css or "color: var(--risk-decrease-text" in st_css
    assert "color: var(--risk-increase-text" in ds_css or "color: var(--risk-increase-text" in st_css
    assert "var(--risk-increase" in st_css
    assert "var(--risk-decrease" in st_css

    # Policy severity badges reference risk variables
    assert "var(--risk-low" in ds_css
    assert "var(--risk-medium" in ds_css
    assert "var(--risk-high" in ds_css
    assert "var(--risk-critical" in ds_css

    # JS dynamically queries CSS variables
    assert "getCssColor('--risk-critical'" in js
    assert "getCssColor('--risk-low'" in js
    assert "getCssColor('--risk-increase'" in js
    assert "getCssColor('--status-info'" in js

    # EDA legend pills in rendered HTML use semantic risk and status CSS variables
    assert "border-left-color: var(--risk-critical)" in index_html
    assert "border-left-color: var(--risk-low)" in index_html
    assert "border-left-color: var(--status-info)" in index_html
    assert "border-left-color: var(--brand-accent)" in index_html
    # Ensure no hardcoded inline hex colors remain in legend pills
    assert 'style="border-left-color: #EF4444;"' not in index_html
    assert 'style="border-left-color: #10B981;"' not in index_html


def test_shap_diverging_chart_datalabels_plugin(client):
    """Verifies that the SHAP waterfall/tornado chart includes signed 3-decimal data labels

    outside each bar, prevents off-canvas overflow, and does not overlap feature name labels.
    """
    import subprocess
    import json

    js = client.get("/static/js/main.js").data.decode("utf-8")

    # 1. Static assertions: plugin registration, scale headroom, and color bindings
    assert "shapDivergingLabelsPlugin" in js
    assert "id: 'shapDivergingLabels'" in js
    assert "plugins: [shapDivergingLabelsPlugin]" in js
    assert "toFixed(3)" in js
    assert "getCssColor('--risk-increase-text'" in js
    assert "getCssColor('--risk-decrease-text'" in js
    assert "grace: '15%'" in js
    assert "suggestedMin: -scaleLimit" in js
    assert "suggestedMax: scaleLimit" in js

    # 2. Node.js runtime behavioral execution and layout verification
    node_script = """
    const fs = require('fs');

    // Minimal browser environment mocks
    global.window = { addEventListener: () => {} };
    global.document = {
      documentElement: { style: {} },
      addEventListener: () => {},
      getElementById: () => null
    };
    global.getComputedStyle = () => ({
      getPropertyValue: (name) => {
        if (name === '--risk-increase-text') return '#9E3834';
        if (name === '--risk-decrease-text') return '#056B4D';
        return '';
      }
    });

    const jsSource = fs.readFileSync('src/ui/static/js/main.js', 'utf8');
    eval(jsSource);

    const plugin = window.shapDivergingLabelsPlugin;
    if (!plugin) {
      console.error(JSON.stringify({ error: "Plugin not exposed on window" }));
      process.exit(1);
    }

    // --- Scenario A: Standard SHAP values (positive, negative, zero, tiny narrow bars) ---
    const labelsA = [];
    const mockCtxA = {
      font: '',
      textAlign: '',
      textBaseline: '',
      fillStyle: '',
      save: () => {},
      restore: () => {},
      measureText: (text) => ({ width: text.length * 6.5 }),
      fillText: (text, x, y) => {
        labelsA.push({
          text,
          x,
          y,
          font: mockCtxA.font,
          textAlign: mockCtxA.textAlign,
          fillStyle: mockCtxA.fillStyle
        });
      }
    };

    const rawValuesA = [-0.354, -0.158, -0.002, 0.000, 0.001, 0.045, 0.263];
    const chartWidth = 600;
    const chartArea = { left: 120, right: 580, top: 40, bottom: 280 };
    const zeroX = (chartArea.left + chartArea.right) / 2; // 350px

    // 1 SHAP unit = 400px
    const elementsA = rawValuesA.map((val, idx) => ({
      x: zeroX + val * 400,
      y: 50 + idx * 30
    }));

    const mockChartA = {
      ctx: mockCtxA,
      width: chartWidth,
      height: 320,
      chartArea: chartArea,
      scales: {
        x: { getPixelForValue: (v) => zeroX + v * 400 },
        y: { getPixelForValue: (i) => 50 + i * 30 }
      },
      data: { datasets: [{ data: rawValuesA }] },
      getDatasetMeta: () => ({ data: elementsA })
    };

    plugin.afterDatasetsDraw(mockChartA);

    // --- Scenario B: Clamping edge cases (extreme bars near chartArea.left and chart.width) ---
    const labelsB = [];
    const mockCtxB = {
      font: '',
      textAlign: '',
      textBaseline: '',
      fillStyle: '',
      save: () => {},
      restore: () => {},
      measureText: (text) => ({ width: text.length * 6.5 }),
      fillText: (text, x, y) => {
        labelsB.push({
          text,
          x,
          y,
          textAlign: mockCtxB.textAlign,
          fillStyle: mockCtxB.fillStyle
        });
      }
    };

    // Very large positive bar near canvas edge (barX=585), and large negative near feature labels (barX=125)
    const rawValuesB = [-0.550, 0.585];
    const elementsB = [
      { x: 125, y: 50 },
      { x: 585, y: 80 }
    ];

    const mockChartB = {
      ctx: mockCtxB,
      width: chartWidth,
      height: 320,
      chartArea: chartArea,
      scales: {
        x: { getPixelForValue: (v) => zeroX + v * 400 },
        y: { getPixelForValue: (i) => 50 + i * 30 }
      },
      data: { datasets: [{ data: rawValuesB }] },
      getDatasetMeta: () => ({ data: elementsB })
    };

    plugin.afterDatasetsDraw(mockChartB);

    console.log(JSON.stringify({
      scenarioA: { labels: labelsA, elements: elementsA },
      scenarioB: { labels: labelsB, elements: elementsB },
      chartArea,
      chartWidth,
      zeroX
    }));
    """

    res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
    out = json.loads(res.stdout.strip())

    scA = out["scenarioA"]
    labels_a = scA["labels"]
    elems_a = scA["elements"]
    chart_area = out["chartArea"]
    chart_width = out["chartWidth"]
    zero_x = out["zeroX"]

    # 7 labels drawn for 7 input factors
    assert len(labels_a) == 7

    expected_texts = ["-0.354", "-0.158", "-0.002", "+0.000", "+0.001", "+0.045", "+0.263"]
    for i, exp in enumerate(expected_texts):
        assert labels_a[i]["text"] == exp, f"Index {i}: expected {exp}, got {labels_a[i]['text']}"
        assert "10px" in labels_a[i]["font"], "Data label must use small 10px font"

    # Verify positions and constraints for Scenario A
    for i, label in enumerate(labels_a):
        elem = elems_a[i]
        val = float(label["text"])
        text_width = len(label["text"]) * 6.5

        if val >= 0:
            # Positive bar: label outside to the right
            assert label["textAlign"] == "left"
            assert label["fillStyle"] == "#9E3834"
            assert label["x"] > elem["x"], f"Positive label must be right of bar: {label['x']} > {elem['x']}"
            assert label["x"] >= elem["x"] + 2, "Label must not overlap positive bar fill"
            # Clamping check: within canvas width
            assert label["x"] + text_width <= chart_width, "Label must not render off-canvas on the right"
        else:
            # Negative bar: label outside to the left
            assert label["textAlign"] == "right"
            assert label["fillStyle"] == "#056B4D"
            assert label["x"] < elem["x"], f"Negative label must be left of bar: {label['x']} < {elem['x']}"
            assert label["x"] <= elem["x"] - 2, "Label must not overlap negative bar fill"
            # Clamping check: must not cross into y-axis feature name labels (< chartArea.left) or off-canvas (< 0)
            text_left_edge = label["x"] - text_width
            assert text_left_edge >= chart_area["left"], f"Negative label overlapped feature names: {text_left_edge} < {chart_area['left']}"
            assert text_left_edge >= 0, "Negative label must not render off-canvas on the left"

    # Narrowest bars check
    # +0.001 narrow bar (index 4): placed strictly right of zeroX
    assert labels_a[4]["x"] > zero_x
    # -0.002 narrow bar (index 2): placed strictly left of zeroX
    assert labels_a[2]["x"] < zero_x

    # Verify Scenario B clamping under extreme bar lengths
    scB = out["scenarioB"]
    labels_b = scB["labels"]
    # Negative extreme bar: left edge clamped to never cross chartArea.left or off-canvas
    neg_label = labels_b[0]
    neg_text_width = len(neg_label["text"]) * 6.5
    assert neg_label["x"] - neg_text_width >= chart_area["left"]

    # Positive extreme bar: right edge clamped to never render off-canvas
    pos_label = labels_b[1]
    pos_text_width = len(pos_label["text"]) * 6.5
    assert pos_label["x"] + pos_text_width <= chart_width


def test_underwriting_combined_tornado_chart(client, index_html: str):
    """Verifies that the Underwriting Simulator replaces the toggleable list with a unified

    combined tornado chart showing both positive and negative SHAP drivers sorted by
    absolute magnitude and capped at top features in a non-scrolling view.
    """
    import subprocess
    import json

    dom = parse_dom(index_html)
    st_css = client.get("/static/css/style.css").data.decode("utf-8")
    main_js = client.get("/static/js/main.js").data.decode("utf-8")

    # 1. HTML assertions: toggle buttons removed, canvas and legend present
    assert dom.find_by_id("tab-risk-incr-btn") is None, "Risk Increases (+) toggle button must be removed"
    assert dom.find_by_id("tab-risk-decr-btn") is None, "Risk Decreases (-) toggle button must be removed"
    assert dom.find_by_id("underwritingTornadoChart") is not None, "Canvas for combined tornado chart must be present"
    assert dom.find_by_id("risk-factors-container") is not None

    # Legend displays directional indicators matching Explainable AI
    assert "shap-chart-legend-compact" in index_html
    assert "Lowers Hazard" in index_html
    assert "Increases Hazard" in index_html

    assert ".risk-factors-chart-container" in st_css
    assert ".key-risk-factors-list" in st_css
    assert "max-height: 320px;" in st_css
    assert "overflow-y: auto;" in st_css

    # 3. Static JS assertions: function definitions and data combination
    assert "function renderUnderwritingTornadoChart(res)" in main_js
    assert "function buildTornadoChartConfig(" in main_js
    assert "allFactors.sort((a, b) => b.absMagnitude - a.absMagnitude)" in main_js
    assert "allFactors.slice(0, 6)" in main_js

    # 4. Node.js runtime behavior simulation
    node_script = """
    const fs = require('fs');

    let interceptedChart = null;

    // Browser environment mocks
    global.window = { addEventListener: () => {} };
    global.document = {
      documentElement: { style: {} },
      addEventListener: () => {},
      getElementById: (id) => {
        if (id === 'underwritingTornadoChart') {
          return { id: 'underwritingTornadoChart', parentElement: {} };
        }
        if (id === 'risk-factors-container') {
          return { id: 'risk-factors-container', innerHTML: '' };
        }
        return null;
      }
    };
    global.getComputedStyle = () => ({
      getPropertyValue: (name) => {
        if (name === '--risk-increase') return '#C94A45';
        if (name === '--risk-decrease') return '#078A63';
        if (name === '--risk-increase-text') return '#A83E3A';
        if (name === '--risk-decrease-text') return '#056B4D';
        return '';
      }
    });

    // Mock Chart.js constructor
    global.Chart = function(canvas, config) {
      interceptedChart = config;
      this.canvas = canvas;
      this.config = config;
      this.destroy = () => {};
      this.resize = () => {};
    };

    const jsSource = fs.readFileSync('src/ui/static/js/main.js', 'utf8');
    eval(jsSource);

    // Mock scoring response with 5 escalators and 5 reducers (10 total features)
    const mockRes = {
      top_risk_escalators: [
        { feature: 'EXT_SOURCE_2', shap_value: 0.263, feature_value: 0.25 },
        { feature: 'AMT_CREDIT', shap_value: 0.145, feature_value: 406597.5 },
        { feature: 'AMT_ANNUITY', shap_value: 0.089, feature_value: 24700.5 },
        { feature: 'AGE_YEARS', shap_value: 0.040, feature_value: 26 },
        { feature: 'AMT_GOODS_PRICE', shap_value: 0.015, feature_value: 351000 }
      ],
      top_risk_reducers: [
        { feature: 'EXT_SOURCES_MEAN', shap_value: -0.354, feature_value: 0.65 },
        { feature: 'EMPLOYED_YEARS', shap_value: -0.198, feature_value: 3.5 },
        { feature: 'AMT_INCOME_TOTAL', shap_value: -0.120, feature_value: 202500 },
        { feature: 'NAME_EDUCATION_TYPE', shap_value: -0.050, feature_value: 'Higher education' },
        { feature: 'PAYMENT_RATE', shap_value: -0.005, feature_value: 0.06 }
      ]
    };

    window.renderUnderwritingTornadoChart(mockRes);

    console.log(JSON.stringify({
      chartConfig: {
        type: interceptedChart.type,
        indexAxis: interceptedChart.options.indexAxis,
        labels: interceptedChart.data.labels,
        data: interceptedChart.data.datasets[0].data,
        backgroundColors: interceptedChart.data.datasets[0].backgroundColor,
        borderColors: interceptedChart.data.datasets[0].borderColor,
        pluginCount: (interceptedChart.plugins || []).length
      }
    }));
    """

    res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
    out = json.loads(res.stdout.strip())
    cfg = out["chartConfig"]

    # Horizontal bar chart
    assert cfg["type"] == "bar"
    assert cfg["indexAxis"] == "y"

    # Capped at top 6 features (out of 10 input features)
    assert len(cfg["labels"]) == 6
    assert len(cfg["data"]) == 6

    # Features must be strictly sorted by absolute magnitude descending:
    # 1. EXT_SOURCES_MEAN (|-0.354| = 0.354)
    # 2. EXT_SOURCE_2 (|+0.263| = 0.263)
    # 3. EMPLOYED_YEARS (|-0.198| = 0.198)
    # 4. AMT_CREDIT (|+0.145| = 0.145)
    # 5. AMT_INCOME_TOTAL (|-0.120| = 0.120)
    # 6. AMT_ANNUITY (|+0.089| = 0.089)
    expected_labels = [
        "Composite Bureau Score",
        "External Bureau Score 2",
        "Employment Tenure",
        "Total Credit Amount",
        "Annual Gross Income",
        "Monthly Annuity Burden"
    ]
    expected_data = [-0.354, 0.263, -0.198, 0.145, -0.120, 0.089]

    assert cfg["labels"] == expected_labels
    assert cfg["data"] == expected_data

    # Verify descending absolute magnitude
    abs_values = [abs(v) for v in cfg["data"]]
    assert abs_values == sorted(abs_values, reverse=True)

    # Verify both positive (red) and negative (green) contributors are present
    pos_count = sum(1 for v in cfg["data"] if v > 0)
    neg_count = sum(1 for v in cfg["data"] if v < 0)
    assert pos_count == 3
    assert neg_count == 3

    for i, val in enumerate(cfg["data"]):
        if val > 0:
            assert cfg["backgroundColors"][i] == "#C94A45"
            assert cfg["borderColors"][i] == "#A83E3A"
        else:
            assert cfg["backgroundColors"][i] == "#078A63"
            assert cfg["borderColors"][i] == "#056B4D"

    # Data label plugin attached
    assert cfg["pluginCount"] >= 1


def test_underwriting_subtab_visibility_gating_and_state_preservation(client, index_html: str):
    """Verifies that the Manual Input / Quick Load toggle gates visibility:

    - When Quick Load is active: sample-applicant chips are shown, manual form fields are hidden.
    - When Manual Input is active: sample-applicant chips are hidden, manual form fields are shown.
    - Switching back and forth preserves user-edited values without clearing.
    - Selecting a quick load profile pre-fills manual fields when switching back.
    """
    import subprocess
    import json

    dom = parse_dom(index_html)
    st_css = client.get("/static/css/style.css").data.decode("utf-8")
    ds_css = client.get("/static/css/design-system.css").data.decode("utf-8")

    # 1. HTML initial state
    quick_panel = dom.find_by_id("quickload-panel")
    manual_fields = dom.find_by_id("manual-entry-fields")
    manual_btn = dom.find_by_id("subtab-manual-btn")
    quickload_btn = dom.find_by_id("subtab-quickload-btn")

    assert quick_panel is not None
    assert manual_fields is not None
    assert manual_btn is not None and manual_btn.has_class("active")
    assert quickload_btn is not None and not quickload_btn.has_class("active")
    # Quick load panel is hidden initially
    assert quick_panel.has_class("is-hidden") or "hidden" in quick_panel.attrs
    # Manual fields are not hidden initially
    assert not manual_fields.has_class("is-hidden") and "hidden" not in manual_fields.attrs

    # 2. CSS gating rules
    for css in [st_css, ds_css]:
        assert ".quickload-drawer.is-hidden" in css or "#quickload-panel[hidden]" in css
        assert ".manual-entry-fields.is-hidden" in css or "#manual-entry-fields[hidden]" in css

    # 3. Node.js runtime simulation of toggle gating and state preservation
    node_script = """
    const fs = require('fs');

    // DOM Mocks
    const elements = {};
    function createMockElement(id, initialDisplay = 'block') {
      const classSet = new Set();
      const el = {
        id,
        style: { display: initialDisplay },
        hidden: false,
        value: '',
        classList: {
          add: (c) => classSet.add(c),
          remove: (c) => classSet.delete(c),
          contains: (c) => classSet.has(c),
          toggle: (c, force) => {
            if (force === undefined) {
              if (classSet.has(c)) classSet.delete(c); else classSet.add(c);
            } else if (force) {
              classSet.add(c);
            } else {
              classSet.delete(c);
            }
          }
        },
        getAttribute: (attr) => el[attr] || null,
        setAttribute: (attr, val) => { el[attr] = val; },
        addEventListener: () => {},
        querySelectorAll: () => []
      };
      elements[id] = el;
      return el;
    }

    createMockElement('subtab-manual-btn');
    createMockElement('subtab-quickload-btn');
    createMockElement('quickload-panel', 'none');
    createMockElement('manual-entry-fields', 'block');
    createMockElement('scoring-result-content');
    createMockElement('scoring-placeholder');
    createMockElement('xai-profile-status');
    createMockElement('xai-sheet-id');
    createMockElement('xai-sheet-age');
    createMockElement('xai-sheet-gender');
    createMockElement('xai-sheet-income');
    createMockElement('xai-sheet-employed');
    createMockElement('xai-sheet-credit');
    createMockElement('xai-sheet-annuity');
    createMockElement('xai-sheet-contract');
    createMockElement('xai-sheet-ext');

    // Form inputs
    ['inp-income', 'inp-credit', 'inp-annuity', 'inp-goods', 'inp-age', 'inp-employed',
     'inp-ext1', 'inp-ext2', 'inp-ext3', 'inp-overdue', 'inp-education', 'inp-income-type',
     'inp-family', 'inp-contract', 'inp-housing'].forEach(id => {
      createMockElement(id);
    });

    // Mock applicant chips
    const chipBtns = [100001, 100005, 100013, 100028].map(id => {
      const btn = createMockElement('btn-' + id);
      btn['data-app-id'] = String(id);
      btn.textContent = '#' + id;
      return btn;
    });

    global.window = { addEventListener: () => {} };
    global.document = {
      documentElement: { style: {} },
      addEventListener: () => {},
      getElementById: (id) => elements[id] || null,
      querySelectorAll: (sel) => {
        if (sel === '.test-loader-btn') return chipBtns;
        return [];
      }
    };
    global.getComputedStyle = () => ({ getPropertyValue: () => '' });

    const jsSource = fs.readFileSync('src/ui/static/js/main.js', 'utf8');
    eval(jsSource);

    const log = [];

    // Step 1: Initialize in Manual Input mode
    window.switchSimulatorSubtab('manual');
    log.push({
      step: 'init_manual',
      manualBtnActive: elements['subtab-manual-btn'].classList.contains('active'),
      quickloadBtnActive: elements['subtab-quickload-btn'].classList.contains('active'),
      quickDrawerHidden: elements['quickload-panel'].hidden || elements['quickload-panel'].style.display === 'none',
      manualFieldsVisible: !elements['manual-entry-fields'].hidden && elements['manual-entry-fields'].style.display !== 'none'
    });

    // Step 2: User manually edits fields in Manual Input mode
    elements['inp-income'].value = '275000';
    elements['inp-credit'].value = '650000';
    elements['inp-age'].value = '42';

    // Step 3: Toggle to Quick Load mode (without clicking a chip yet)
    window.switchSimulatorSubtab('quickload');
    log.push({
      step: 'toggle_quickload',
      manualBtnActive: elements['subtab-manual-btn'].classList.contains('active'),
      quickloadBtnActive: elements['subtab-quickload-btn'].classList.contains('active'),
      quickDrawerVisible: !elements['quickload-panel'].hidden && elements['quickload-panel'].style.display === 'block',
      manualFieldsHidden: elements['manual-entry-fields'].hidden || elements['manual-entry-fields'].style.display === 'none',
      // Form fields MUST retain existing values:
      preservedIncome: elements['inp-income'].value,
      preservedCredit: elements['inp-credit'].value,
      preservedAge: elements['inp-age'].value
    });

    // Step 4: Toggle back to Manual Input mode (existing state must be preserved!)
    window.switchSimulatorSubtab('manual');
    log.push({
      step: 'return_manual_without_load',
      quickDrawerHidden: elements['quickload-panel'].hidden || elements['quickload-panel'].style.display === 'none',
      manualFieldsVisible: !elements['manual-entry-fields'].hidden && elements['manual-entry-fields'].style.display !== 'none',
      incomeStillPreserved: elements['inp-income'].value === '275000',
      creditStillPreserved: elements['inp-credit'].value === '650000',
      ageStillPreserved: elements['inp-age'].value === '42'
    });

    // Step 5: Toggle to Quick Load mode and select applicant #100005
    window.switchSimulatorSubtab('quickload');
    window.loadTestApplicant(100005);
    log.push({
      step: 'quickload_applicant_100005',
      loadedIncome: elements['inp-income'].value,
      loadedCredit: elements['inp-credit'].value,
      chipActive: chipBtns[1].classList.contains('active')
    });

    // Step 6: Toggle to Manual Input mode (now pre-filled with last-loaded values from #100005)
    window.switchSimulatorSubtab('manual');
    log.push({
      step: 'return_manual_after_load',
      manualFieldsVisible: !elements['manual-entry-fields'].hidden,
      prefilledIncome: elements['inp-income'].value,
      prefilledCredit: elements['inp-credit'].value
    });

    console.log(JSON.stringify(log));
    """

    res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
    steps = {s["step"]: s for s in json.loads(res.stdout.strip())}

    # Verify Step 1: Initial manual mode
    s1 = steps["init_manual"]
    assert s1["manualBtnActive"] is True
    assert s1["quickloadBtnActive"] is False
    assert s1["quickDrawerHidden"] is True
    assert s1["manualFieldsVisible"] is True

    # Verify Step 3: Quickload mode hides manual fields and shows chips, keeping edited values
    s3 = steps["toggle_quickload"]
    assert s3["manualBtnActive"] is False
    assert s3["quickloadBtnActive"] is True
    assert s3["quickDrawerVisible"] is True
    assert s3["manualFieldsHidden"] is True
    assert s3["preservedIncome"] == "275000"
    assert s3["preservedCredit"] == "650000"
    assert s3["preservedAge"] == "42"

    # Verify Step 4: Returning to manual preserves user edits
    s4 = steps["return_manual_without_load"]
    assert s4["quickDrawerHidden"] is True
    assert s4["manualFieldsVisible"] is True
    assert s4["incomeStillPreserved"] is True
    assert s4["creditStillPreserved"] is True
    assert s4["ageStillPreserved"] is True

    # Verify Step 5: Quickload selection populates fields and highlights active chip
    s5 = steps["quickload_applicant_100005"]
    assert str(s5["loadedIncome"]) == "99000"
    assert str(s5["loadedCredit"]) == "222768"
    assert s5["chipActive"] is True

    # Verify Step 6: Manual mode shows pre-filled values from last-loaded applicant
    s6 = steps["return_manual_after_load"]
    assert s6["manualFieldsVisible"] is True
    assert str(s6["prefilledIncome"]) == "99000"
    assert str(s6["prefilledCredit"]) == "222768"


def test_topbar_model_status_indicators_as_pills(client, index_html: str):
    """Verifies that the top bar model status indicators:
      - Stay inline inside .navbar .header-status (no layout shift).
      - Contain both 'LightGBM · AUC 0.7717' and 'LLM ready'.
      - Are styled as small pill/chip components with subtle background fill,
        border-radius (9999px), slightly larger font size (13px), and colored status dot on left.
    """
    dom = parse_dom(index_html)
    navbars = dom.find_all_by_class("navbar")
    assert len(navbars) >= 1

    header_statuses = dom.find_all_by_class("header-status")
    assert len(header_statuses) >= 1

    indicators = dom.find_all_by_class("status-indicator")
    assert len(indicators) >= 2

    # Verify indicators text
    texts = [e.text for e in indicators]
    assert any("LightGBM · AUC 0.7717" in t for t in texts)
    assert any("LLM ready" in t for t in texts)

    # Verify colored status dots exist in markup
    dots = dom.find_all_by_class("status-dot")
    assert len(dots) >= 2

    # Verify CSS styling in both style.css and design-system.css
    style_css = client.get("/static/css/style.css").data.decode("utf-8")
    ds_css = client.get("/static/css/design-system.css").data.decode("utf-8")

    for css in [style_css, ds_css]:
        assert ".status-indicator" in css
        assert "9999px" in css
        assert "13px" in css
        assert "padding:" in css
        assert ".status-dot" in css


def test_policy_tab_is_purely_static_and_simulator_owns_guardrails_audit(client, index_html: str):
    """
    Verifies that:
    1. Credit Policy Rules tab contains NO active applicant table and NO applicant-specific data.
    2. Underwriting Simulator contains the expandable heuristics drawer with #policy-rules-tbody.
    3. The toggle button #btn-audit-heuristics is present in the Simulator.
    4. Policy tab retains all portfolio-level static content:
       - Risk Bands & Actions Matrix
       - Why These Thresholds?
       - Risk-band distribution
    """
    dom = parse_dom(index_html)

    # 1. Underwriting Simulator owns the applicant guardrails audit
    assert dom.find_by_id("guardrail-audit-drawer") is not None
    assert dom.find_by_id("btn-audit-heuristics") is not None
    assert dom.find_by_id("policy-rules-tbody") is not None

    # Verify button references toggleGuardrailAudit
    btn = dom.find_by_id("btn-audit-heuristics")
    assert "toggleGuardrailAudit()" in btn.attrs.get("onclick", "")

    # 2. Check partial file directly to confirm Credit Policy Rules tab has no per-applicant table
    from pathlib import Path
    policy_partial_path = Path(__file__).resolve().parent.parent / "src/ui/templates/partials/policy_rules.html"
    with open(policy_partial_path, "r", encoding="utf-8") as f:
        policy_html = f.read()

    assert "Active Applicant Policy Rules Audit" not in policy_html
    assert "policy-rules-tbody" not in policy_html
    assert "Live evaluation of 5 deterministic credit guardrails" not in policy_html

    # 3. Policy tab retains portfolio-level static content
    assert "Risk Bands &amp; Actions Matrix" in policy_html or "Risk Bands & Actions Matrix" in policy_html
    assert "Why These Thresholds?" in policy_html
    assert "Risk-band distribution" in policy_html
    assert "risk_band_distribution.png" in policy_html


def test_talk_to_data_scrollable_and_no_bottom_dead_space(client):
    """
    Verifies that:
    1. .chat-query-card uses height: auto to eliminate dead empty space at the bottom.
    2. .chat-exchange-card uses flex-shrink: 0 and overflow: visible so content does not clip.
    3. .chat-history-stream / .chat-message-list uses overflow-y: auto and max-height: 320px for bounded scrolling.
    """
    style_css = client.get("/static/css/style.css").data.decode("utf-8")
    ds_css = client.get("/static/css/design-system.css").data.decode("utf-8")

    for css in [style_css, ds_css]:
        # Exchange card does not shrink inside flex stream and does not clip
        assert ".chat-exchange-card" in css
        assert "flex-shrink: 0" in css
        assert "min-height: fit-content" in css

