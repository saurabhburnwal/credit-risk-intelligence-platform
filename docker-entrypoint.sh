#!/bin/bash
set -e

TARGET_DB="${DB_PATH:-sql/credit_risk.db}"
DATA_DIRECTORY="${DATA_DIR:-data}"

# Ensure SQLite analytics database is built on first startup
if [ ! -f "$TARGET_DB" ]; then
    echo "=================================================================="
    echo "[Entrypoint] SQLite database not found at $TARGET_DB."
    echo "[Entrypoint] Building fresh database from CSVs in $DATA_DIRECTORY..."
    echo "=================================================================="
    uv run python -m src.data.loader --build-db
    echo "[Entrypoint] Database build complete. Persisted to volume."
else
    echo "[Entrypoint] SQLite database verified at $TARGET_DB."
fi

exec "$@"
