"""
Helper and formatting utilities for risk intelligence.
"""

from typing import Dict, Any, Tuple
from src.utils.config import THRESHOLD_LOW_RISK, THRESHOLD_MEDIUM_RISK


def calculate_risk_band(prob_default: float) -> Tuple[int, str, str]:
    """
    Maps probability of default (0.0 - 1.0) into:
      - Risk Score (0 - 100)
      - Risk Band ('Low Risk', 'Medium Risk', 'High Risk')
      - Recommendation ('Fast-Track Approve', 'Manual Review', 'High Risk - Decline')
    """
    prob_clamped = max(0.0, min(1.0, float(prob_default)))
    score = int(round(prob_clamped * 100))

    if prob_clamped < THRESHOLD_LOW_RISK:
        band = "Low Risk"
        recommendation = "Fast-Track Approve"
    elif prob_clamped < THRESHOLD_MEDIUM_RISK:
        band = "Medium Risk"
        recommendation = "Manual Review / Extra Collateral"
    else:
        band = "High Risk"
        recommendation = "High Risk - Stricter Terms or Decline"

    return score, band, recommendation


def format_currency(amount: float) -> str:
    """Formats a float as USD currency string."""
    try:
        return f"${amount:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


def format_percentage(val: float) -> str:
    """Formats float as percentage string."""
    try:
        return f"{val * 100:.2f}%"
    except (ValueError, TypeError):
        return "0.00%"
