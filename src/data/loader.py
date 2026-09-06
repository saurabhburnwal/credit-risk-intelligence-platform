"""
Data loading and multi-table joining pipeline for Credit Risk Intelligence Platform.
Loads full 307,511 rows, aggregates bureau.csv & previous_application.csv,
and seeds the SQLite database for Talk-to-Data.
"""

import sys
import os
import sqlite3
from pathlib import Path
from typing import Tuple, Optional
import pandas as pd
import numpy as np

from src.utils.config import DATA_DIR, DB_PATH
from src.utils.logger import logger


def load_raw_applications(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Loads the complete application_train.csv dataset (307,511 rows)."""
    dir_path = data_dir or DATA_DIR
    train_file = dir_path / "application_train.csv"
    if not train_file.exists():
        raise FileNotFoundError(f"application_train.csv not found at {train_file}")

    logger.info(f"Loading raw applications from {train_file}...")
    df = pd.read_csv(train_file)
    logger.info(f"Loaded {len(df):,} applicant records with {len(df.columns)} features.")
    return df


def aggregate_bureau(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Aggregates bureau.csv records by SK_ID_CURR:
      - BUREAU_LOAN_COUNT: Total credit bureau accounts
      - BUREAU_ACTIVE_COUNT: Number of currently active credit lines
      - BUREAU_TOTAL_OVERDUE: Total overdue amount across all credits
      - BUREAU_MAX_OVERDUE_DAYS: Maximum days past due
      - BUREAU_TOTAL_DEBT: Total outstanding debt
    """
    dir_path = data_dir or DATA_DIR
    bureau_file = dir_path / "bureau.csv"
    if not bureau_file.exists():
        logger.warning(f"bureau.csv not found at {bureau_file}. Proceeding without bureau aggregations.")
        return pd.DataFrame(columns=["SK_ID_CURR"])

    logger.info(f"Aggregating credit bureau data from {bureau_file}...")
    usecols = [
        "SK_ID_CURR", "CREDIT_ACTIVE", "CREDIT_DAY_OVERDUE",
        "AMT_CREDIT_SUM_DEBT", "AMT_CREDIT_SUM_OVERDUE"
    ]
    bureau = pd.read_csv(bureau_file, usecols=usecols)

    bureau["IS_ACTIVE"] = (bureau["CREDIT_ACTIVE"] == "Active").astype(int)
    bureau["AMT_CREDIT_SUM_DEBT"] = bureau["AMT_CREDIT_SUM_DEBT"].fillna(0)
    bureau["AMT_CREDIT_SUM_OVERDUE"] = bureau["AMT_CREDIT_SUM_OVERDUE"].fillna(0)
    bureau["CREDIT_DAY_OVERDUE"] = bureau["CREDIT_DAY_OVERDUE"].fillna(0)

    agg = bureau.groupby("SK_ID_CURR").agg(
        BUREAU_LOAN_COUNT=("CREDIT_ACTIVE", "count"),
        BUREAU_ACTIVE_COUNT=("IS_ACTIVE", "sum"),
        BUREAU_TOTAL_OVERDUE=("AMT_CREDIT_SUM_OVERDUE", "sum"),
        BUREAU_MAX_OVERDUE_DAYS=("CREDIT_DAY_OVERDUE", "max"),
        BUREAU_TOTAL_DEBT=("AMT_CREDIT_SUM_DEBT", "sum"),
    ).reset_index()

    logger.info(f"Aggregated bureau statistics for {len(agg):,} unique clients.")
    return agg


def aggregate_previous_applications(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Aggregates previous_application.csv records by SK_ID_CURR:
      - PREV_APP_COUNT: Total prior loan applications
      - PREV_REFUSED_COUNT: Prior refused applications
      - PREV_APPROVED_COUNT: Prior approved applications
      - PREV_REFUSAL_RATE: Refused / Total prior applications
      - PREV_AVG_CREDIT: Average prior credit amount
    """
    dir_path = data_dir or DATA_DIR
    prev_file = dir_path / "previous_application.csv"
    if not prev_file.exists():
        logger.warning(f"previous_application.csv not found at {prev_file}. Proceeding without previous app aggregations.")
        return pd.DataFrame(columns=["SK_ID_CURR"])

    logger.info(f"Aggregating previous applications data from {prev_file}...")
    usecols = ["SK_ID_CURR", "NAME_CONTRACT_STATUS", "AMT_CREDIT"]
    prev = pd.read_csv(prev_file, usecols=usecols)

    prev["IS_REFUSED"] = (prev["NAME_CONTRACT_STATUS"] == "Refused").astype(int)
    prev["IS_APPROVED"] = (prev["NAME_CONTRACT_STATUS"] == "Approved").astype(int)
    prev["AMT_CREDIT"] = prev["AMT_CREDIT"].fillna(0)

    agg = prev.groupby("SK_ID_CURR").agg(
        PREV_APP_COUNT=("NAME_CONTRACT_STATUS", "count"),
        PREV_REFUSED_COUNT=("IS_REFUSED", "sum"),
        PREV_APPROVED_COUNT=("IS_APPROVED", "sum"),
        PREV_AVG_CREDIT=("AMT_CREDIT", "mean"),
    ).reset_index()

    agg["PREV_REFUSAL_RATE"] = agg["PREV_REFUSED_COUNT"] / (agg["PREV_APP_COUNT"] + 1e-5)
    logger.info(f"Aggregated previous application statistics for {len(agg):,} unique clients.")
    return agg


def load_full_dataset(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Loads full application_train.csv and joins aggregated bureau and previous applications tables.
    Returns master merged DataFrame.
    """
    df = load_raw_applications(data_dir)
    bureau_agg = aggregate_bureau(data_dir)
    prev_agg = aggregate_previous_applications(data_dir)

    logger.info("Merging application records with multi-table aggregations...")
    if len(bureau_agg) > 0 and "SK_ID_CURR" in bureau_agg.columns:
        df = df.merge(bureau_agg, on="SK_ID_CURR", how="left")
        df["BUREAU_LOAN_COUNT"] = df["BUREAU_LOAN_COUNT"].fillna(0)
        df["BUREAU_ACTIVE_COUNT"] = df["BUREAU_ACTIVE_COUNT"].fillna(0)
        df["BUREAU_TOTAL_OVERDUE"] = df["BUREAU_TOTAL_OVERDUE"].fillna(0)
        df["BUREAU_MAX_OVERDUE_DAYS"] = df["BUREAU_MAX_OVERDUE_DAYS"].fillna(0)
        df["BUREAU_TOTAL_DEBT"] = df["BUREAU_TOTAL_DEBT"].fillna(0)

    if len(prev_agg) > 0 and "SK_ID_CURR" in prev_agg.columns:
        df = df.merge(prev_agg, on="SK_ID_CURR", how="left")
        df["PREV_APP_COUNT"] = df["PREV_APP_COUNT"].fillna(0)
        df["PREV_REFUSED_COUNT"] = df["PREV_REFUSED_COUNT"].fillna(0)
        df["PREV_APPROVED_COUNT"] = df["PREV_APPROVED_COUNT"].fillna(0)
        df["PREV_REFUSAL_RATE"] = df["PREV_REFUSAL_RATE"].fillna(0)
        df["PREV_AVG_CREDIT"] = df["PREV_AVG_CREDIT"].fillna(0)

    logger.info(f"Final merged dataset: {df.shape[0]:,} rows x {df.shape[1]:,} columns.")
    return df


def build_sqlite_database(data_dir: Optional[Path] = None, db_path: Optional[Path] = None):
    """
    Initializes and seeds the SQLite database with indexed tables for Talk-to-Data querying.
    """
    target_db = db_path or DB_PATH
    target_db.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Building SQLite database at {target_db}...")

    df_apps = load_raw_applications(data_dir)
    bureau_agg = aggregate_bureau(data_dir)
    prev_agg = aggregate_previous_applications(data_dir)

    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()

    # Core table selection to ensure high query performance
    core_cols = [
        "SK_ID_CURR", "TARGET", "NAME_CONTRACT_TYPE", "CODE_GENDER",
        "FLAG_OWN_CAR", "FLAG_OWN_REALTY", "CNT_CHILDREN", "AMT_INCOME_TOTAL",
        "AMT_CREDIT", "AMT_ANNUITY", "AMT_GOODS_PRICE", "NAME_INCOME_TYPE",
        "NAME_EDUCATION_TYPE", "NAME_FAMILY_STATUS", "NAME_HOUSING_TYPE",
        "DAYS_BIRTH", "DAYS_EMPLOYED", "OCCUPATION_TYPE", "REGION_RATING_CLIENT",
        "EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3",
        "DEF_30_CNT_SOCIAL_CIRCLE", "DEF_60_CNT_SOCIAL_CIRCLE",
        "AMT_REQ_CREDIT_BUREAU_YEAR"
    ]
    avail_cols = [c for c in core_cols if c in df_apps.columns]
    apps_subset = df_apps[avail_cols].copy()

    # Derived easy-to-query columns
    apps_subset["AGE_YEARS"] = (-apps_subset["DAYS_BIRTH"] / 365.25).round(1)
    apps_subset["EMPLOYED_YEARS"] = np.where(
        apps_subset["DAYS_EMPLOYED"] > 0, np.nan, (-apps_subset["DAYS_EMPLOYED"] / 365.25).round(1)
    )
    apps_subset["DEBT_TO_INCOME"] = (apps_subset["AMT_ANNUITY"] / (apps_subset["AMT_INCOME_TOTAL"] + 1.0)).round(4)
    apps_subset["PAYMENT_RATE"] = (apps_subset["AMT_ANNUITY"] / (apps_subset["AMT_CREDIT"] + 1.0)).round(4)

    logger.info("Writing 'applications' table to SQLite...")
    apps_subset.to_sql("applications", conn, if_exists="replace", index=False)

    logger.info("Writing 'bureau_summary' table to SQLite...")
    bureau_agg.to_sql("bureau_summary", conn, if_exists="replace", index=False)

    logger.info("Writing 'previous_applications_summary' table to SQLite...")
    prev_agg.to_sql("previous_applications_summary", conn, if_exists="replace", index=False)

    logger.info("Creating indexes for fast querying...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_id ON applications(SK_ID_CURR);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_target ON applications(TARGET);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_edu ON applications(NAME_EDUCATION_TYPE);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_inc ON applications(NAME_INCOME_TYPE);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_gender ON applications(CODE_GENDER);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bureau_id ON bureau_summary(SK_ID_CURR);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prev_id ON previous_applications_summary(SK_ID_CURR);")

    conn.commit()
    conn.close()
    logger.info(f"SQLite database successfully built at {target_db} (Size: {target_db.stat().st_size / (1024*1024):.2f} MB).")


if __name__ == "__main__":
    if "--build-db" in sys.argv:
        build_sqlite_database()
    else:
        df = load_full_dataset()
        print(f"Dataset successfully loaded. Shape: {df.shape}")
