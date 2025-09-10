"""
Suppress xdrlib deprecation warnings from stellar_sdk.
This addresses the external dependency warning that we cannot fix directly.
"""

import warnings


def suppress_stellar_sdk_warnings():
    """
    Suppress xdrlib deprecation warning from stellar_sdk.
    
    This warning comes from stellar_sdk using Python's deprecated xdrlib module.
    Since this is an external dependency issue, we suppress the warning until
    stellar_sdk releases a fix.
    """
    warnings.filterwarnings(
        "ignore",
        message="'xdrlib' is deprecated and slated for removal in Python 3.13",
        category=DeprecationWarning,
        module="stellar_sdk.xdr.*"
    )


# Alternative: More specific suppression
def suppress_xdrlib_warnings_specific():
    """
    Suppress xdrlib warnings with more specific filtering.
    """
    warnings.filterwarnings(
        "ignore",
        message=".*xdrlib.*deprecated.*",
        category=DeprecationWarning,
    )


# Context manager for temporary suppression
class suppress_stellar_warnings:
    """Context manager to temporarily suppress stellar_sdk warnings."""
    
    def __enter__(self):
        self._original_filters = warnings.filters[:]
        suppress_stellar_sdk_warnings()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        warnings.filters[:] = self._original_filters
        return False


if __name__ == "__main__":
    # Test the suppression
    suppress_stellar_sdk_warnings()
    
    import stellar_sdk
    print(f"✅ stellar_sdk {stellar_sdk.__version__} imported with suppressed warnings")