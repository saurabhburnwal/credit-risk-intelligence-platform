"""
Machine Learning Training Pipeline for Credit Risk Intelligence Platform.
Trains on full 307,511 rows with class imbalance mitigation (scale_pos_weight).
Performs benchmark comparison: Logistic Regression Baseline vs LightGBM Champion.
Saves model bundle and metadata to models/.
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    roc_auc_score, average_precision_score, f1_score,
    precision_score, recall_score, brier_score_loss, confusion_matrix
)
from lightgbm import LGBMClassifier

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.loader import load_full_dataset
from src.data.preprocessor import CreditRiskPreprocessor
from src.utils.config import (
    MODEL_PATH, PREPROCESSOR_PATH, METADATA_PATH,
    THRESHOLD_LOW_RISK, THRESHOLD_MEDIUM_RISK
)
from src.utils.logger import logger


def calculate_ks_statistic(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Calculates Kolmogorov-Smirnov (KS) statistic, standard in banking credit risk."""
    df = pd.DataFrame({"target": y_true, "prob": y_prob})
    df = df.sort_values(by="prob", ascending=False)
    total_def = df["target"].sum()
    total_non_def = len(df) - total_def

    if total_def == 0 or total_non_def == 0:
        return 0.0

    df["cum_def"] = df["target"].cumsum() / total_def
    df["cum_non_def"] = (1 - df["target"]).cumsum() / total_non_def
    ks = np.max(np.abs(df["cum_def"] - df["cum_non_def"]))
    return float(ks * 100)


def optimize_threshold(y_true: np.ndarray, y_prob: np.ndarray, cost_fn: float = 5.0, cost_fp: float = 1.0) -> Tuple[float, float]:
    """
    Finds threshold minimizing credit loss: Cost = (cost_fn * FN) + (cost_fp * FP).
    Missing a defaulter (FN) is typically 5x more costly to a bank than rejecting a good applicant (FP).
    """
    best_thresh = 0.5
    min_cost = float("inf")

    for thresh in np.linspace(0.05, 0.95, 91):
        preds = (y_prob >= thresh).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, preds).ravel()
        cost = (cost_fn * fn) + (cost_fp * fp)
        if cost < min_cost:
            min_cost = cost
            best_thresh = float(thresh)

    return best_thresh, min_cost


def run_training_pipeline() -> Dict[str, Any]:
    logger.info("=" * 70)
    logger.info("COMMENCING FULL DATASET TRAINING PIPELINE (307,511 ROWS)")
    logger.info("=" * 70)

    start_time = time.time()
    df = load_full_dataset()

    y = df["TARGET"].astype(int)
    X = df.drop(columns=["TARGET"])

    logger.info(f"Target distribution: {y.value_counts().to_dict()} (Default Rate: {y.mean():.2%})")

    # Stratified 80/20 train/test split
    logger.info("Performing Stratified 80/20 Train/Test split...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    logger.info(f"Train set: {len(X_train):,} samples | Test set: {len(X_test):,} samples")

    # Fit preprocessor on train set
    preprocessor = CreditRiskPreprocessor()
    preprocessor.fit(X_train, y_train)
    X_train_proc = preprocessor.transform(X_train)
    X_test_proc = preprocessor.transform(X_test)
    preprocessor.save(PREPROCESSOR_PATH)

    feature_names = preprocessor.feature_names
    logger.info(f"Engineered and selected {len(feature_names)} features for training.")

    # --------------------------------------------------------------------------
    # 1. Baseline Model: Logistic Regression with Balanced Class Weights
    # --------------------------------------------------------------------------
    logger.info("Training Baseline Model: Logistic Regression (class_weight='balanced')...")
    lr_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(class_weight="balanced", max_iter=300, random_state=42, n_jobs=-1))
    ])
    lr_pipeline.fit(X_train_proc, y_train)
    lr_test_probs = lr_pipeline.predict_proba(X_test_proc)[:, 1]

    lr_roc_auc = roc_auc_score(y_test, lr_test_probs)
    lr_pr_auc = average_precision_score(y_test, lr_test_probs)
    lr_ks = calculate_ks_statistic(y_test.values, lr_test_probs)
    logger.info(f"[Baseline - Logistic Regression] ROC-AUC: {lr_roc_auc:.4f} | PR-AUC: {lr_pr_auc:.4f} | KS: {lr_ks:.2f}%")

    # --------------------------------------------------------------------------
    # 2. Champion Model: LightGBM Classifier with scale_pos_weight
    # --------------------------------------------------------------------------
    class_ratio = float((y_train == 0).sum() / (y_train == 1).sum())
    logger.info(f"Training Champion Model: LightGBM (scale_pos_weight={class_ratio:.2f})...")

    lgbm = LGBMClassifier(
        n_estimators=350,
        learning_rate=0.03,
        num_leaves=31,
        max_depth=6,
        scale_pos_weight=class_ratio,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )
    lgbm.fit(
        X_train_proc, y_train,
        eval_set=[(X_test_proc, y_test)],
        eval_metric="auc"
    )

    lgbm_test_probs = lgbm.predict_proba(X_test_proc)[:, 1]
    lgbm_roc_auc = roc_auc_score(y_test, lgbm_test_probs)
    lgbm_pr_auc = average_precision_score(y_test, lgbm_test_probs)
    lgbm_ks = calculate_ks_statistic(y_test.values, lgbm_test_probs)
    brier = brier_score_loss(y_test, lgbm_test_probs)

    optimal_thresh, min_cost = optimize_threshold(y_test.values, lgbm_test_probs)
    opt_preds = (lgbm_test_probs >= optimal_thresh).astype(int)
    f1 = f1_score(y_test, opt_preds)
    precision = precision_score(y_test, opt_preds)
    recall = recall_score(y_test, opt_preds)
    cm = confusion_matrix(y_test, opt_preds).tolist()

    logger.info("=" * 70)
    logger.info(f"[Champion - LightGBM] ROC-AUC  : {lgbm_roc_auc:.4f} (Baseline: {lr_roc_auc:.4f})")
    logger.info(f"[Champion - LightGBM] PR-AUC   : {lgbm_pr_auc:.4f} (Baseline: {lr_pr_auc:.4f})")
    logger.info(f"[Champion - LightGBM] KS Stat  : {lgbm_ks:.2f}% (Baseline: {lr_ks:.2f}%)")
    logger.info(f"[Champion - LightGBM] Brier    : {brier:.4f}")
    logger.info(f"[Champion - LightGBM] Opt Thresh: {optimal_thresh:.3f} | Recall: {recall:.2%} | Precision: {precision:.2%}")
    logger.info("=" * 70)

    # Feature importances
    importances = lgbm.feature_importances_
    feat_imp = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
    top_features = [{"feature": f, "importance": int(imp)} for f, imp in feat_imp[:20]]

    # Save champion model bundle
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(lgbm, MODEL_PATH)
    logger.info(f"Champion LightGBM model saved to {MODEL_PATH}")

    # Save comprehensive metadata
    elapsed = time.time() - start_time
    metadata = {
        "model_type": "LightGBM Classifier",
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "features_count": len(feature_names),
        "features": feature_names,
        "class_imbalance_ratio": round(class_ratio, 2),
        "training_time_seconds": round(elapsed, 2),
        "benchmarks": {
            "logistic_regression": {
                "roc_auc": round(lr_roc_auc, 4),
                "pr_auc": round(lr_pr_auc, 4),
                "ks_statistic_pct": round(lr_ks, 2)
            },
            "lightgbm_champion": {
                "roc_auc": round(lgbm_roc_auc, 4),
                "pr_auc": round(lgbm_pr_auc, 4),
                "ks_statistic_pct": round(lgbm_ks, 2),
                "brier_score": round(brier, 4),
                "optimal_threshold": round(optimal_thresh, 3),
                "f1_score": round(f1, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "confusion_matrix": cm
            }
        },
        "risk_bands": {
            "low_risk": {"max_prob": THRESHOLD_LOW_RISK, "action": "Fast-Track Approve"},
            "medium_risk": {"min_prob": THRESHOLD_LOW_RISK, "max_prob": THRESHOLD_MEDIUM_RISK, "action": "Manual Review"},
            "high_risk": {"min_prob": THRESHOLD_MEDIUM_RISK, "action": "Strict Underwriting / Decline"}
        },
        "top_features": top_features
    }

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Metadata and benchmark reports saved to {METADATA_PATH}")

    return metadata


if __name__ == "__main__":
    run_training_pipeline()
