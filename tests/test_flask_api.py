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

