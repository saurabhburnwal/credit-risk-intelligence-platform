"""
Strict Whitelist SQL Safety Validator and Execution Engine for Talk-to-Data.
Enforces single-SELECT whitelist validation, blocks comments/chaining, and executes
queries in read-only SQLite mode.
"""

import re
import time
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DML, DDL, Comment

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import DB_PATH
from src.utils.logger import logger


class SQLSecurityError(ValueError):
    """Raised when SQL fails strict whitelist security checks."""
    pass


class SafeQueryRunner:
    """
    Executes database queries with strict AST-based single-SELECT whitelist validation.
    """

    FORBIDDEN_KEYWORDS = {
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
        "ATTACH", "DETACH", "PRAGMA", "EXEC", "EXECUTE", "REPLACE", "VACUUM",
        "GRANT", "REVOKE", "INTO", "OUTFILE", "DUMPFILE"
    }

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database missing at {self.db_path}. Build DB first via loader.py --build-db.")

    def validate_sql_whitelist(self, query: str) -> str:
        """
        Validates SQL against strict whitelist safety rules:
          1. Exactly one statement allowed.
          2. Statement type MUST be 'SELECT'.
          3. Semicolons and chained queries rejected.
          4. Comments (-- and /* */) rejected to prevent hidden payloads.
          5. No forbidden DDL/DML/admin keywords permitted anywhere.
        Returns cleaned SQL query if valid, raises SQLSecurityError otherwise.
        """
        raw_sql = query.strip()
        if not raw_sql:
            raise SQLSecurityError("Empty query provided.")

        # 1. Reject comments that could conceal chained statements or bypass parser
        if re.search(r"--|/\*|\*/", raw_sql):
            raise SQLSecurityError("SQL comments (-- or /* */) are strictly prohibited.")

        # 2. Reject internal unquoted semicolons that chain statements
        semicolon_count = raw_sql.count(";")
        if semicolon_count > 1 or (semicolon_count == 1 and not raw_sql.endswith(";")):
            raise SQLSecurityError("Multiple statements or chained commands (';') are strictly prohibited.")

        cleaned_sql = raw_sql.rstrip(";").strip()

        # 3. Parse AST using sqlparse
        parsed = sqlparse.parse(cleaned_sql)
        if len(parsed) != 1:
            raise SQLSecurityError(f"Expected exactly 1 statement, but received {len(parsed)}.")

        stmt: Statement = parsed[0]

        # 4. Strict assertion: Statement type MUST be SELECT
        stmt_type = stmt.get_type()
        if stmt_type.upper() != "SELECT":
            raise SQLSecurityError(f"Only single 'SELECT' queries are allowed. Detected: '{stmt_type}'.")

        # 5. Token inspection for forbidden keywords
        tokens = list(stmt.flatten())
        for token in tokens:
            val_upper = token.value.upper()
            if val_upper in self.FORBIDDEN_KEYWORDS:
                raise SQLSecurityError(f"Forbidden keyword '{val_upper}' detected in statement.")
            if token.ttype in (DML, DDL) and val_upper != "SELECT":
                raise SQLSecurityError(f"Forbidden DML/DDL operation '{val_upper}' detected.")

        return cleaned_sql

    def execute_query(self, query: str, max_rows: int = 100) -> Dict[str, Any]:
        """
        Validates and executes SQL query in read-only mode against SQLite.
        Returns dictionary with column headers, records, execution time, and row count.
        """
        start_time = time.time()
        uri = f"file:{self.db_path.resolve()}?mode=ro"
        conn = None
        validated_sql = query
        try:
            validated_sql = self.validate_sql_whitelist(query)
            conn = sqlite3.connect(uri, uri=True, timeout=5.0)
            cursor = conn.cursor()

            # Execute with limit enforcement
            cursor.execute(validated_sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchmany(max_rows)

            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            logger.info(f"Query executed successfully in {elapsed_ms}ms ({len(rows)} rows returned).")

            # Convert rows to serializable records
            records = [dict(zip(columns, row)) for row in rows]

            return {
                "success": True,
                "sql": validated_sql,
                "columns": columns,
                "data": records,
                "row_count": len(rows),
                "execution_time_ms": elapsed_ms,
                "truncated": len(rows) == max_rows
            }
        except sqlite3.Error as e:
            logger.error(f"Database execution error: {str(e)}")
            return {
                "success": False,
                "sql": validated_sql,
                "error": f"Database Error: {str(e)}",
                "execution_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        except SQLSecurityError as sec_err:
            logger.warning(f"SQL validation blocked: {str(sec_err)}")
            return {
                "success": False,
                "sql": query,
                "error": f"Security Validation Blocked: {str(sec_err)}",
                "execution_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        finally:
            if conn:
                conn.close()


if __name__ == "__main__":
    runner = SafeQueryRunner()
    test_query = "SELECT NAME_CONTRACT_TYPE, COUNT(*) as total, ROUND(AVG(TARGET)*100, 2) as default_rate_pct FROM applications GROUP BY NAME_CONTRACT_TYPE"
    res = runner.execute_query(test_query)
    print("Test Execution Result:", res)

    # Test safety rejection
    bad_query = "SELECT * FROM applications; DROP TABLE applications;"
    res_bad = runner.execute_query(bad_query)
    print("Safety Check (Should Fail):", res_bad["error"])
