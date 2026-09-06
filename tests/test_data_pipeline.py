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
