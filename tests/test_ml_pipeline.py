"""Tests for ML inference, probability calibration, risk banding, and SHAP."""
import pytest
from src.ml.predict import get_inference_engine


def test_inference_scoring_and_banding():
    engine = get_inference_engine()

    # Prime Borrower Profile
    prime = {
        "AMT_INCOME_TOTAL": 250000.0,
        "AMT_CREDIT": 400000.0,
        "AMT_ANNUITY": 16000.0,
        "AMT_GOODS_PRICE": 400000.0,
        "DAYS_BIRTH": -16000,
        "DAYS_EMPLOYED": -2500,
        "EXT_SOURCE_1": 0.75,
        "EXT_SOURCE_2": 0.72,
        "EXT_SOURCE_3": 0.70,
        "BUREAU_TOTAL_OVERDUE": 0.0,
        "NAME_EDUCATION_TYPE": "Higher education"
    }
    res_prime = engine.predict(prime)
    assert 0 <= res_prime["risk_score"] <= 100
    assert res_prime["risk_band"] == "Low Risk"
    assert res_prime["calibrated_default_prob"] < 0.05
    assert len(res_prime["top_risk_reducers"]) > 0

    # High Risk Profile
    subprime = {
        "AMT_INCOME_TOTAL": 50000.0,
        "AMT_CREDIT": 600000.0,
        "AMT_ANNUITY": 35000.0,
        "AMT_GOODS_PRICE": 550000.0,
        "DAYS_BIRTH": -8200,
        "DAYS_EMPLOYED": -150,
        "EXT_SOURCE_1": 0.15,
        "EXT_SOURCE_2": 0.12,
        "EXT_SOURCE_3": 0.10,
        "BUREAU_TOTAL_OVERDUE": 25000.0,
        "NAME_EDUCATION_TYPE": "Lower secondary"
    }
    res_subprime = engine.predict(subprime)
    assert 0 <= res_subprime["risk_score"] <= 100
    assert res_subprime["risk_band"] == "High Risk"
    assert res_subprime["calibrated_default_prob"] >= 0.15
    assert len(res_subprime["top_risk_escalators"]) > 0
    assert res_subprime["policy_rules"]["failed_count"] >= 2
