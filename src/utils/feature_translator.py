"""
Feature Translation and Plain-English Interpretability Utility.
Maps raw and engineered model feature names into human-readable banking descriptions
and generates contextual adverse action / credit risk explanations for SHAP attributions.
"""

from typing import Optional, Dict

FEATURE_NAME_MAP: Dict[str, str] = {
    # External Scores & Engineered Aggregates
    "EXT_SOURCES_MEAN": "Composite External Credit Bureau Score",
    "EXT_SOURCES_MIN": "Worst External Credit Bureau Score",
    "EXT_SOURCES_MAX": "Best External Credit Bureau Score",
    "EXT_SOURCES_STD": "External Credit Bureau Score Dispersion",
    "EXT_SOURCE_1": "External Bureau Score 1 (Institutional)",
    "EXT_SOURCE_2": "External Bureau Score 2 (Alternative / Transactional)",
    "EXT_SOURCE_3": "External Bureau Score 3 (Telco / Utility Rating)",

    # Financial Ratios & Amounts
    "GOODS_PRICE_TO_CREDIT": "Goods Price to Loan Ratio (Collateral Margin)",
    "PAYMENT_RATE": "Loan Payment-to-Credit Ratio (Repayment Stress)",
    "DEBT_TO_INCOME": "Debt-to-Income Burden (Annuity to Total Income)",
    "AMT_CREDIT": "Total Credit Amount Applied For",
    "AMT_ANNUITY": "Loan Annuity (Monthly Installment)",
    "AMT_INCOME_TOTAL": "Total Annual Applicant Income",
    "AMT_GOODS_PRICE": "Goods Price Financed",

    # External Bureau History & Debt
    "BUREAU_TOTAL_OVERDUE": "External Bureau Past-Due Overdue Debt",
    "BUREAU_TOTAL_DEBT": "External Bureau Total Outstanding Debt",
    "BUREAU_MAX_OVERDUE_DAYS": "Maximum Days Past Due in Bureau History",
    "BUREAU_ACTIVE_LOANS": "Active Loan Facilities in Bureau Registry",

    # Prior Application History
    "PREV_AVG_CREDIT": "Average Prior Approved Credit Amount",
    "PREV_AVG_ANNUITY": "Average Prior Loan Annuity",
    "PREV_REFUSED_COUNT": "Count of Prior Refused Loan Applications",
    "PREV_APPROVED_COUNT": "Count of Prior Approved Loan Applications",

    # Demographics, Stability & Employment
    "AGE_YEARS": "Applicant Age (Years)",
    "DAYS_BIRTH": "Applicant Age Profile (Days Since Birth)",
    "EMPLOYED_YEARS": "Employment Tenure Duration (Years)",
    "DAYS_EMPLOYED": "Employment Duration (Days)",
    "DAYS_EMPLOYED_ANOM": "Pensioner / Employment Anomaly Indicator",
    "OWN_CAR_AGE": "Age of Applicant Vehicle (Years)",
    "NAME_EDUCATION_TYPE": "Educational Attainment Background",
    "CODE_GENDER": "Applicant Demographic Classification",
    "NAME_INCOME_TYPE": "Income / Employment Category",
    "NAME_CONTRACT_TYPE": "Contract Loan Type (Cash vs Revolving)",
    "NAME_FAMILY_STATUS": "Marital and Family Status",
    "NAME_HOUSING_TYPE": "Housing and Residential Arrangement",
    "CNT_CHILDREN": "Number of Dependent Children",
    "CNT_FAM_MEMBERS": "Total Household Family Members",

    # Identity & Residential Stability
    "DAYS_ID_PUBLISH": "Identity Document Age (Days Since Issue)",
    "DAYS_REGISTRATION": "Residential Registration Duration (Days)",
    "DAYS_LAST_PHONE_CHANGE": "Days Since Last Contact Phone Change",
    "FLAG_PHONE": "Home / Fixed Landline Contact Flag",
    "FLAG_WORK_PHONE": "Employer / Work Phone Verification Flag",
    "FLAG_EMAIL": "Email Address Verification Flag",
    "FLAG_OWN_CAR": "Vehicle Ownership Flag",
    "FLAG_OWN_REALTY": "Real Estate / Homeownership Flag",

    # Credit History & Behavioral Delinquency
    "DELINQUENCY_FLAG": "Prior Delinquency / Default Hazard Indicator",
    "DEF_30_CNT_SOCIAL_CIRCLE": "Defaults Within 30 Days in Social Circle",
    "DEF_60_CNT_SOCIAL_CIRCLE": "Defaults Within 60 Days in Social Circle",
    "OBS_30_CNT_SOCIAL_CIRCLE": "Observed Borrowers in Social Circle (30-day)",
    "OBS_60_CNT_SOCIAL_CIRCLE": "Observed Borrowers in Social Circle (60-day)",
    "REGION_RATING_CLIENT": "Regional Credit Risk Rating",
    "REGION_RATING_CLIENT_W_CITY": "Regional Risk Rating with City Context",
    "REGION_POPULATION_RELATIVE": "Relative Regional Population Density",
    "HOUR_APPR_PROCESS_START": "Application Submission Hour",

    # Inquiries
    "AMT_REQ_CREDIT_BUREAU_YEAR": "Credit Bureau Inquiries in Prior Year",
    "AMT_REQ_CREDIT_BUREAU_QRT": "Credit Bureau Inquiries in Prior Quarter",
    "AMT_REQ_CREDIT_BUREAU_MON": "Credit Bureau Inquiries in Prior Month",
    "AMT_REQ_CREDIT_BUREAU_WEEK": "Credit Bureau Inquiries in Prior Week",
    "AMT_REQ_CREDIT_BUREAU_DAY": "Credit Bureau Inquiries in Prior Day",
    "AMT_REQ_CREDIT_BUREAU_HOUR": "Credit Bureau Inquiries in Prior Hour"
}


def translate_feature_name(name: str) -> str:
    """
    Returns a professional plain-English title for a given technical feature name.
    Falls back to title-cased string if feature is not explicitly mapped.
    """
    if not name:
        return ""
    if name in FEATURE_NAME_MAP:
        return FEATURE_NAME_MAP[name]
    return name.replace("_", " ").strip().title()


def generate_feature_explanation(name: str, shap_val: float, raw_val: Optional[float] = None) -> str:
    """
    Generates a natural-language adverse action / risk explanation from a SHAP attribution.
    
    Args:
        name: Technical feature name (e.g. 'EXT_SOURCES_MEAN')
        shap_val: SHAP contribution value (positive = increased risk, negative = reduced risk)
        raw_val: Optional raw or normalized feature value for additional context
        
    Returns:
        A complete plain-English credit narrative statement.
    """
    direction = "increased" if shap_val > 0 else "reduced"
    impact_magnitude = f"(+{shap_val:.2f})" if shap_val > 0 else f"({shap_val:.2f})"
    feature_title = translate_feature_name(name)

    # Domain-specific narrative phrasing for primary risk drivers
    if name in ("EXT_SOURCES_MEAN", "EXT_SOURCES_MIN", "EXT_SOURCES_MAX"):
        if shap_val > 0:
            return f"{feature_title} elevated default hazard {impact_magnitude}"
        return f"{feature_title} significantly reduced default risk {impact_magnitude}"

    if name in ("EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"):
        if shap_val > 0:
            return f"{feature_title} elevated default risk {impact_magnitude}"
        return f"{feature_title} strengthened borrower solvency rating {impact_magnitude}"

    if name == "DEBT_TO_INCOME":
        if shap_val > 0:
            return f"Debt-to-Income burden increased default probability {impact_magnitude}"
        return f"Conservative Debt-to-Income ratio lowered default risk {impact_magnitude}"

    if name == "PAYMENT_RATE":
        if shap_val > 0:
            return f"Loan Payment-to-Credit ratio increased repayment hazard {impact_magnitude}"
        return f"Favorable Loan Payment-to-Credit ratio supported creditworthiness {impact_magnitude}"

    if name == "GOODS_PRICE_TO_CREDIT":
        if shap_val > 0:
            return f"Goods Price to Credit ratio increased collateral risk {impact_magnitude}"
        return f"Strong collateral equity margin reduced credit risk {impact_magnitude}"

    if name in ("BUREAU_TOTAL_OVERDUE", "BUREAU_MAX_OVERDUE_DAYS", "DELINQUENCY_FLAG"):
        if shap_val > 0:
            return f"{feature_title} substantially elevated default risk {impact_magnitude}"
        return f"Clean credit bureau delinquency record supported credit approval {impact_magnitude}"

    if name == "BUREAU_TOTAL_DEBT":
        if shap_val > 0:
            return f"High total external bureau debt increased leverage hazard {impact_magnitude}"
        return f"Manageable external bureau debt profile lowered risk {impact_magnitude}"

    if name in ("EMPLOYED_YEARS", "DAYS_EMPLOYED"):
        if shap_val > 0:
            return f"Shorter employment tenure duration elevated risk {impact_magnitude}"
        return f"Stable employment tenure duration reduced risk {impact_magnitude}"

    if name in ("AGE_YEARS", "DAYS_BIRTH"):
        return f"Applicant age profile {direction} default risk {impact_magnitude}"

    if name == "NAME_EDUCATION_TYPE":
        if shap_val > 0:
            return f"Educational attainment background elevated risk profile {impact_magnitude}"
        return f"Educational attainment background lowered default risk {impact_magnitude}"

    if name == "OWN_CAR_AGE":
        if shap_val > 0:
            return f"Older vehicle collateral age contributed to higher risk {impact_magnitude}"
        return f"Vehicle asset ownership profile reduced credit risk {impact_magnitude}"

    if name == "DAYS_EMPLOYED_ANOM":
        return f"Pensioner / employment anomaly status {direction} risk {impact_magnitude}"

    # General standard explanation
    return f"{feature_title} {direction} risk {impact_magnitude}"
