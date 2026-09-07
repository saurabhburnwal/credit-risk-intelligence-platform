#!/bin/bash
set -e

TARGET_DB="${DB_PATH:-sql/credit_risk.db}"
DATA_DIRECTORY="${DATA_DIR:-data}"
APP_PORT="${PORT:-5000}"

# If database doesn't exist, download pre-built release or build from CSV
if [ ! -f "$TARGET_DB" ]; then
    if [ -n "$DATA_DOWNLOAD_URL" ]; then
        echo "=================================================================="
        echo "[Entrypoint] SQLite database not found at $TARGET_DB."
        echo "[Entrypoint] Downloading pre-built database from $DATA_DOWNLOAD_URL..."
        echo "=================================================================="
        mkdir -p "$(dirname "$TARGET_DB")"
        TMP_ZIP="/tmp/downloaded_db.zip"
        curl -fSL "$DATA_DOWNLOAD_URL" -o "$TMP_ZIP"
        
        # Extract the .db file directly to $TARGET_DB
        python3 -c "
import zipfile, os, shutil
zip_path = '$TMP_ZIP'
target_db = '$TARGET_DB'
with zipfile.ZipFile(zip_path, 'r') as z:
    db_files = [m for m in z.namelist() if m.endswith('.db') and not m.startswith('__MACOSX')]
    if not db_files:
        raise RuntimeError('No .db file found inside downloaded zip!')
    with z.open(db_files[0]) as src, open(target_db, 'wb') as dst:
        shutil.copyfileobj(src, dst)
print(f'[Entrypoint] Successfully extracted {db_files[0]} -> {target_db}')
"
        rm -f "$TMP_ZIP"
        echo "[Entrypoint] Pre-built database installed. File size: $(ls -lh "$TARGET_DB" | awk '{print $5}')"
    elif [ -d "$DATA_DIRECTORY" ] && [ -n "$(ls -A "$DATA_DIRECTORY" 2>/dev/null)" ]; then
        echo "=================================================================="
        echo "[Entrypoint] SQLite database not found at $TARGET_DB."
        echo "[Entrypoint] Building fresh database from CSVs in $DATA_DIRECTORY..."
        echo "=================================================================="
        uv run python -m src.data.loader --build-db
        echo "[Entrypoint] Database build complete. Persisted to volume."
    else
        echo "=================================================================="
        echo "[Entrypoint] ERROR: Neither $TARGET_DB, DATA_DOWNLOAD_URL, nor CSV files in $DATA_DIRECTORY were found!"
        echo "=================================================================="
        exit 1
    fi
else
    echo "[Entrypoint] SQLite database verified at $TARGET_DB."
fi

# Dynamically adjust port binding if PORT environment variable is set
FINAL_CMD=()
for arg in "$@"; do
    if [[ "$arg" == *"0.0.0.0:5000"* ]] && [ "$APP_PORT" != "5000" ]; then
        FINAL_CMD+=("${arg//0.0.0.0:5000/0.0.0.0:$APP_PORT}")
    else
        FINAL_CMD+=("$arg")
    fi
done

exec "${FINAL_CMD[@]}"
