"""
Production preprocessing and feature engineering pipeline for Credit Risk Intelligence.
Handles DAYS_EMPLOYED anomaly (365243 -> NaN + flag), calculates domain features,
and encodes categorical variables.
"""

import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np
import joblib
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import OrdinalEncoder

from src.utils.config import PREPROCESSOR_PATH
from src.utils.logger import logger


class CreditRiskPreprocessor(BaseEstimator, TransformerMixin):
    """
    Scikit-learn compatible transformer that:
      1. Corrects DAYS_EMPLOYED anomalies (365,243 -> NaN + boolean flag)
      2. Computes banking domain features (DTI, Payment Rate, Age, Bureau flags)
      3. Performs label/ordinal encoding for categorical features
      4. Selects and aligns feature columns for model training & inference
    """

    def __init__(self):
        self.categorical_cols: List[str] = [
            "NAME_CONTRACT_TYPE", "CODE_GENDER", "FLAG_OWN_CAR", "FLAG_OWN_REALTY",
            "NAME_TYPE_SUITE", "NAME_INCOME_TYPE", "NAME_EDUCATION_TYPE",
            "NAME_FAMILY_STATUS", "NAME_HOUSING_TYPE", "OCCUPATION_TYPE",
            "ORGANIZATION_TYPE", "FONDKAPREMONT_MODE", "HOUSETYPE_MODE",
            "WALLSMATERIAL_MODE", "EMERGENCYSTATE_MODE"
        ]
        self.numerical_cols: List[str] = []
        self.feature_names: List[str] = []
        self.cat_encoder: Optional[OrdinalEncoder] = None
        self.medians: Dict[str, float] = {}
        self.is_fitted: bool = False

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies banking domain feature transformations and handles data anomalies."""
        X = df.copy()

        # Handle 365,243 day anomaly (pensioner/unemployed placeholder in Home Credit dataset)
        if "DAYS_EMPLOYED" in X.columns:
            X["DAYS_EMPLOYED_ANOM"] = (X["DAYS_EMPLOYED"] == 365243).astype(int)
            X["DAYS_EMPLOYED"] = X["DAYS_EMPLOYED"].replace({365243: np.nan})
            X["EMPLOYED_YEARS"] = -X["DAYS_EMPLOYED"] / 365.25
        else:
            X["DAYS_EMPLOYED_ANOM"] = 0
            X["EMPLOYED_YEARS"] = np.nan

        # Age in Years
        if "DAYS_BIRTH" in X.columns:
            X["AGE_YEARS"] = -X["DAYS_BIRTH"] / 365.25

        # Key Banking Ratios (safe Series alignment)
        income = X["AMT_INCOME_TOTAL"] if "AMT_INCOME_TOTAL" in X.columns else pd.Series(1.0, index=X.index)
        credit = X["AMT_CREDIT"] if "AMT_CREDIT" in X.columns else pd.Series(1.0, index=X.index)
        annuity = X["AMT_ANNUITY"] if "AMT_ANNUITY" in X.columns else pd.Series(0.0, index=X.index)
        goods_price = X["AMT_GOODS_PRICE"] if "AMT_GOODS_PRICE" in X.columns else credit

        X["DEBT_TO_INCOME"] = annuity / (income + 1.0)
        X["PAYMENT_RATE"] = annuity / (credit + 1.0)
        X["CREDIT_TO_INCOME"] = credit / (income + 1.0)
        X["GOODS_PRICE_TO_CREDIT"] = goods_price / (credit + 1.0)

        # External Credit Bureau Score Aggregations
        ext_cols = [c for c in ["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"] if c in X.columns]
        if ext_cols:
            X["EXT_SOURCES_MEAN"] = X[ext_cols].mean(axis=1)
            X["EXT_SOURCES_MIN"] = X[ext_cols].min(axis=1)
            X["EXT_SOURCES_MAX"] = X[ext_cols].max(axis=1)
            X["EXT_SOURCES_STD"] = X[ext_cols].std(axis=1).fillna(0)
        else:
            X["EXT_SOURCES_MEAN"] = np.nan
            X["EXT_SOURCES_MIN"] = np.nan
            X["EXT_SOURCES_MAX"] = np.nan
            X["EXT_SOURCES_STD"] = 0.0

        # Delinquency and Risk Indicator Flags (robust Series handling)
        bureau_overdue = (X["BUREAU_TOTAL_OVERDUE"] > 0) if "BUREAU_TOTAL_OVERDUE" in X.columns else pd.Series(False, index=X.index)
        social_def30 = (X["DEF_30_CNT_SOCIAL_CIRCLE"] > 0) if "DEF_30_CNT_SOCIAL_CIRCLE" in X.columns else pd.Series(False, index=X.index)
        X["DELINQUENCY_FLAG"] = (bureau_overdue | social_def30).astype(int)

        # High Debt Burden Flag (Credit Policy Rule)
        X["FLAG_HIGH_DTI"] = (X["DEBT_TO_INCOME"] > 0.40).astype(int)

        return X

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None):
        """Fits encoders and computes medians on the training dataset."""
        logger.info("Fitting CreditRiskPreprocessor on training data...")
        engineered = self._engineer_features(X)

        # Identify existing categoricals
        self.active_cat_cols = [c for c in self.categorical_cols if c in engineered.columns]
        
        # Fit OrdinalEncoder for categoricals (handles unknown categories gracefully)
        self.cat_encoder = OrdinalEncoder(
            handle_unknown="use_encoded_value",
            unknown_value=-1,
            encoded_missing_value=-1
        )
        if self.active_cat_cols:
            cat_df = engineered[self.active_cat_cols].astype(str).fillna("MISSING")
            self.cat_encoder.fit(cat_df)

        # Identify numerical features (exclude IDs and Target)
        ignore_cols = {"SK_ID_CURR", "TARGET", "index"} | set(self.active_cat_cols)
        self.numerical_cols = [c for c in engineered.columns if c not in ignore_cols and pd.api.types.is_numeric_dtype(engineered[c])]

        # Compute numerical medians for fallback/imputation
        for col in self.numerical_cols:
            self.medians[col] = float(engineered[col].median(skipna=True))

        self.feature_names = self.numerical_cols + self.active_cat_cols
        self.is_fitted = True
        logger.info(f"Preprocessor fitted with {len(self.feature_names)} features ({len(self.numerical_cols)} numerical, {len(self.active_cat_cols)} categorical).")
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transforms raw input data into model-ready features."""
        if not self.is_fitted:
            raise RuntimeError("CreditRiskPreprocessor must be fitted before calling transform().")

        engineered = self._engineer_features(X)
        data_dict = {}

        # Copy numerical columns
        for col in self.numerical_cols:
            if col in engineered.columns:
                data_dict[col] = engineered[col].astype(float)
            else:
                data_dict[col] = pd.Series(self.medians.get(col, 0.0), index=engineered.index, dtype=float)

        # Encode categorical columns
        if self.active_cat_cols and self.cat_encoder is not None:
            cat_df = pd.DataFrame(index=engineered.index)
            for c in self.active_cat_cols:
                if c in engineered.columns:
                    cat_df[c] = engineered[c].astype(str).fillna("MISSING")
                else:
                    cat_df[c] = "MISSING"
            encoded_cats = self.cat_encoder.transform(cat_df)
            for idx, c in enumerate(self.active_cat_cols):
                data_dict[c] = encoded_cats[:, idx]

        out_df = pd.DataFrame(data_dict, index=engineered.index)
        # Re-order columns strictly
        out_df = out_df[self.feature_names]
        return out_df

    def save(self, file_path: Optional[Path] = None):
        """Saves preprocessor pipeline to disk."""
        path = file_path or PREPROCESSOR_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        logger.info(f"Preprocessor successfully saved to {path}.")

    @classmethod
    def load(cls, file_path: Optional[Path] = None) -> "CreditRiskPreprocessor":
        """Loads preprocessor pipeline from disk."""
        path = file_path or PREPROCESSOR_PATH
        if not path.exists():
            raise FileNotFoundError(f"Preprocessor artifact not found at {path}.")
        return joblib.load(path)
