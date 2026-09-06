"""
Exploratory Data Analysis (EDA) Script for Credit Risk Intelligence Platform.
Generates portfolio statistics, missing value analyses, and the 5 key business insight charts.
Outputs charts directly to notebooks/plots/ for use in reports, presentations, and UI.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.loader import load_full_dataset
from src.utils.logger import logger

PLOTS_DIR = PROJECT_ROOT / "notebooks" / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# Styling configuration
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10
plt.rcParams["axes.titlesize"] = 12
plt.rcParams["axes.labelsize"] = 11

COLOR_PRIMARY = "#1E3A8A"   # Deep Banking Navy
COLOR_DANGER = "#DC2626"    # High Risk Crimson
COLOR_SUCCESS = "#059669"   # Prime Green
COLOR_ACCENT = "#F59E0B"    # Amber Warning


def generate_eda_report():
    logger.info("Starting comprehensive Exploratory Data Analysis on full dataset...")
    df = load_full_dataset()

    total_records = len(df)
    target_dist = df["TARGET"].value_counts()
    default_rate = df["TARGET"].mean()

    print("=" * 70)
    print("PORTFOLIO SUMMARY")
    print("=" * 70)
    print(f"Total Applicants Evaluated : {total_records:,}")
    print(f"Total Features (Master)    : {len(df.columns)}")
    print(f"Non-Default (Target=0)     : {target_dist.get(0, 0):,} ({1 - default_rate:.2%})")
    print(f"Defaulted (Target=1)       : {target_dist.get(1, 0):,} ({default_rate:.2%})")
    print(f"Class Imbalance Ratio      : {target_dist.get(0, 0) / target_dist.get(1, 1):.2f} to 1")
    print("=" * 70)

    # --------------------------------------------------------------------------
    # Chart 0: Target Class Imbalance
    # --------------------------------------------------------------------------
    logger.info("Generating Chart 0: Class Imbalance...")
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
    sns.countplot(
        x="TARGET", data=df, ax=ax,
        palette=[COLOR_PRIMARY, COLOR_DANGER]
    )
    ax.set_title("Loan Default Class Imbalance (Home Credit Portfolio)", fontweight="bold", pad=12)
    ax.set_xticklabels(["Non-Default (0) [91.93%]", "Defaulted (1) [8.07%]"])
    ax.set_xlabel("Applicant Outcome")
    ax.set_ylabel("Count of Loans")
    for p in ax.patches:
        height = p.get_height()
        ax.annotate(
            f"{int(height):,} ({height / total_records:.1%})",
            (p.get_x() + p.get_width() / 2., height / 2),
            ha='center', va='center', color='white', fontweight='bold', fontsize=11
        )
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "class_imbalance.png")
    plt.close()

    # --------------------------------------------------------------------------
    # Chart 0B: Missing Values Analysis
    # --------------------------------------------------------------------------
    logger.info("Generating Chart 0B: Missing Values Audit...")
    missing = df.isnull().sum()
    missing_pct = (missing / total_records) * 100
    missing_df = pd.DataFrame({"Missing_Count": missing, "Missing_Pct": missing_pct})
    missing_top15 = missing_df.sort_values(by="Missing_Pct", ascending=False).head(15)

    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    sns.barplot(
        x="Missing_Pct", y=missing_top15.index, data=missing_top15,
        ax=ax, palette="Blues_r"
    )
    ax.set_title("Top 15 Columns with Missing Data (Data Quality Audit)", fontweight="bold", pad=12)
    ax.set_xlabel("Missing Percentage (%)")
    ax.set_ylabel("Feature Name")
    for p in ax.patches:
        ax.annotate(
            f"{p.get_width():.1f}%",
            (p.get_width() + 1, p.get_y() + p.get_height() / 2.),
            ha='left', va='center', fontsize=9
        )
    ax.set_xlim(0, 100)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "missing_values.png")
    plt.close()

    # Derived working features for insights
    df["AGE_YEARS"] = -df["DAYS_BIRTH"] / 365.25
    df["EMPLOYED_CLEAN"] = df["DAYS_EMPLOYED"].replace({365243: np.nan})
    df["EMPLOYED_YEARS"] = -df["EMPLOYED_CLEAN"] / 365.25
    df["DEBT_TO_INCOME"] = df["AMT_ANNUITY"] / (df["AMT_INCOME_TOTAL"] + 1.0)
    df["PAYMENT_RATE"] = df["AMT_ANNUITY"] / (df["AMT_CREDIT"] + 1.0)
    ext_cols = [c for c in ["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"] if c in df.columns]
    df["EXT_SOURCES_MEAN"] = df[ext_cols].mean(axis=1)

    # --------------------------------------------------------------------------
    # BUSINESS INSIGHT 1: External Credit Bureau Score Power
    # --------------------------------------------------------------------------
    logger.info("Generating Business Insight 1: External Credit Scores vs Default...")
    df["EXT_SCORE_TIER"] = pd.cut(
        df["EXT_SOURCES_MEAN"],
        bins=[0.0, 0.30, 0.45, 0.60, 1.0],
        labels=["Critical (<0.30)", "Subprime (0.30-0.45)", "Prime (0.45-0.60)", "Super-Prime (>0.60)"]
    )
    insight1 = df.groupby("EXT_SCORE_TIER", observed=True)["TARGET"].agg(["count", "mean"]).reset_index()
    insight1["default_pct"] = insight1["mean"] * 100

    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=300)
    bars = sns.barplot(
        x="EXT_SCORE_TIER", y="default_pct", data=insight1,
        ax=ax, palette=[COLOR_DANGER, COLOR_ACCENT, "#3B82F6", COLOR_SUCCESS]
    )
    ax.set_title("Insight 1: External Bureau Score Gradient vs Default Hazard", fontweight="bold", pad=12)
    ax.set_xlabel("External Bureau Credit Tier")
    ax.set_ylabel("Default Rate (%)")
    for p, count in zip(ax.patches, insight1["count"]):
        h = p.get_height()
        ax.annotate(
            f"{h:.1f}%\n({count:,} loans)",
            (p.get_x() + p.get_width() / 2., h + 0.5),
            ha='center', va='bottom', fontsize=9, fontweight='bold'
        )
    ax.set_ylim(0, max(insight1["default_pct"]) * 1.25)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "insight1_ext_scores.png")
    plt.close()

    # --------------------------------------------------------------------------
    # BUSINESS INSIGHT 2: Debt-to-Income & Payment Rate Stress Zones
    # --------------------------------------------------------------------------
    logger.info("Generating Business Insight 2: Debt & Payment Stress Zones...")
    df["DTI_TIER"] = pd.cut(
        df["DEBT_TO_INCOME"],
        bins=[0.0, 0.15, 0.30, 0.45, 10.0],
        labels=["Low (<15%)", "Moderate (15-30%)", "Stressed (30-45%)", "Severe (>45%)"]
    )
    insight2 = df.groupby("DTI_TIER", observed=True)["TARGET"].agg(["count", "mean"]).reset_index()
    insight2["default_pct"] = insight2["mean"] * 100

    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=300)
    sns.barplot(
        x="DTI_TIER", y="default_pct", data=insight2,
        ax=ax, palette=["#60A5FA", "#3B82F6", COLOR_ACCENT, COLOR_DANGER]
    )
    ax.set_title("Insight 2: Debt-to-Income (DTI) Stress & Default Acceleration", fontweight="bold", pad=12)
    ax.set_xlabel("Debt-to-Income (Annuity / Annual Income)")
    ax.set_ylabel("Default Rate (%)")
    for p, count in zip(ax.patches, insight2["count"]):
        h = p.get_height()
        ax.annotate(
            f"{h:.1f}%\n({count:,})",
            (p.get_x() + p.get_width() / 2., h + 0.3),
            ha='center', va='bottom', fontsize=9, fontweight='bold'
        )
    ax.set_ylim(0, max(insight2["default_pct"]) * 1.25)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "insight2_debt_stress.png")
    plt.close()

    # --------------------------------------------------------------------------
    # BUSINESS INSIGHT 3: Age & Employment Tenure Stability
    # --------------------------------------------------------------------------
    logger.info("Generating Business Insight 3: Age & Employment Tenure...")
    df["AGE_GROUP"] = pd.cut(
        df["AGE_YEARS"],
        bins=[18, 25, 35, 50, 75],
        labels=["Young (<25)", "Early Career (25-35)", "Mature (35-50)", "Senior (50+)"]
    )
    insight3 = df.groupby("AGE_GROUP", observed=True)["TARGET"].agg(["count", "mean"]).reset_index()
    insight3["default_pct"] = insight3["mean"] * 100

    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=300)
    sns.barplot(
        x="AGE_GROUP", y="default_pct", data=insight3,
        ax=ax, palette=[COLOR_DANGER, COLOR_ACCENT, "#3B82F6", COLOR_SUCCESS]
    )
    ax.set_title("Insight 3: Age Demographics & Credit Risk Maturation", fontweight="bold", pad=12)
    ax.set_xlabel("Borrower Age Cohort")
    ax.set_ylabel("Default Rate (%)")
    for p, count in zip(ax.patches, insight3["count"]):
        h = p.get_height()
        ax.annotate(
            f"{h:.1f}%\n({count:,})",
            (p.get_x() + p.get_width() / 2., h + 0.3),
            ha='center', va='bottom', fontsize=9, fontweight='bold'
        )
    ax.set_ylim(0, max(insight3["default_pct"]) * 1.25)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "insight3_age_employment.png")
    plt.close()

    # --------------------------------------------------------------------------
    # BUSINESS INSIGHT 4: Education Level & Income Type Risk Profiling
    # --------------------------------------------------------------------------
    logger.info("Generating Business Insight 4: Education Level Risk Profiling...")
    insight4 = df.groupby("NAME_EDUCATION_TYPE")["TARGET"].agg(["count", "mean"]).reset_index()
    insight4 = insight4[insight4["count"] > 500].sort_values(by="mean", ascending=False)
    insight4["default_pct"] = insight4["mean"] * 100

    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=300)
    sns.barplot(
        x="default_pct", y="NAME_EDUCATION_TYPE", data=insight4,
        ax=ax, palette="Reds_r"
    )
    ax.set_title("Insight 4: Educational Attainment & Default Probability Spread", fontweight="bold", pad=12)
    ax.set_xlabel("Default Rate (%)")
    ax.set_ylabel("Education Level")
    for p, count in zip(ax.patches, insight4["count"]):
        w = p.get_width()
        ax.annotate(
            f" {w:.1f}% ({count:,} loans)",
            (w, p.get_y() + p.get_height() / 2.),
            ha='left', va='center', fontsize=9, fontweight='bold'
        )
    ax.set_xlim(0, max(insight4["default_pct"]) * 1.35)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "insight4_education_income.png")
    plt.close()

    # --------------------------------------------------------------------------
    # BUSINESS INSIGHT 5: Historical Bureau Delinquency Ripple Effect
    # --------------------------------------------------------------------------
    logger.info("Generating Business Insight 5: Bureau Overdue Delinquencies...")
    if "BUREAU_TOTAL_OVERDUE" in df.columns:
        df["HAS_BUREAU_OVERDUE"] = np.where(
            df["BUREAU_TOTAL_OVERDUE"] > 0, "Prior Delinquent (>0 Overdue)", "Clean Bureau (Zero Overdue)"
        )
        insight5 = df.groupby("HAS_BUREAU_OVERDUE")["TARGET"].agg(["count", "mean"]).reset_index()
        insight5["default_pct"] = insight5["mean"] * 100

        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
        sns.barplot(
            x="HAS_BUREAU_OVERDUE", y="default_pct", data=insight5,
            ax=ax, palette=[COLOR_DANGER, COLOR_SUCCESS]
        )
        ax.set_title("Insight 5: Past Bureau Delinquency as Direct Multiplier of Risk", fontweight="bold", pad=12)
        ax.set_xlabel("Credit Bureau History")
        ax.set_ylabel("Current Default Rate (%)")
        for p, count in zip(ax.patches, insight5["count"]):
            h = p.get_height()
            ax.annotate(
                f"{h:.1f}%\n({count:,} loans)",
                (p.get_x() + p.get_width() / 2., h / 2),
                ha='center', va='center', color='white', fontsize=11, fontweight='bold'
            )
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / "insight5_bureau_delinquency.png")
        plt.close()

    logger.info(f"All 7 EDA charts successfully saved to {PLOTS_DIR}!")


if __name__ == "__main__":
    generate_eda_report()
