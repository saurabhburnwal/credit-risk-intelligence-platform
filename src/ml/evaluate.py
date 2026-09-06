"""
Evaluation and diagnostic reporting module for Credit Risk Intelligence Platform.
Generates ROC Curves, Precision-Recall Curves, KS Separation plots, and metric summaries.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any
import pandas as pd
import numpy as np
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, precision_recall_curve, roc_auc_score, average_precision_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import MODEL_PATH, PREPROCESSOR_PATH, METADATA_PATH
from src.utils.logger import logger

PLOTS_DIR = PROJECT_ROOT / "notebooks" / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def plot_performance_curves(y_true: np.ndarray, y_prob: np.ndarray):
    """Generates combined ROC and Precision-Recall Curves."""
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    roc_auc = roc_auc_score(y_true, y_prob)
    pr_auc = average_precision_score(y_true, y_prob)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

    # 1. ROC Curve
    ax1.plot(fpr, tpr, color="#1E3A8A", lw=2, label=f"LightGBM (ROC-AUC = {roc_auc:.4f})")
    ax1.plot([0, 1], [0, 1], color="gray", lw=1.5, linestyle="--", label="Random Chance (0.50)")
    ax1.set_xlim([0.0, 1.0])
    ax1.set_ylim([0.0, 1.05])
    ax1.set_xlabel("False Positive Rate (1 - Specificity)")
    ax1.set_ylabel("True Positive Rate (Sensitivity / Recall)")
    ax1.set_title("Receiver Operating Characteristic (ROC)", fontweight="bold")
    ax1.legend(loc="lower right")
    ax1.grid(True, alpha=0.3)

    # 2. Precision-Recall Curve
    random_pr = y_true.mean()
    ax2.plot(recall, precision, color="#DC2626", lw=2, label=f"LightGBM (PR-AUC = {pr_auc:.4f})")
    ax2.plot([0, 1], [random_pr, random_pr], color="gray", lw=1.5, linestyle="--", label=f"Random Baseline ({random_pr:.3f})")
    ax2.set_xlim([0.0, 1.0])
    ax2.set_ylim([0.0, 1.05])
    ax2.set_xlabel("Recall")
    ax2.set_ylabel("Precision")
    ax2.set_title("Precision-Recall (PR) Curve", fontweight="bold")
    ax2.legend(loc="upper right")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    curve_path = PLOTS_DIR / "model_performance_curves.png"
    plt.savefig(curve_path)
    plt.close()
    logger.info(f"Performance curves saved to {curve_path}")


def display_model_summary():
    """Reads saved metadata.json and displays audit table."""
    if not METADATA_PATH.exists():
        logger.error(f"No metadata found at {METADATA_PATH}. Train the model first via train.py.")
        return

    with open(METADATA_PATH) as f:
        meta = json.load(f)

    print("\n" + "=" * 70)
    print("MODEL PERFORMANCE & BENCHMARK AUDIT")
    print("=" * 70)
    print(f"Model Architecture  : {meta['model_type']}")
    print(f"Training Samples    : {meta['training_samples']:,}")
    print(f"Test Samples        : {meta['test_samples']:,}")
    print(f"Features Count      : {meta['features_count']}")
    print(f"Training Duration   : {meta['training_time_seconds']} seconds")
    print("-" * 70)
    print("BENCHMARK COMPARISON (TEST SET):")
    print(f"  Logistic Regression Baseline : ROC-AUC = {meta['benchmarks']['logistic_regression']['roc_auc']:.4f} | PR-AUC = {meta['benchmarks']['logistic_regression']['pr_auc']:.4f} | KS = {meta['benchmarks']['logistic_regression']['ks_statistic_pct']}%")
    print(f"  LightGBM Champion Model      : ROC-AUC = {meta['benchmarks']['lightgbm_champion']['roc_auc']:.4f} | PR-AUC = {meta['benchmarks']['lightgbm_champion']['pr_auc']:.4f} | KS = {meta['benchmarks']['lightgbm_champion']['ks_statistic_pct']}%")
    print("-" * 70)
    print("CHAMPION CALIBRATION & RISK METRICS:")
    print(f"  Brier Score Loss   : {meta['benchmarks']['lightgbm_champion']['brier_score']:.4f}")
    print(f"  Optimal Threshold  : {meta['benchmarks']['lightgbm_champion']['optimal_threshold']:.3f}")
    print(f"  Recall at Opt Cutoff: {meta['benchmarks']['lightgbm_champion']['recall']:.2%}")
    print(f"  Precision at Cutoff: {meta['benchmarks']['lightgbm_champion']['precision']:.2%}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    display_model_summary()
