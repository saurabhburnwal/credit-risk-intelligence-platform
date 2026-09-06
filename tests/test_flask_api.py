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
