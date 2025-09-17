"""
Stellar SDK Warning Filter
Manages deprecation warnings from external dependencies.
"""

import logging
import warnings
from typing import Optional

# Configure logger
logger = logging.getLogger(__name__)


class StellarWarningsFilter:
    """
    Manages warning filters for Stellar SDK and related dependencies.

    This class provides a centralized way to handle external dependency
    warnings that we cannot fix directly.
    """

    @staticmethod
    def suppress_xdrlib_deprecation() -> None:
        """
        Suppress xdrlib deprecation warning from stellar_sdk.

        Background:
        - Python's xdrlib module is deprecated in 3.11 and removed in 3.13
        - stellar_sdk still uses xdrlib internally
        - This warning is beyond our control until stellar_sdk is updated
        """
        warnings.filterwarnings(
            "ignore",
            message="'xdrlib' is deprecated and slated for removal in Python 3.13",
            category=DeprecationWarning,
            module="stellar_sdk.xdr.*",
        )

        logger.debug("Suppressed stellar_sdk xdrlib deprecation warnings")

    @staticmethod
    def suppress_all_stellar_warnings() -> None:
        """
        Suppress all known warnings from stellar_sdk dependencies.
        """
        # XDR deprecation
        StellarWarningsFilter.suppress_xdrlib_deprecation()

        # Any future stellar_sdk warnings can be added here
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="stellar_sdk.*")

        logger.debug("Suppressed all stellar_sdk dependency warnings")

    @staticmethod
    def configure_production_warnings() -> None:
        """
        Configure warning filters for production environment.

        In production, we suppress external dependency warnings but
        keep our own code warnings active.
        """
        # Suppress external dependency warnings
        StellarWarningsFilter.suppress_all_stellar_warnings()

        # Keep warnings for our code active
        warnings.filterwarnings(
            "default", category=DeprecationWarning, module="hummingbot.connector.exchange.stellar.*"
        )

        logger.info("Configured production warning filters")


# Convenience function for easy import
def suppress_stellar_warnings() -> None:
    """Convenience function to suppress stellar_sdk warnings."""
    StellarWarningsFilter.suppress_all_stellar_warnings()


# Auto-suppress on import (optional)
def _auto_suppress_warnings() -> None:
    """
    Automatically suppress warnings on module import.

    Uncomment the call below if you want warnings suppressed
    automatically when this module is imported.
    """
    # StellarWarningsFilter.suppress_all_stellar_warnings()
    pass


if __name__ == "__main__":
    # Test the warning suppression
    StellarWarningsFilter.configure_production_warnings()

    import stellar_sdk

    print(f"✅ stellar_sdk {stellar_sdk.__version__} warnings configured")
