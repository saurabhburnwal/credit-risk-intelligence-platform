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


def test_policy_rules_engine_and_flags():
    """Verify that individual policy flags (FLAG_HIGH_DTI, FLAG_LOW_EXT_SOURCE, FLAG_PAST_DUE) trigger correctly."""
    engine = get_inference_engine()

    # 1. Test Clean Profile - All Rules Pass, All Flags False
    clean_applicant = {
        "AMT_INCOME_TOTAL": 200000.0,
        "AMT_CREDIT": 300000.0,
        "AMT_ANNUITY": 15000.0,        # DTI = 300k / 200k = 1.5 total debt, but annuity/income = 7.5%
        "DAYS_BIRTH": -15000,          # ~41 years old
        "DAYS_EMPLOYED": -2000,        # ~5.5 years tenure
        "EXT_SOURCE_1": 0.60,
        "EXT_SOURCE_2": 0.65,
        "EXT_SOURCE_3": 0.70,
        "BUREAU_TOTAL_OVERDUE": 0.0,
    }
    res_clean = engine.predict(clean_applicant)
    flags_clean = res_clean["policy_rules"]["flags"]
    assert flags_clean["FLAG_HIGH_DTI"] is False
    assert flags_clean["FLAG_LOW_EXT_SOURCE"] is False
    assert flags_clean["FLAG_PAST_DUE"] is False
    assert flags_clean["FLAG_UNSTABLE_TENURE"] is False
    assert flags_clean["FLAG_PAYMENT_RATE_STRESS"] is False
    assert res_clean["policy_rules"]["all_passed"] is True
    assert res_clean["policy_rules"]["failed_count"] == 0

    # 2. Test Triggering FLAG_HIGH_DTI
    high_dti_applicant = dict(clean_applicant)
    high_dti_applicant["AMT_INCOME_TOTAL"] = 50000.0
    high_dti_applicant["AMT_ANNUITY"] = 25000.0  # Annuity/Income = 50% (>40%)
    res_dti = engine.predict(high_dti_applicant)
    assert res_dti["policy_rules"]["flags"]["FLAG_HIGH_DTI"] is True

    # 3. Test Triggering FLAG_LOW_EXT_SOURCE
    low_ext_applicant = dict(clean_applicant)
    low_ext_applicant["EXT_SOURCE_1"] = 0.10
    low_ext_applicant["EXT_SOURCE_2"] = 0.20
    low_ext_applicant["EXT_SOURCE_3"] = 0.15      # Mean = 0.15 (<0.35)
    res_ext = engine.predict(low_ext_applicant)
    assert res_ext["policy_rules"]["flags"]["FLAG_LOW_EXT_SOURCE"] is True

    # 4. Test Triggering FLAG_PAST_DUE
    past_due_applicant = dict(clean_applicant)
    past_due_applicant["BUREAU_TOTAL_OVERDUE"] = 15000.0  # Overdue debt > 0
    res_due = engine.predict(past_due_applicant)
    assert res_due["policy_rules"]["flags"]["FLAG_PAST_DUE"] is True
    assert res_due["policy_rules"]["all_passed"] is False


def test_shap_base_value_and_feature_translations():
    """Verify that SHAP TreeExplainer base value is present and feature explanations are plain English."""
    from src.utils.feature_translator import translate_feature_name, generate_feature_explanation, FEATURE_NAME_MAP
    engine = get_inference_engine()

    prime = {
        "AMT_INCOME_TOTAL": 250000.0,
        "AMT_CREDIT": 400000.0,
        "AMT_ANNUITY": 16000.0,
        "EXT_SOURCE_1": 0.75,
        "EXT_SOURCE_2": 0.72,
        "EXT_SOURCE_3": 0.70,
    }
    res = engine.predict(prime)
    assert "shap_base_value" in res
    assert isinstance(res["shap_base_value"], (float, int))

    # Test translator mappings
    assert "EXT_SOURCES_MEAN" in FEATURE_NAME_MAP
    assert translate_feature_name("EXT_SOURCES_MEAN") == "Composite External Credit Bureau Score"
    assert translate_feature_name("GOODS_PRICE_TO_CREDIT") == "Goods Price to Loan Ratio (Collateral Margin)"
    assert translate_feature_name("UNKNOWN_CUSTOM_COL") == "Unknown Custom Col"

    # Test explanation generation
    exp_pos = generate_feature_explanation("EXT_SOURCES_MEAN", 0.15)
    assert "elevated" in exp_pos or "increased" in exp_pos
    assert "(+0.15)" in exp_pos

    exp_neg = generate_feature_explanation("EXT_SOURCES_MEAN", -0.25)
    assert "reduced" in exp_neg
    assert "(-0.25)" in exp_neg


def test_nlp_compatibility_package():
    """Verify that src.nlp compatibility exports map cleanly to talk_to_data."""
    from src.nlp.agent import ConversationalTalkToDataAgent, get_talk_to_data_agent
    from src.nlp.sql_runner import SafeQueryRunner, SQLSecurityError
    import src.nlp as nlp

    agent = get_talk_to_data_agent()
    assert isinstance(agent, ConversationalTalkToDataAgent)

    runner = SafeQueryRunner()
    assert isinstance(runner, SafeQueryRunner)
    assert issubclass(SQLSecurityError, Exception)
    assert nlp.ConversationalTalkToDataAgent is ConversationalTalkToDataAgent
    assert nlp.SafeQueryRunner is SafeQueryRunner

