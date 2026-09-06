"""Tests for data loading, multi-table joins, and feature engineering."""
import pytest
import pandas as pd
import numpy as np
from src.data.preprocessor import CreditRiskPreprocessor


def test_preprocessor_anomaly_handling():
    prep = CreditRiskPreprocessor()
    test_df = pd.DataFrame({
        "DAYS_EMPLOYED": [365243, -1500, -365],
        "DAYS_BIRTH": [-12000, -15000, -9000],
        "AMT_INCOME_TOTAL": [150000.0, 200000.0, 100000.0],
        "AMT_CREDIT": [450000.0, 600000.0, 300000.0],
        "AMT_ANNUITY": [22500.0, 30000.0, 15000.0],
        "AMT_GOODS_PRICE": [400000.0, 550000.0, 280000.0],
        "NAME_CONTRACT_TYPE": ["Cash loans", "Cash loans", "Revolving loans"]
    })

    prep.fit(test_df)
    transformed = prep.transform(test_df)

    # DAYS_EMPLOYED anomaly test
    assert "DAYS_EMPLOYED_ANOM" in prep.feature_names
    assert "EMPLOYED_YEARS" in prep.feature_names
    assert "DEBT_TO_INCOME" in prep.feature_names
    assert "PAYMENT_RATE" in prep.feature_names

    # Check engineered outputs
    assert len(transformed) == 3

    # Verify DAYS_EMPLOYED anomaly was converted to NaN and flag set to 1
    assert transformed["DAYS_EMPLOYED_ANOM"].iloc[0] == 1
    assert np.isnan(transformed["DAYS_EMPLOYED"].iloc[0])
    assert np.isnan(transformed["EMPLOYED_YEARS"].iloc[0])

    # Verify normal employment row preserves negative days and flag set to 0
    assert transformed["DAYS_EMPLOYED_ANOM"].iloc[1] == 0
    assert transformed["DAYS_EMPLOYED"].iloc[1] == -1500.0
    assert transformed["EMPLOYED_YEARS"].iloc[1] == pytest.approx(1500.0 / 365.25, 0.01)

    # Check that DTI and Payment Rate are non-null and valid
    assert not transformed["DEBT_TO_INCOME"].isnull().any()
    assert not transformed["PAYMENT_RATE"].isnull().any()


def test_real_data_loading_and_columns():
    """Verify that real CSV files in data/ exist, have proper headers, and can be read."""
    from src.utils.config import DATA_DIR
    import pandas as pd

    train_path = DATA_DIR / "application_train.csv"
    bureau_path = DATA_DIR / "bureau.csv"
    prev_path = DATA_DIR / "previous_application.csv"

    assert train_path.exists(), f"Missing real data file: {train_path}"
    assert bureau_path.exists(), f"Missing real data file: {bureau_path}"
    assert prev_path.exists(), f"Missing real data file: {prev_path}"

    # Load 100 rows directly from the physical disk files
    df_train_sample = pd.read_csv(train_path, nrows=100)
    assert len(df_train_sample) == 100
    assert "TARGET" in df_train_sample.columns
    assert "SK_ID_CURR" in df_train_sample.columns
    assert "AMT_CREDIT" in df_train_sample.columns

    df_bureau_sample = pd.read_csv(bureau_path, nrows=100)
    assert len(df_bureau_sample) == 100
    assert "SK_ID_CURR" in df_bureau_sample.columns

    df_prev_sample = pd.read_csv(prev_path, nrows=100)
    assert len(df_prev_sample) == 100
    assert "SK_ID_CURR" in df_prev_sample.columns

    # Pass actual sample through preprocessor
    prep = CreditRiskPreprocessor()
    prep.fit(df_train_sample)
    trans = prep.transform(df_train_sample)
    assert len(trans) == 100
    assert "DEBT_TO_INCOME" in trans.columns
    assert "PAYMENT_RATE" in trans.columns
