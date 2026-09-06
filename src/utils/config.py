"""
Configuration module for Credit Risk Intelligence Platform.
Auto-detects data paths, sets default thresholds, and loads environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory: root of credit_risk_platform
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")


def get_data_dir() -> Path:
    """
    Locates the dataset directory automatically.
    Searches:
      1. DATA_DIR env variable
      2. ./data inside credit_risk_platform (if csv files exist)
      3. ../home-credit-default-risk (local workspace root)
      4. /app/data (Docker container mount)
    """
    env_data = os.getenv("DATA_DIR")
    if env_data and Path(env_data).exists():
        return Path(env_data)

    local_data = BASE_DIR / "data"
    if local_data.exists() and (local_data / "application_train.csv").exists():
        return local_data

    parent_data = BASE_DIR.parent / "home-credit-default-risk"
    if parent_data.exists() and (parent_data / "application_train.csv").exists():
        return parent_data

    docker_data = Path("/app/data")
    if docker_data.exists() and (docker_data / "application_train.csv").exists():
        return docker_data

    # Default fallback to local data dir
    return local_data


def ensure_sqlite_db() -> Path:
    """
    Ensures that the SQLite analytics database is available.
    If credit_risk.db is missing but credit_risk.db.gz exists,
    transparently decompresses it in ~0.5s for zero-setup evaluation.
    """
    db_target = BASE_DIR / os.getenv("DB_PATH", "sql/credit_risk.db")
    if not db_target.exists():
        gz_candidate = db_target.parent / (db_target.name + ".gz")
        if gz_candidate.exists():
            import gzip
            import shutil
            db_target.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(gz_candidate, "rb") as f_in:
                with open(db_target, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
    return db_target


DATA_DIR = get_data_dir()
MODELS_DIR = BASE_DIR / "models"
SQL_DIR = BASE_DIR / "sql"
DB_PATH = ensure_sqlite_db()
MODEL_PATH = BASE_DIR / os.getenv("MODEL_PATH", "models/lightgbm_credit_model.joblib")
PREPROCESSOR_PATH = BASE_DIR / "models/preprocessor.joblib"
METADATA_PATH = BASE_DIR / "models/metadata.json"

# Underwriting Risk Band Thresholds
# Probability of Default cutoffs
THRESHOLD_LOW_RISK = 0.05       # P < 0.05 -> Low Risk (Instant Approval)
THRESHOLD_MEDIUM_RISK = 0.15    # 0.05 <= P < 0.15 -> Medium Risk (Manual Diligence)
# P >= 0.15 -> High Risk (Strict Decline / Covenants)

# LLM Configurations
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "ministral-3:3b")

# Web Configuration
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
SECRET_KEY = os.getenv("SECRET_KEY", "neostats-secret-key-2026")
