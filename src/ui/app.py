"""
Flask Application and REST API for AI-Powered Credit Risk Intelligence Platform.
Demonstrates end-to-end workflow: EDA insights, real-time risk scoring,
SHAP explainability, policy rules engine, and conversational Talk-to-Data assistant.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any
from flask import Flask, render_template, request, jsonify, send_from_directory

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import FLASK_PORT, FLASK_DEBUG, SECRET_KEY, METADATA_PATH, DB_PATH, ensure_sqlite_db
from src.utils.logger import logger
from src.ml.predict import get_inference_engine
from src.talk_to_data.nl_to_sql import get_talk_to_data_agent

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "src/ui/templates"),
    static_folder=str(PROJECT_ROOT / "src/ui/static")
)
app.config["SECRET_KEY"] = SECRET_KEY

# Ensure SQLite analytics database is built/available before initializing talk-to-data
ensure_sqlite_db()

# Initialize singletons
logger.info("Initializing ML Inference Engine for UI...")
inference_engine = get_inference_engine()

logger.info("Initializing Talk-to-Data Agent for UI...")
talk_to_data_agent = get_talk_to_data_agent()


@app.route("/")
def index():
    """Renders the main multi-section executive platform."""
    return render_template("index.html")


@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health_check():
    """Healthcheck endpoint for Docker and orchestration."""
    return jsonify({
        "status": "healthy",
        "service": "credit_risk_platform",
        "db_exists": DB_PATH.exists(),
        "model_loaded": inference_engine.model is not None,
        "preprocessor_loaded": inference_engine.preprocessor is not None
    })


@app.route("/api/eda/insights", methods=["GET"])
def get_eda_insights():
    """Returns metadata and portfolio overview metrics."""
    metadata = {}
    if METADATA_PATH.exists():
        with open(METADATA_PATH) as f:
            metadata = json.load(f)

    return jsonify({
        "portfolio": {
            "total_applications": 307511,
            "overall_default_rate_pct": 8.07,
            "bureau_records": 305811,
            "previous_applications": 338857,
            "class_imbalance_ratio": "11.39 to 1"
        },
        "model_benchmarks": metadata.get("benchmarks", {}),
        "top_features": metadata.get("top_features", []),
        "insights_list": [
            {
                "id": 1,
                "title": "External Bureau Score Gradient",
                "summary": "External credit bureau composite scores create a >10x default rate spread between Critical (<0.35) and Prime (>0.60) tiers.",
                "image": "/static/plots/insight1_ext_scores.png"
            },
            {
                "id": 2,
                "title": "Debt-to-Income & Payment Stress Zones",
                "summary": "Applicants with Debt-to-Income ratios above 40% experience severe default acceleration (12.4% vs 6.1% for healthy DTI).",
                "image": "/static/plots/insight2_debt_stress.png"
            },
            {
                "id": 3,
                "title": "Age Demographics & Career Tenure",
                "summary": "Young borrowers under 25 default at nearly 3x the rate of established senior applicants (>50 years).",
                "image": "/static/plots/insight3_age_employment.png"
            },
            {
                "id": 4,
                "title": "Education Level Risk Profiling",
                "summary": "Academic degree holders maintain an exceptional 1.8% default rate versus 10.9% for lower secondary education applicants.",
                "image": "/static/plots/insight4_education_income.png"
            },
            {
                "id": 5,
                "title": "Past Bureau Delinquency Ripple Effect",
                "summary": "Any active overdue debt with external lenders doubles current default hazard (16.2% vs 8.0%).",
                "image": "/static/plots/insight5_bureau_delinquency.png"
            }
        ]
    })


@app.route("/static/plots/<path:filename>")
def serve_plot(filename):
    """Serves high-resolution EDA charts from notebooks/plots/."""
    plots_dir = PROJECT_ROOT / "notebooks/plots"
    return send_from_directory(plots_dir, filename)


@app.route("/api/underwriting/score", methods=["POST"])
def score_applicant():
    """Scores applicant attributes, returning calibrated probability, SHAP factors, and policy rules."""
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No applicant data provided."}), 400

        # Transform inputs into standard applicant format
        applicant_payload = {
            "SK_ID_CURR": int(data.get("SK_ID_CURR", 100001)),
            "NAME_CONTRACT_TYPE": str(data.get("NAME_CONTRACT_TYPE", "Cash loans")),
            "CODE_GENDER": str(data.get("CODE_GENDER", "M")),
            "FLAG_OWN_CAR": str(data.get("FLAG_OWN_CAR", "N")),
            "FLAG_OWN_REALTY": str(data.get("FLAG_OWN_REALTY", "Y")),
            "CNT_CHILDREN": int(data.get("CNT_CHILDREN", 0)),
            "AMT_INCOME_TOTAL": float(data.get("AMT_INCOME_TOTAL", 150000.0)),
            "AMT_CREDIT": float(data.get("AMT_CREDIT", 500000.0)),
            "AMT_ANNUITY": float(data.get("AMT_ANNUITY", 25000.0)),
            "AMT_GOODS_PRICE": float(data.get("AMT_GOODS_PRICE", 450000.0)),
            "NAME_INCOME_TYPE": str(data.get("NAME_INCOME_TYPE", "Working")),
            "NAME_EDUCATION_TYPE": str(data.get("NAME_EDUCATION_TYPE", "Higher education")),
            "NAME_FAMILY_STATUS": str(data.get("NAME_FAMILY_STATUS", "Married")),
            "NAME_HOUSING_TYPE": str(data.get("NAME_HOUSING_TYPE", "House / apartment")),
            "DAYS_BIRTH": -int(float(data.get("AGE_YEARS", 35.0)) * 365.25),
            "DAYS_EMPLOYED": -int(float(data.get("EMPLOYED_YEARS", 5.0)) * 365.25),
            "EXT_SOURCE_1": float(data.get("EXT_SOURCE_1", 0.5)),
            "EXT_SOURCE_2": float(data.get("EXT_SOURCE_2", 0.5)),
            "EXT_SOURCE_3": float(data.get("EXT_SOURCE_3", 0.5)),
            "BUREAU_TOTAL_OVERDUE": float(data.get("BUREAU_TOTAL_OVERDUE", 0.0)),
            "DEF_30_CNT_SOCIAL_CIRCLE": float(data.get("DEF_30_CNT_SOCIAL_CIRCLE", 0.0))
        }

        result = inference_engine.predict(applicant_payload)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Underwriting scoring error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Scoring failure: {str(e)}"}), 500


@app.route("/api/talk-to-data/chat", methods=["POST"])
def talk_to_data_chat():
    """Processes natural language questions into validated SQL and plain-English insights."""
    try:
        data = request.get_json(force=True)
        question = (data.get("question") or data.get("query") or "").strip()
        if not question:
            return jsonify({"error": "Empty question provided."}), 400

        result = talk_to_data_agent.ask(question)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Talk-to-data error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Talk-to-Data agent failure: {str(e)}"}), 500


def run_app():
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG)


if __name__ == "__main__":
    run_app()
