"""
Stellar Utilities
Common utility functions for Stellar operations.
"""

from decimal import Decimal
from typing import Optional
from stellar_sdk import Asset


def format_stellar_amount(amount: Decimal) -> str:
    """Format amount for Stellar transactions."""
    return f"{amount:.7f}"


def parse_asset_string(asset_str: str) -> Optional[Asset]:
    """Parse asset string into Asset object."""
    if asset_str == "XLM" or asset_str == "native":
        return Asset.native()

    parts = asset_str.split(":")
    if len(parts) == 2:
        return Asset(parts[0], parts[1])

    return None
