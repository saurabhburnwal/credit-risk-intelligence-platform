"""Tests for SQL Whitelist Safety Validation, Query Runner, and NL-to-SQL Agent."""
import pytest
from src.talk_to_data.query_runner import SafeQueryRunner, SQLSecurityError
from src.talk_to_data.nl_to_sql import get_talk_to_data_agent


def test_sql_whitelist_safety():
    runner = SafeQueryRunner()

    # 1. Valid single SELECT should pass
    valid_sql = "SELECT NAME_CONTRACT_TYPE, COUNT(*) as cnt FROM applications GROUP BY NAME_CONTRACT_TYPE"
    res = runner.execute_query(valid_sql)
    assert res["success"] is True
    assert len(res["data"]) > 0

    # 2. Block DROP statements
    bad_drop = "DROP TABLE applications"
    res_drop = runner.execute_query(bad_drop)
    assert res_drop["success"] is False
    assert "Security Validation Blocked" in res_drop["error"]

    # 3. Block DELETE statements
    bad_del = "DELETE FROM applications WHERE 1=1"
    res_del = runner.execute_query(bad_del)
    assert res_del["success"] is False
    assert "Security Validation Blocked" in res_del["error"]

    # 4. Block chained semicolon queries
    chained = "SELECT * FROM applications; DROP TABLE applications;"
    res_chained = runner.execute_query(chained)
    assert res_chained["success"] is False
    assert "Security Validation Blocked" in res_chained["error"]

    # 5. Block SQL comments (-- and /* */)
    comment1 = "SELECT * FROM applications -- drop table"
    res_com1 = runner.execute_query(comment1)
    assert res_com1["success"] is False
    assert "Security Validation Blocked" in res_com1["error"]

    comment2 = "SELECT /* admin query */ * FROM applications"
    res_com2 = runner.execute_query(comment2)
    assert res_com2["success"] is False
    assert "Security Validation Blocked" in res_com2["error"]


def test_talk_to_data_queries():
    agent = get_talk_to_data_agent()

    # Test the 5 required query patterns
    patterns = [
        "What is the default rate across different education levels?",
        "Show average credit amount and default rate by income type.",
        "How do external credit bureau scores impact default rates?",
        "Compare default rates for applicants with prior bureau overdue debt versus clean credit histories.",
        "Which demographic clusters by gender and family status have the highest default rates?"
    ]

    for q in patterns:
        res = agent.ask(q)
        assert res["success"] is True
        assert res["row_count"] > 0
        assert len(res["sql"]) > 10
        assert len(res["business_insight"]) > 5
