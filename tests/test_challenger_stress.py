"""
Challenger Empirical Stress Testing Suite for Redesigned Frontend & APIs.
Empirically verifies:
  1. Rapid sequential & concurrent requests to /api/v1/predict and /api/v1/query.
  2. Boundary input conditions (extreme numbers, NaN/Inf, empty chat queries, type mismatches).
  3. SQL injection and XSS defense across diverse payloads through chat UI/API.
  4. Floating chat widget linkage to Tab 5, focus behavior, and DOM/CSS integrity.
  5. Zero server crashes (0 unhandled 500 errors) and database integrity preservation.
"""

import re
import time
import sqlite3
import concurrent.futures
import pytest
from src.ui.app import app
from src.utils.config import DB_PATH


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ============================================================================
# 1. Rapid Sequential & Concurrent API Requests
# ============================================================================

def test_stress_rapid_sequential_predict(client):
    """Executes 30 rapid sequential requests to /api/v1/predict with varying applicant profiles."""
    test_applicants = [
        {"SK_ID_CURR": 100001, "AMT_INCOME_TOTAL": 135000, "AMT_CREDIT": 568800, "AMT_ANNUITY": 20560.5, "EXT_SOURCE_1": 0.75, "EXT_SOURCE_2": 0.79, "EXT_SOURCE_3": 0.16},
        {"SK_ID_CURR": 100005, "AMT_INCOME_TOTAL": 99000, "AMT_CREDIT": 222768, "AMT_ANNUITY": 17370, "EXT_SOURCE_1": 0.56, "EXT_SOURCE_2": 0.29, "EXT_SOURCE_3": 0.43},
        {"SK_ID_CURR": 100013, "AMT_INCOME_TOTAL": 202500, "AMT_CREDIT": 663264, "AMT_ANNUITY": 69777, "EXT_SOURCE_1": 0.50, "EXT_SOURCE_2": 0.70, "EXT_SOURCE_3": 0.61},
        {"SK_ID_CURR": 100028, "AMT_INCOME_TOTAL": 315000, "AMT_CREDIT": 1575000, "AMT_ANNUITY": 49018.5, "EXT_SOURCE_1": 0.52, "EXT_SOURCE_2": 0.51, "EXT_SOURCE_3": 0.61},
    ]

    total_requests = 30
    latencies = []
    error_count = 0

    for i in range(total_requests):
        payload = test_applicants[i % len(test_applicants)].copy()
        payload["AMT_INCOME_TOTAL"] += i * 1000  # subtle variation

        t0 = time.time()
        res = client.post("/api/v1/predict", json=payload)
        t1 = time.time()
        latencies.append(t1 - t0)

        assert res.status_code == 200, f"Request {i} failed with status {res.status_code}: {res.get_data(as_text=True)}"
        data = res.get_json()
        assert "risk_score" in data
        assert "calibrated_default_prob" in data
        assert 0.0 <= data["calibrated_default_prob"] <= 1.0
        assert data["risk_band"] in ("Low Risk", "Medium Risk", "High Risk")
        assert "top_risk_escalators" in data
        assert "top_risk_reducers" in data
        assert "policy_rules" in data

    avg_latency = sum(latencies) / len(latencies)
    assert error_count == 0
    assert avg_latency < 1.0, f"Average predict latency too high: {avg_latency:.3f}s"


def test_stress_concurrent_predict(client):
    """Executes 8 concurrent scoring requests to verify thread safety and state isolation."""
    payload = {
        "SK_ID_CURR": 100001,
        "AMT_INCOME_TOTAL": 180000.0,
        "AMT_CREDIT": 450000.0,
        "AMT_ANNUITY": 22500.0,
        "EXT_SOURCE_1": 0.65,
        "EXT_SOURCE_2": 0.55,
        "EXT_SOURCE_3": 0.70
    }

    def send_req(i):
        with app.test_client() as c:
            p = payload.copy()
            p["SK_ID_CURR"] += i
            res = c.post("/api/v1/predict", json=p)
            return res.status_code, res.get_json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(send_req, i) for i in range(8)]
        results = [f.result() for f in futures]

    for idx, (status_code, data) in enumerate(results):
        assert status_code == 200, f"Concurrent request {idx} returned status {status_code}"
        assert data["applicant_id"] == 100001 + idx
        assert "risk_score" in data
        assert "calibrated_default_prob" in data


def test_stress_rapid_sequential_query_deterministic(client, monkeypatch):
    """Executes 15 rapid sequential queries to /api/v1/query with deterministic fail-safe."""
    from src.talk_to_data.nl_to_sql import GroqProvider, OllamaProvider
    monkeypatch.setattr(GroqProvider, "is_available", lambda self: False)
    monkeypatch.setattr(OllamaProvider, "is_available", lambda self: False)

    queries = [
        "What is the default rate across different education levels?",
        "Show average credit amount and default rate by income type.",
        "How do external credit bureau scores impact default rates?",
        "Compare default rates for applicants with prior bureau overdue debt versus clean credit histories.",
        "Which demographic clusters by gender and family status have the highest default rates?",
        "What is the portfolio summary and total loans?",
        "Show default rates for high DTI debt burden applicants",
        "What is the default rate by contract type?"
    ]

    for i in range(15):
        q = queries[i % len(queries)]
        res = client.post("/api/v1/query", json={"question": q})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert len(data["sql"]) > 10
        assert data["row_count"] > 0
        assert "data" in data
        assert len(data["business_insight"]) > 0


# ============================================================================
# 2. Boundary Input Conditions & Resiliency
# ============================================================================

def test_stress_boundary_numerical_values(client):
    """Tests extreme numerical values, edge cases, and string numbers."""
    extreme_cases = [
        # Ultra-high income ($100M)
        {"AMT_INCOME_TOTAL": 100_000_000.0, "AMT_CREDIT": 500000.0, "AMT_ANNUITY": 25000.0},
        # Extreme negative income (handled safely)
        {"AMT_INCOME_TOTAL": -50_000.0, "AMT_CREDIT": 500000.0, "AMT_ANNUITY": 25000.0},
        # Denominator edge case (-1.0 + 1.0 = 0.0)
        {"AMT_INCOME_TOTAL": -1.0, "AMT_CREDIT": 500000.0, "AMT_ANNUITY": 25000.0},
        # Zero income and zero credit
        {"AMT_INCOME_TOTAL": 0.0, "AMT_CREDIT": 0.0, "AMT_ANNUITY": 0.0},
        # Jumbo loan credit ($1 Billion)
        {"AMT_INCOME_TOTAL": 250000.0, "AMT_CREDIT": 1_000_000_000.0, "AMT_ANNUITY": 50_000_000.0},
        # Home Credit Pensioner anomaly (DAYS_EMPLOYED = 365243)
        {"DAYS_EMPLOYED": 365243, "DAYS_BIRTH": -20000},
        # Extreme age boundary (100 years old = -36525 days, 18 years old = -6574 days)
        {"DAYS_BIRTH": -36525, "DAYS_EMPLOYED": -10000},
        {"DAYS_BIRTH": -6574, "DAYS_EMPLOYED": -365},
        # Boundary external bureau scores
        {"EXT_SOURCE_1": 0.0, "EXT_SOURCE_2": 0.0, "EXT_SOURCE_3": 0.0},
        {"EXT_SOURCE_1": 1.0, "EXT_SOURCE_2": 1.0, "EXT_SOURCE_3": 1.0},
        {"EXT_SOURCE_1": -0.5, "EXT_SOURCE_2": 1.5, "EXT_SOURCE_3": 99.0},
        # Severe overdue debt
        {"BUREAU_TOTAL_OVERDUE": 10_000_000.0, "DEF_30_CNT_SOCIAL_CIRCLE": 50.0},
        # String representations of NaN and Infinity
        {"AMT_INCOME_TOTAL": "NaN"},
        {"AMT_INCOME_TOTAL": "Infinity"},
    ]

    for idx, case in enumerate(extreme_cases):
        res = client.post("/api/v1/predict", json=case)
        # Must return 200 with calibrated prediction or 400 for bad input; NEVER 500!
        assert res.status_code in (200, 400), f"Case {idx} ({case}) returned unexpected status {res.status_code}"
        if res.status_code == 200:
            data = res.get_json()
            assert "risk_score" in data
            assert "calibrated_default_prob" in data
            assert 0.0 <= data["calibrated_default_prob"] <= 1.0


def test_stress_boundary_empty_and_malformed_chat_queries(client):
    """Tests empty, whitespace, null, non-string, and invalid chat queries."""
    bad_payloads = [
        {"question": ""},
        {"question": "   \t\r\n  "},
        {"question": None},
        {"query": ""},
        {"query": "   "},
        {},
        {"question": 12345},
        {"question": ["not a string"]},
        {"question": {"nested": "value"}},
        {"wrong_key": "What is the default rate?"},
    ]

    for idx, payload in enumerate(bad_payloads):
        res = client.post("/api/v1/query", json=payload)
        assert res.status_code == 400, f"Payload {idx} ({payload}) expected 400, got {res.status_code}"
        data = res.get_json()
        assert "error" in data

    # Raw non-JSON or empty body
    res_empty = client.post("/api/v1/query", data="", content_type="application/json")
    assert res_empty.status_code == 400


def test_stress_huge_chat_query(client, monkeypatch):
    """Tests resilience against an oversized 10,000-character query."""
    from src.talk_to_data.nl_to_sql import GroqProvider, OllamaProvider
    monkeypatch.setattr(GroqProvider, "is_available", lambda self: False)
    monkeypatch.setattr(OllamaProvider, "is_available", lambda self: False)

    huge_query = "What is the default rate across education levels? " + ("A" * 10000)
    res = client.post("/api/v1/query", json={"question": huge_query})
    # Should safely process through deterministic engine or return 400; NEVER 500
    assert res.status_code in (200, 400)
    if res.status_code == 200:
        data = res.get_json()
        assert data["success"] is True


# ============================================================================
# 3. Security Boundaries & SQL Injection Attempts
# ============================================================================

def test_stress_sql_injection_defense(client, monkeypatch):
    """Stress tests SQL injection resilience across diverse attack vectors."""
    from src.talk_to_data.nl_to_sql import GroqProvider, OllamaProvider
    monkeypatch.setattr(GroqProvider, "is_available", lambda self: False)
    monkeypatch.setattr(OllamaProvider, "is_available", lambda self: False)

    sqli_vectors = [
        "' OR '1'='1",
        "1; DROP TABLE applications;",
        "UNION SELECT * FROM sqlite_master; --",
        "SELECT * FROM applications WHERE 1=1 /* bypass */",
        "admin' OR 1=1 #",
        "SELECT 1; UPDATE applications SET TARGET=0;",
        "DROP TABLE applications",
        "1'; ATTACH DATABASE '/tmp/pwn.db' AS pwn; --",
        "'; EXEC xp_cmdshell('dir'); --",
        "<script>alert('XSS')</script>",
        "{{ 7 * 7 }}",
        "SELECT sqlite_version();",
    ]

    for vec in sqli_vectors:
        res = client.post("/api/v1/query", json={"question": vec})
        assert res.status_code == 200, f"Vector {vec} caused non-200 status: {res.status_code}"
        data = res.get_json()
        assert data["success"] is True
        # Ensure fallback safely ran without exposing system internals or executing malicious command
        assert "DROP" not in data["sql"].upper()
        assert "UPDATE" not in data["sql"].upper()
        assert "ATTACH" not in data["sql"].upper()

    # Empirical Database Integrity Check: ensure applications table was NOT modified or dropped
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM applications")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 307511, f"Database integrity compromised! Row count is {count}, expected 307511"


# ============================================================================
# 4. Floating Chat Button & Tab 5 Linkage & Input Focus Verification
# ============================================================================

def test_floating_chat_button_links_and_focuses_tab5(client):
    """
    Verifies that:
      1. #floating-chat-widget exists on the page with .floating-chat-btn.
      2. It has onclick='openFloatingChat()'.
      3. openFloatingChat() in main.js calls switchTab('chat-tab') and focuses #chat-input.
      4. #chat-tab exists and contains #chat-input with type='text'.
      5. CSS ensures fixed, persistent positioning on all views.
    """
    # 1. Fetch index page
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # 2. Check floating chat button element in HTML
    assert '<div id="floating-chat-widget"' in html
    assert 'class="floating-chat-btn"' in html
    assert 'onclick="openFloatingChat()"' in html
    assert 'chat-float-icon' in html
    assert 'chat-badge-pulse' in html
    assert 'floating-tooltip' in html

    # 3. Check Tab 5 section and chat-input
    assert '<section id="chat-tab"' in html
    assert '<input type="text" id="chat-input"' in html
    assert '<form id="chat-form"' in html
    assert 'onsubmit="sendChatMessage(event)"' in html
    assert '<button type="submit" class="btn btn-emerald" id="chat-submit-btn"' in html
    assert '<select id="chat-example-select"' in html

    # 4. Check main.js implementation
    res_js = client.get("/static/js/main.js")
    assert res_js.status_code == 200
    js = res_js.get_data(as_text=True)

    # Verify openFloatingChat function definition and logic
    assert "function openFloatingChat()" in js
    # Must switch to chat-tab
    assert "switchTab('chat-tab')" in js
    # Must query #chat-input and focus it
    assert "document.getElementById('chat-input')" in js
    assert "input.focus()" in js
    assert "input.scrollIntoView" in js

    # Verify switchTab function activates chat-tab
    assert "function switchTab(tabId)" in js
    assert "document.querySelectorAll('.tab-btn')" in js
    assert "document.querySelectorAll('.tab-content')" in js

    # 5. Check CSS for persistent fixed positioning
    res_css = client.get("/static/css/style.css")
    assert res_css.status_code == 200
    css = res_css.get_data(as_text=True)

    assert ".floating-chat-btn" in css
    # Check fixed positioning and high z-index
    assert "position: fixed;" in css
    assert "z-index: 999;" in css or "z-index: 1000;" in css or "z-index: 99;" in css


# ============================================================================
# 5. Zero Server Crashes & Platform Health Sign-Off
# ============================================================================

def test_zero_server_crashes_and_system_health(client):
    """Confirms zero server crashes, healthcheck endpoint status, and data integrity."""
    # Health endpoint
    res_health = client.get("/health")
    assert res_health.status_code == 200
    health_data = res_health.get_json()
    assert health_data["status"] == "healthy"
    assert health_data["db_exists"] is True
    assert health_data["model_loaded"] is True
    assert health_data["preprocessor_loaded"] is True

    # EDA insights endpoint
    res_eda = client.get("/api/eda/insights")
    assert res_eda.status_code == 200
    eda_data = res_eda.get_json()
    assert eda_data["portfolio"]["total_applications"] == 307511
    assert len(eda_data["insights_list"]) == 5
