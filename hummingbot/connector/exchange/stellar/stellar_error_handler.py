"""
Modern Stellar Error Handler
Advanced error classification and recovery.
"""

import asyncio
from typing import Dict, Optional, Any, Union
from enum import Enum
from stellar_sdk import exceptions as stellar_exceptions


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""

    NETWORK = "network"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    SEQUENCE_ERROR = "sequence_error"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class StellarErrorClassification:
    """Stellar error classification result."""

    def __init__(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        recoverable: bool,
        retry_after: Optional[int] = None,
        action: Optional[str] = None,
    ):
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.retry_after = retry_after
        self.action = action


class ModernStellarErrorHandler:
    """Advanced error handling and classification."""

    def __init__(self, observability: "StellarObservabilityFramework"):
        self.observability = observability
        self._error_patterns = self._initialize_error_patterns()
        self._error_counts: Dict[str, int] = {}
        self._last_errors: Dict[str, float] = {}

    def _initialize_error_patterns(self) -> Dict[str, StellarErrorClassification]:
        """Initialize error pattern mappings."""
        return {
            "op_underfunded": StellarErrorClassification(
                ErrorCategory.INSUFFICIENT_FUNDS,
                ErrorSeverity.HIGH,
                recoverable=True,
                action="check_balance",
            ),
            "op_no_trust": StellarErrorClassification(
                ErrorCategory.VALIDATION,
                ErrorSeverity.HIGH,
                recoverable=True,
                action="create_trustline",
            ),
            "tx_bad_seq": StellarErrorClassification(
                ErrorCategory.SEQUENCE_ERROR,
                ErrorSeverity.MEDIUM,
                recoverable=True,
                retry_after=2,
                action="refresh_sequence",
            ),
            "op_no_destination": StellarErrorClassification(
                ErrorCategory.VALIDATION,
                ErrorSeverity.HIGH,
                recoverable=False,
                action="verify_destination",
            ),
            "tx_too_early": StellarErrorClassification(
                ErrorCategory.VALIDATION, ErrorSeverity.LOW, recoverable=True, retry_after=1
            ),
            "tx_too_late": StellarErrorClassification(
                ErrorCategory.VALIDATION,
                ErrorSeverity.LOW,
                recoverable=False,
                action="rebuild_transaction",
            ),
        }

    async def classify_error(self, error: Exception) -> StellarErrorClassification:
        """Classify error and return classification details."""
        error_str = str(error).lower()

        # Check for known Stellar error patterns
        for pattern, classification in self._error_patterns.items():
            if pattern in error_str:
                await self.observability.log_event(
                    "error_classified",
                    {
                        "pattern": pattern,
                        "category": classification.category.value,
                        "severity": classification.severity.value,
                        "recoverable": classification.recoverable,
                    },
                )
                return classification

        # Handle network errors
        if any(x in error_str for x in ["timeout", "connection", "network"]):
            return StellarErrorClassification(
                ErrorCategory.NETWORK,
                ErrorSeverity.MEDIUM,
                recoverable=True,
                retry_after=5,
                action="retry_with_backoff",
            )

        # Handle rate limiting
        if any(x in error_str for x in ["rate limit", "429", "too many requests"]):
            return StellarErrorClassification(
                ErrorCategory.RATE_LIMIT,
                ErrorSeverity.LOW,
                recoverable=True,
                retry_after=30,
                action="wait_and_retry",
            )

        # Default classification for unknown errors
        return StellarErrorClassification(
            ErrorCategory.UNKNOWN, ErrorSeverity.HIGH, recoverable=False, action="investigate"
        )

    async def handle_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> StellarErrorClassification:
        """Handle error with classification and recovery suggestions."""
        classification = await self.classify_error(error)

        # Log error with classification
        await self.observability.log_error(
            "stellar_error_handled",
            error,
            {
                "category": classification.category.value,
                "severity": classification.severity.value,
                "recoverable": classification.recoverable,
                "action": classification.action,
                "context": context or {},
            },
        )

        # Update error counts for monitoring
        error_key = f"{classification.category.value}_{type(error).__name__}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

        return classification

    async def handle_startup_error(self, error: Exception):
        """Handle startup errors."""
        classification = await self.handle_error(error, {"phase": "startup"})

        if classification.severity == ErrorSeverity.CRITICAL:
            await self.observability.log_event(
                "startup_failure_critical",
                {"error_type": type(error).__name__, "message": str(error)},
            )
            raise error

    async def should_retry(self, error: Exception, attempt: int, max_attempts: int = 3) -> bool:
        """Determine if operation should be retried."""
        classification = await self.classify_error(error)

        if not classification.recoverable:
            return False

        if attempt >= max_attempts:
            return False

        return True

    async def get_retry_delay(self, error: Exception, attempt: int) -> int:
        """Calculate retry delay based on error type."""
        classification = await self.classify_error(error)

        if classification.retry_after:
            return classification.retry_after * (2 ** (attempt - 1))  # Exponential backoff

        return min(2**attempt, 30)  # Default exponential backoff, max 30s

    def get_error_statistics(self) -> Dict[str, int]:
        """Get error statistics for monitoring."""
        return self._error_counts.copy()
