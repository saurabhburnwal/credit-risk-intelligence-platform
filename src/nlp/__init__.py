"""
NLP and Conversational SQL Compatibility Package.
Provides clean alias exports mapping legacy/spec references in src.nlp to src.talk_to_data.
"""

from src.nlp.agent import ConversationalTalkToDataAgent, get_talk_to_data_agent
from src.nlp.sql_runner import SafeQueryRunner, SQLSecurityError

__all__ = [
    "ConversationalTalkToDataAgent",
    "get_talk_to_data_agent",
    "SafeQueryRunner",
    "SQLSecurityError",
]
