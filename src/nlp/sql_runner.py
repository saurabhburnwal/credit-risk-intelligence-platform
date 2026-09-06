"""
Safe SQL Query Runner Compatibility Module.
Re-exports SafeQueryRunner and SQLSecurityError from src.talk_to_data.query_runner.
"""

from src.talk_to_data.query_runner import (
    SafeQueryRunner,
    SQLSecurityError,
)

__all__ = [
    "SafeQueryRunner",
    "SQLSecurityError",
]
