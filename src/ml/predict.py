"""
Inference, Explainable AI (SHAP), and Credit Policy Rule Engine for Credit Risk Intelligence.
Produces calibrated default probabilities, 0-100 risk scores, Low/Medium/High risk bands,
local SHAP factor attributions with plain-English translations, and underwriting rule checks.
"""

import sys
import json
import warnings
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
import joblib
import shap

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.preprocessor import CreditRiskPreprocessor
from src.utils.config import (
    MODEL_PATH, PREPROCESSOR_PATH, METADATA_PATH,
    THRESHOLD_LOW_RISK, THRESHOLD_MEDIUM_RISK
)
from src.utils.feature_translator import generate_feature_explanation, translate_feature_name
from src.utils.logger import logger


class CreditRiskInferenceEngine:
    """
    Production-grade inference engine providing:
      1. Default probability prediction with Bayes prior calibration
      2. Risk scoring (0-100) and banding (<5% Low, 5-15% Medium, >=15% High)
      3. Local SHAP factor attribution and business-readable translation
      4. Regulatory credit policy rule verification
    """

    def __init__(self, model_path: Optional[Path] = None, preprocessor_path: Optional[Path] = None):
        self.model_path = model_path or MODEL_PATH
        self.preprocessor_path = preprocessor_path or PREPROCESSOR_PATH

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model artifact missing at {self.model_path}. Train model first.")
        if not self.preprocessor_path.exists():
            raise FileNotFoundError(f"Preprocessor missing at {self.preprocessor_path}. Train model first.")

        logger.info(f"Loading model from {self.model_path}...")
        self.model = joblib.load(self.model_path)
        logger.info(f"Loading preprocessor from {self.preprocessor_path}...")
        self.preprocessor: CreditRiskPreprocessor = CreditRiskPreprocessor.load(self.preprocessor_path)

        # Load metadata if present for training imbalance ratio
        self.class_ratio = 11.39
        if METADATA_PATH.exists():
            try:
                with open(METADATA_PATH) as f:
                    meta = json.load(f)
                    self.class_ratio = meta.get("class_imbalance_ratio", 11.39)
            except Exception:
                pass

        logger.info("Initializing SHAP TreeExplainer...")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.explainer = shap.TreeExplainer(self.model)
        logger.info("CreditRiskInferenceEngine initialized and ready.")

    def _calibrate_probability(self, raw_prob: float) -> float:
        """
        Adjusts raw probability for scale_pos_weight training distortion using Bayes odds adjustment.
        odds_true = odds_weighted / class_ratio
        """
        p = max(1e-6, min(1.0 - 1e-6, float(raw_prob)))
        odds_weighted = p / (1.0 - p)
        odds_true = odds_weighted / self.class_ratio
        p_calibrated = odds_true / (1.0 + odds_true)
        return float(np.clip(p_calibrated, 0.001, 0.999))

    def _evaluate_policy_rules(self, applicant_raw: Dict[str, Any], engineered_row: pd.Series) -> List[Dict[str, Any]]:
        """
        Evaluates heuristic credit underwriting policy rules derived from machine learning splits.
        """
        rules = []

        # Rule 1: High Debt-to-Income (DTI > 40%) - FLAG_HIGH_DTI
        dti = float(engineered_row.get("DEBT_TO_INCOME", 0.0))
        dti_passed = bool(dti <= 0.40)
        rules.append({
            "rule_id": "RULE_DTI_BURDEN",
            "flag_id": "FLAG_HIGH_DTI",
            "name": "Debt-to-Income Limit",
            "threshold": "DTI <= 40%",
            "value": f"{dti * 100:.1f}%",
            "passed": dti_passed,
            "flag_triggered": not dti_passed,
            "severity": "HIGH",
            "rationale": "Applicants allocating >40% of gross income to loan repayments face severe debt stress."
        })

        # Rule 2: Weak External Credit Bureau Score (< 0.35) - FLAG_LOW_EXT_SOURCE
        ext_mean = float(engineered_row.get("EXT_SOURCES_MEAN", 0.5))
        ext_passed = bool(np.isnan(ext_mean) or ext_mean >= 0.35)
        rules.append({
            "rule_id": "RULE_EXT_SCORE_MIN",
            "flag_id": "FLAG_LOW_EXT_SOURCE",
            "name": "External Bureau Score Floor",
            "threshold": "Score Mean >= 0.35",
            "value": f"{ext_mean:.3f}" if not np.isnan(ext_mean) else "N/A",
            "passed": ext_passed,
            "flag_triggered": not ext_passed,
            "severity": "HIGH",
            "rationale": "External credit bureau composite score below 0.35 represents a >10x default risk multiplier."
        })

        # Rule 3: Historical Overdue Delinquencies - FLAG_PAST_DUE
        bureau_overdue = float(applicant_raw.get("BUREAU_TOTAL_OVERDUE", 0.0))
        delinq_passed = bool(bureau_overdue <= 0.0)
        rules.append({
            "rule_id": "RULE_DELINQUENCY_CHECK",
            "flag_id": "FLAG_PAST_DUE",
            "name": "Past Due Credit Clearance",
            "threshold": "Zero Active Overdue Debt",
            "value": f"${bureau_overdue:,.2f}",
            "passed": delinq_passed,
            "flag_triggered": not delinq_passed,
            "severity": "CRITICAL",
            "rationale": "Prior overdue records with external lenders double current default probability."
        })

        # Rule 4: Young Unstable Employment Tenure - FLAG_UNSTABLE_TENURE
        age = float(engineered_row.get("AGE_YEARS", 35.0))
        emp_years = float(engineered_row.get("EMPLOYED_YEARS", 5.0))
        is_unstable = (age < 25.0) and (np.isnan(emp_years) or emp_years < 1.0)
        rules.append({
            "rule_id": "RULE_TENURE_STABILITY",
            "flag_id": "FLAG_UNSTABLE_TENURE",
            "name": "Employment & Age Stability",
            "threshold": "Tenure >= 1 yr if Age < 25",
            "value": f"Age {age:.1f}y, Tenure {emp_years:.1f}y" if not np.isnan(emp_years) else f"Age {age:.1f}y, Unemployed/Pensioner",
            "passed": bool(not is_unstable),
            "flag_triggered": bool(is_unstable),
            "severity": "MEDIUM",
            "rationale": "Young applicants (<25) without established employment tenure carry higher default risk."
        })

        # Rule 5: Payment Rate Strain - FLAG_PAYMENT_RATE_STRESS
        payment_rate = float(engineered_row.get("PAYMENT_RATE", 0.05))
        payment_passed = bool(payment_rate <= 0.08)
        rules.append({
            "rule_id": "RULE_PAYMENT_RATE_STRESS",
            "flag_id": "FLAG_PAYMENT_RATE_STRESS",
            "name": "Payment Rate Cushion",
            "threshold": "Annuity / Credit <= 8%",
            "value": f"{payment_rate * 100:.2f}%",
            "passed": payment_passed,
            "flag_triggered": not payment_passed,
            "severity": "MEDIUM",
            "rationale": "Monthly payments exceeding 8% of total principal create accelerated repayment strain."
        })

        return rules

    def _translate_shap_feature(self, feature: str, value: float, shap_val: float) -> str:
        """Translates technical SHAP values and feature magnitudes into plain-English credit explanations."""
        return generate_feature_explanation(feature, shap_val, value)

    def predict(self, applicant_data: Dict[str, Any] | pd.DataFrame) -> Dict[str, Any]:
        """
        Executes end-to-end scoring, explainability, and policy evaluation for an applicant.
        """
        if isinstance(applicant_data, dict):
            df_raw = pd.DataFrame([applicant_data])
        else:
            df_raw = applicant_data.copy()

        # 1. Feature Preprocessing
        engineered = self.preprocessor._engineer_features(df_raw)
        X_proc = self.preprocessor.transform(df_raw)

        # 2. Raw Model Probability & Bayes Calibration
        raw_prob = float(self.model.predict_proba(X_proc)[0, 1])
        calibrated_prob = self._calibrate_probability(raw_prob)

        # 3. Score & Banding (<5% Low, 5-15% Medium, >=15% High)
        risk_score = int(round(calibrated_prob * 100))

        if calibrated_prob < THRESHOLD_LOW_RISK:
            risk_band = "Low Risk"
            badge_color = "success"
            decision = "Fast-Track Instant Approval"
            rationale = "Applicant demonstrates strong creditworthiness and low probability of default."
        elif calibrated_prob < THRESHOLD_MEDIUM_RISK:
            risk_band = "Medium Risk"
            badge_color = "warning"
            decision = "Manual Review / Additional Collateral"
            rationale = "Applicant falls into standard commercial risk zone; recommends income verification."
        else:
            risk_band = "High Risk"
            badge_color = "danger"
            decision = "Strict Underwriting / Decline"
            rationale = "Applicant exhibits elevated default hazard; requires credit committee exception."

        # 4. Local SHAP Attribution
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            shap_raw = self.explainer.shap_values(X_proc)

        # Normalize SHAP output format across SHAP versions
        if isinstance(shap_raw, list):
            sample_shap = shap_raw[1][0] if len(shap_raw) > 1 else shap_raw[0][0]
        elif len(shap_raw.shape) == 2:
            sample_shap = shap_raw[0]
        else:
            sample_shap = shap_raw[0][0]

        # Extract TreeExplainer base value (expected value in log-odds / margin space)
        if hasattr(self.explainer, "expected_value"):
            ev = self.explainer.expected_value
            if isinstance(ev, (list, np.ndarray)):
                shap_base = float(ev[0])
            else:
                shap_base = float(ev)
        else:
            shap_base = 0.0

        feature_names = self.preprocessor.feature_names
        feature_impacts = []
        for feat, s_val in zip(feature_names, sample_shap):
            raw_val = float(X_proc[feat].iloc[0]) if feat in X_proc.columns else 0.0
            feature_impacts.append({
                "feature": feat,
                "shap_value": float(s_val),
                "feature_value": round(raw_val, 4),
                "direction": "Risk Escalator (+)" if s_val > 0 else "Risk Reducer (-)"
            })

        # Sort top positive and negative factors
        escalators = sorted([f for f in feature_impacts if f["shap_value"] > 0], key=lambda x: x["shap_value"], reverse=True)[:5]
        reducers = sorted([f for f in feature_impacts if f["shap_value"] < 0], key=lambda x: x["shap_value"])[:5]

        # Plain English Explanations
        business_bullets = []
        for f in escalators[:3]:
            business_bullets.append(self._translate_shap_feature(f["feature"], f["feature_value"], f["shap_value"]))
        for f in reducers[:3]:
            business_bullets.append(self._translate_shap_feature(f["feature"], f["feature_value"], f["shap_value"]))

        # 5. Policy Rules Verification
        row_eng = engineered.iloc[0]
        applicant_dict = df_raw.iloc[0].to_dict()
        policy_rules = self._evaluate_policy_rules(applicant_dict, row_eng)
        rules_passed = all(r["passed"] for r in policy_rules)
        failed_count = sum(1 for r in policy_rules if not r["passed"])
        flags_dict = {r["flag_id"]: bool(r["flag_triggered"]) for r in policy_rules if "flag_id" in r}

        return {
            "applicant_id": int(df_raw.get("SK_ID_CURR", pd.Series([100001])).iloc[0]),
            "raw_model_prob": round(raw_prob, 4),
            "calibrated_default_prob": round(calibrated_prob, 4),
            "risk_score": risk_score,
            "risk_band": risk_band,
            "badge_color": badge_color,
            "underwriting_decision": decision,
            "decision_rationale": rationale,
            "shap_base_value": round(shap_base, 4),
            "top_risk_escalators": escalators,
            "top_risk_reducers": reducers,
            "business_explanations": business_bullets,
            "policy_rules": {
                "all_passed": rules_passed,
                "failed_count": failed_count,
                "flags": flags_dict,
                "rules": policy_rules
            }
        }


# Global cached singleton instance
_cached_engine: Optional[CreditRiskInferenceEngine] = None


def get_inference_engine() -> CreditRiskInferenceEngine:
    global _cached_engine
    if _cached_engine is None:
        _cached_engine = CreditRiskInferenceEngine()
    return _cached_engine


if __name__ == "__main__":
    engine = get_inference_engine()
    test_applicant = {
        "SK_ID_CURR": 999001,
        "NAME_CONTRACT_TYPE": "Cash loans",
        "CODE_GENDER": "M",
        "AMT_INCOME_TOTAL": 180000.0,
        "AMT_CREDIT": 450000.0,
        "AMT_ANNUITY": 22500.0,
        "AMT_GOODS_PRICE": 400000.0,
        "NAME_INCOME_TYPE": "Working",
        "NAME_EDUCATION_TYPE": "Higher education",
        "NAME_FAMILY_STATUS": "Married",
        "DAYS_BIRTH": -14000,          # ~38.3 years old
        "DAYS_EMPLOYED": -1800,        # ~4.9 years tenure
        "EXT_SOURCE_1": 0.65,
        "EXT_SOURCE_2": 0.58,
        "EXT_SOURCE_3": 0.62,
        "BUREAU_TOTAL_OVERDUE": 0.0,
        "DEF_30_CNT_SOCIAL_CIRCLE": 0.0
    }
    result = engine.predict(test_applicant)
    print("\n" + "=" * 65)
    print("INFERENCE & UNDERWRITING DECISION")
    print("=" * 65)
    print(f"Risk Score : {result['risk_score']} / 100")
    print(f"Risk Band  : {result['risk_band']}")
    print(f"Decision   : {result['underwriting_decision']}")
    print(f"Rationale  : {result['decision_rationale']}")
    print("\nTop Contributing Factors:")
    for b in result["business_explanations"]:
        print(f"  • {b}")
    print(f"\nPolicy Check : {'PASSED' if result['policy_rules']['all_passed'] else 'FLAGGED'}")
    print("=" * 65 + "\n")
