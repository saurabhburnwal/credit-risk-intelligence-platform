"""Tests for Flask web application endpoints."""
import pytest
from src.ui.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"NeoStats Credit Risk Intelligence" in res.data


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["db_exists"] is True
    assert data["model_loaded"] is True


def test_eda_insights_endpoint(client):
    res = client.get("/api/eda/insights")
    assert res.status_code == 200
    data = res.get_json()
    assert data["portfolio"]["total_applications"] == 307511
    assert len(data["insights_list"]) == 5


def test_scoring_endpoint(client):
    res = client.post("/api/underwriting/score", json={
        "AMT_INCOME_TOTAL": 180000,
        "AMT_CREDIT": 450000,
        "AMT_ANNUITY": 22500,
        "EXT_SOURCE_1": 0.65,
        "EXT_SOURCE_2": 0.60,
        "EXT_SOURCE_3": 0.62
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "risk_score" in data
    assert "risk_band" in data
    assert "business_explanations" in data
    assert "policy_rules" in data
    assert "flags" in data["policy_rules"]
    assert "FLAG_HIGH_DTI" in data["policy_rules"]["flags"]
    assert "FLAG_LOW_EXT_SOURCE" in data["policy_rules"]["flags"]
    assert "FLAG_PAST_DUE" in data["policy_rules"]["flags"]
    assert len(data["policy_rules"]["rules"]) >= 5


def test_unseen_applicant_scoring(client):
    """Test inference on a real record from application_test.csv (Applicant #100001)."""
    res = client.post("/api/underwriting/score", json={
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
        "NAME_EDUCATION_TYPE": "Higher education",
        "NAME_INCOME_TYPE": "Working",
        "BUREAU_TOTAL_OVERDUE": 0.0
    })
    assert res.status_code == 200
    data = res.get_json()
    assert 0 <= data["risk_score"] <= 100
    assert data["risk_band"] == "Low Risk"
    assert data["calibrated_default_prob"] < 0.05
    assert len(data["top_risk_reducers"]) > 0
    assert data["policy_rules"]["all_passed"] is True


def test_api_v1_predict_endpoint(client):
    """Verify /api/v1/predict alias returns full payload including shap_base_value."""
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
    assert "risk_score" in data
    assert "risk_band" in data
    assert "calibrated_default_prob" in data
    assert "shap_base_value" in data
    assert isinstance(data["shap_base_value"], (float, int))
    assert "top_risk_escalators" in data
    assert "top_risk_reducers" in data
    assert "business_explanations" in data
    assert "policy_rules" in data
    assert len(data["business_explanations"]) > 0


def test_api_v1_predict_malformed_payload(client):
    """Verify /api/v1/predict handles empty or malformed payload cleanly with HTTP 400."""
    res_empty = client.post("/api/v1/predict", data="", content_type="application/json")
    assert res_empty.status_code == 400
    assert res_empty.get_json()["error"] == "Invalid or missing JSON payload"

    res_empty_dict = client.post("/api/v1/predict", json={})
    assert res_empty_dict.status_code == 400
    assert res_empty_dict.get_json()["error"] == "Invalid or missing JSON payload"


def test_api_v1_query_endpoint(client):
    """Verify /api/v1/query alias processes questions cleanly."""
    res = client.post("/api/v1/query", json={
        "question": "What is the default rate by education level?"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "sql" in data
    assert "data" in data
    assert "tier_used" in data


def test_api_v1_predict_invalid_types(client):
    """Verify /api/v1/predict returns HTTP 400 for type mismatch errors."""
    res_invalid_str = client.post("/api/v1/predict", json={"AMT_INCOME_TOTAL": "invalid"})
    assert res_invalid_str.status_code == 400
    assert "Invalid input format or type" in res_invalid_str.get_json()["error"]

    res_none = client.post("/api/v1/predict", json={"AMT_INCOME_TOTAL": None})
    assert res_none.status_code == 400
    assert "Invalid input format or type" in res_none.get_json()["error"]

    res_list = client.post("/api/v1/predict", json={"EXT_SOURCE_1": [0.5]})
    assert res_list.status_code == 400
    assert "Invalid input format or type" in res_list.get_json()["error"]


def test_api_v1_query_invalid_questions(client):
    """Verify /api/v1/query returns HTTP 400 for non-string, empty, or whitespace questions."""
    res_int = client.post("/api/v1/query", json={"question": 12345})
    assert res_int.status_code == 400
    assert "Empty or invalid question string provided" in res_int.get_json()["error"]

    res_list = client.post("/api/v1/query", json={"question": ["invalid"]})
    assert res_list.status_code == 400
    assert "Empty or invalid question string provided" in res_list.get_json()["error"]

    res_empty_str = client.post("/api/v1/query", json={"question": ""})
    assert res_empty_str.status_code == 400
    assert "Empty or invalid question string provided" in res_empty_str.get_json()["error"]

    res_whitespace = client.post("/api/v1/query", json={"question": "   "})
    assert res_whitespace.status_code == 400
    assert "Empty or invalid question string provided" in res_whitespace.get_json()["error"]

    res_query_none = client.post("/api/v1/query", json={"query": None})
    assert res_query_none.status_code == 400
    assert "Empty or invalid question string provided" in res_query_none.get_json()["error"]



