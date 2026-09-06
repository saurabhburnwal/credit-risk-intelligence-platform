-- ==============================================================================
-- Schema for AI-Powered Credit Risk Intelligence Platform
-- Multi-table relational database for credit underwriting and Talk-to-Data analytics
-- ==============================================================================

-- 1. Main Loan Applications Table
CREATE TABLE IF NOT EXISTS applications (
    SK_ID_CURR INTEGER PRIMARY KEY,
    TARGET INTEGER,                             -- 0: Non-default, 1: Default / payment difficulty
    NAME_CONTRACT_TYPE TEXT,                    -- Cash loans, Revolving loans
    CODE_GENDER TEXT,                           -- M, F, XNA
    FLAG_OWN_CAR TEXT,                          -- Y, N
    FLAG_OWN_REALTY TEXT,                       -- Y, N
    CNT_CHILDREN INTEGER,                       -- Number of children
    AMT_INCOME_TOTAL REAL,                      -- Annual applicant income
    AMT_CREDIT REAL,                            -- Loan credit amount
    AMT_ANNUITY REAL,                           -- Monthly loan annuity
    AMT_GOODS_PRICE REAL,                       -- Goods price for consumer loans
    NAME_INCOME_TYPE TEXT,                      -- Working, Commercial associate, Pensioner, State servant
    NAME_EDUCATION_TYPE TEXT,                   -- Higher education, Secondary / secondary special, etc.
    NAME_FAMILY_STATUS TEXT,                    -- Married, Single / not married, Civil marriage, etc.
    NAME_HOUSING_TYPE TEXT,                     -- House / apartment, Rented apartment, With parents, etc.
    DAYS_BIRTH INTEGER,                         -- Age in days (negative)
    DAYS_EMPLOYED INTEGER,                      -- Employment duration in days (negative, 365243 = anomaly)
    OCCUPATION_TYPE TEXT,                       -- Laborers, Core staff, Managers, Drivers, etc.
    REGION_RATING_CLIENT INTEGER,               -- Regional rating (1, 2, 3)
    EXT_SOURCE_1 REAL,                          -- Normalized external bureau score 1 (0.0 - 1.0)
    EXT_SOURCE_2 REAL,                          -- Normalized external bureau score 2 (0.0 - 1.0)
    EXT_SOURCE_3 REAL,                          -- Normalized external bureau score 3 (0.0 - 1.0)
    DEF_30_CNT_SOCIAL_CIRCLE REAL,              -- Social circle delinquencies (30 DPD)
    DEF_60_CNT_SOCIAL_CIRCLE REAL,              -- Social circle delinquencies (60 DPD)
    AMT_REQ_CREDIT_BUREAU_YEAR REAL,            -- Inquiries in past year
    AGE_YEARS REAL,                             -- Calculated age in years
    EMPLOYED_YEARS REAL,                        -- Calculated employment tenure in years
    DEBT_TO_INCOME REAL,                        -- Ratio of Annuity to Annual Income
    PAYMENT_RATE REAL                           -- Ratio of Annuity to Credit Amount
);

-- 2. Aggregated External Credit Bureau Table
CREATE TABLE IF NOT EXISTS bureau_summary (
    SK_ID_CURR INTEGER PRIMARY KEY,
    BUREAU_LOAN_COUNT INTEGER,                  -- Total prior external credit lines
    BUREAU_ACTIVE_COUNT INTEGER,                -- Currently active credit lines
    BUREAU_TOTAL_OVERDUE REAL,                  -- Total current overdue debt amount
    BUREAU_MAX_OVERDUE_DAYS REAL,               -- Historical maximum days past due
    BUREAU_TOTAL_DEBT REAL                      -- Total debt across active credit lines
);

-- 3. Aggregated Home Credit Previous Applications Table
CREATE TABLE IF NOT EXISTS previous_applications_summary (
    SK_ID_CURR INTEGER PRIMARY KEY,
    PREV_APP_COUNT INTEGER,                     -- Total previous loan applications at Home Credit
    PREV_REFUSED_COUNT INTEGER,                 -- Number of previous loan applications rejected
    PREV_APPROVED_COUNT INTEGER,                -- Number of previous loan applications approved
    PREV_AVG_CREDIT REAL,                       -- Mean prior loan credit amount
    PREV_REFUSAL_RATE REAL                      -- Rejection rate (Refused / Total)
);

-- Indexes for lightning-fast Talk-to-Data SQL query execution
CREATE INDEX IF NOT EXISTS idx_app_id ON applications(SK_ID_CURR);
CREATE INDEX IF NOT EXISTS idx_app_target ON applications(TARGET);
CREATE INDEX IF NOT EXISTS idx_app_edu ON applications(NAME_EDUCATION_TYPE);
CREATE INDEX IF NOT EXISTS idx_app_inc ON applications(NAME_INCOME_TYPE);
CREATE INDEX IF NOT EXISTS idx_app_gender ON applications(CODE_GENDER);
CREATE INDEX IF NOT EXISTS idx_bureau_id ON bureau_summary(SK_ID_CURR);
CREATE INDEX IF NOT EXISTS idx_prev_id ON previous_applications_summary(SK_ID_CURR);
