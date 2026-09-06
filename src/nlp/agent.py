"""
Conversational Talk-to-Data Agent Compatibility Module.
Re-exports ConversationalTalkToDataAgent and get_talk_to_data_agent from src.talk_to_data.nl_to_sql.
"""

from src.talk_to_data.nl_to_sql import (
    ConversationalTalkToDataAgent,
    get_talk_to_data_agent,
)

__all__ = [
    "ConversationalTalkToDataAgent",
    "get_talk_to_data_agent",
]
