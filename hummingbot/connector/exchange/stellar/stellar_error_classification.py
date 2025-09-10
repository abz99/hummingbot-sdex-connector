"""
Stellar Error Classification and Handling
Comprehensive error classification, handling strategies, and recovery mechanisms.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import auto, Enum
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, Type, Union

import aiohttp
from stellar_sdk.exceptions import (
    BadRequestError,
    BadResponseError,
    BaseHorizonError,
)
from stellar_sdk.exceptions import ConnectionError as StellarConnectionError
from stellar_sdk.exceptions import (
    NotFoundError,
    SdkError,
)

from .stellar_logging import get_stellar_logger, LogCategory


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class ErrorCategory(Enum):
    """Error categories for classification."""

    NETWORK = auto()
    AUTHENTICATION = auto()
    RATE_LIMITING = auto()
    VALIDATION = auto()
    BUSINESS_LOGIC = auto()
    SYSTEM = auto()
    CONFIGURATION = auto()
    TIMEOUT = auto()
    RESOURCE_EXHAUSTION = auto()
    DATA_CORRUPTION = auto()


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""

    RETRY_IMMEDIATE = auto()
    RETRY_WITH_BACKOFF = auto()
    RETRY_WITH_JITTER = auto()
    SWITCH_ENDPOINT = auto()
    CIRCUIT_BREAKER = auto()
    DEGRADE_SERVICE = auto()
    ESCALATE = auto()
    NO_RECOVERY = auto()


@dataclass
class ErrorContext:
    """Context information for error handling."""

    operation: str
    endpoint: Optional[str] = None
    network: Optional[str] = None
    account_id: Optional[str] = None
    request_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ErrorClassification:
    """Error classification result."""

    category: ErrorCategory
    severity: ErrorSeverity
    recovery_strategy: RecoveryStrategy
    is_retryable: bool
    backoff_seconds: float = 1.0
    max_retries: int = 3
    description: str = ""


class StellarErrorClassifier:
    """Classifies Stellar-specific errors and determines recovery strategies."""

    def __init__(self) -> None:
        self.logger = get_stellar_logger()
        self._error_patterns = self._build_error_patterns()

    def _build_error_patterns(self) -> Dict[Type[Exception], ErrorClassification]:
        """Build error pattern mappings."""
        return {
            # Network errors
            aiohttp.ClientConnectorError: ErrorClassification(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                recovery_strategy=RecoveryStrategy.SWITCH_ENDPOINT,
                is_retryable=True,
                backoff_seconds=2.0,
                max_retries=3,
                description="Network connection failed",
            ),
            aiohttp.ClientTimeout: ErrorClassification(
                category=ErrorCategory.TIMEOUT,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                is_retryable=True,
                backoff_seconds=1.0,
                max_retries=2,
                description="Request timeout",
            ),
            StellarConnectionError: ErrorClassification(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                recovery_strategy=RecoveryStrategy.SWITCH_ENDPOINT,
                is_retryable=True,
                backoff_seconds=2.0,
                max_retries=3,
                description="Stellar network connection error",
            ),
            # HTTP status code errors
            BadRequestError: ErrorClassification(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.NO_RECOVERY,
                is_retryable=False,
                description="Bad request - fix the request parameters",
            ),
            NotFoundError: ErrorClassification(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                recovery_strategy=RecoveryStrategy.NO_RECOVERY,
                is_retryable=False,
                description="Resource not found",
            ),
            BaseHorizonError: ErrorClassification(
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recovery_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                is_retryable=True,
                backoff_seconds=5.0,
                max_retries=2,
                description="Horizon server error - temporary issue",
            ),
            # General errors
            ValueError: ErrorClassification(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.NO_RECOVERY,
                is_retryable=False,
                description="Invalid value or parameter",
            ),
            asyncio.TimeoutError: ErrorClassification(
                category=ErrorCategory.TIMEOUT,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                is_retryable=True,
                backoff_seconds=2.0,
                max_retries=2,
                description="Operation timeout",
            ),
            ConnectionError: ErrorClassification(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                recovery_strategy=RecoveryStrategy.SWITCH_ENDPOINT,
                is_retryable=True,
                backoff_seconds=3.0,
                max_retries=3,
                description="Connection error",
            ),
        }

    def classify_error(
        self, error: Exception, context: Optional[ErrorContext] = None
    ) -> ErrorClassification:
        """
        Classify an error and determine recovery strategy.

        Args:
            error: The exception to classify
            context: Additional context for classification

        Returns:
            ErrorClassification with recovery strategy
        """
        error_type = type(error)

        # Direct type mapping
        if error_type in self._error_patterns:
            classification = self._error_patterns[error_type]
        else:
            # Check inheritance hierarchy
            classification = None
            for pattern_type, pattern_class in self._error_patterns.items():
                if isinstance(error, pattern_type):
                    classification = pattern_class
                    break

            if not classification:
                classification = self._classify_unknown_error(error, context)

        # Enhance classification with context-specific logic
        return self._enhance_classification_with_context(classification, error, context)

    def _classify_unknown_error(
        self, error: Exception, context: Optional[ErrorContext]
    ) -> ErrorClassification:
        """Classify unknown errors based on message patterns."""
        error_msg = str(error).lower()

        # Rate limiting patterns
        if any(pattern in error_msg for pattern in ["rate limit", "too many requests", "429"]):
            return ErrorClassification(
                category=ErrorCategory.RATE_LIMITING,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.RETRY_WITH_JITTER,
                is_retryable=True,
                backoff_seconds=10.0,
                max_retries=5,
                description="Rate limit exceeded",
            )

        # Authentication patterns
        if any(
            pattern in error_msg
            for pattern in ["unauthorized", "authentication", "401", "forbidden", "403"]
        ):
            return ErrorClassification(
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                recovery_strategy=RecoveryStrategy.NO_RECOVERY,
                is_retryable=False,
                description="Authentication/authorization error",
            )

        # Validation patterns
        if any(pattern in error_msg for pattern in ["invalid", "malformed", "bad format"]):
            return ErrorClassification(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.NO_RECOVERY,
                is_retryable=False,
                description="Data validation error",
            )

        # Default classification for unknown errors
        return ErrorClassification(
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            recovery_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            is_retryable=True,
            backoff_seconds=5.0,
            max_retries=2,
            description=f"Unknown error: {type(error).__name__}",
        )

    def _enhance_classification_with_context(
        self, classification: ErrorClassification, error: Exception, context: Optional[ErrorContext]
    ) -> ErrorClassification:
        """Enhance error classification based on context."""
        if not context:
            return classification

        # Adjust retry count based on context
        if context.retry_count >= context.max_retries:
            classification.is_retryable = False
            classification.recovery_strategy = RecoveryStrategy.ESCALATE

        # Network-specific adjustments
        if context.network == "mainnet" and classification.category == ErrorCategory.NETWORK:
            # Be more aggressive with mainnet recovery
            classification.severity = ErrorSeverity.CRITICAL
            classification.max_retries = min(classification.max_retries + 2, 5)

        return classification


class ErrorRecoveryHandler(ABC):
    """Abstract base class for error recovery handlers."""

    @abstractmethod
    async def can_handle(self, classification: ErrorClassification, context: ErrorContext) -> bool:
        """Check if this handler can handle the error."""
        pass

    @abstractmethod
    async def handle(
        self, error: Exception, classification: ErrorClassification, context: ErrorContext
    ) -> bool:
        """
        Handle the error and attempt recovery.

        Returns:
            True if recovery was successful, False otherwise
        """
        pass


class RetryWithBackoffHandler(ErrorRecoveryHandler):
    """Handler for retry with exponential backoff."""

    async def can_handle(self, classification: ErrorClassification, context: ErrorContext) -> bool:
        return (
            classification.recovery_strategy == RecoveryStrategy.RETRY_WITH_BACKOFF
            and classification.is_retryable
        )

    async def handle(
        self, error: Exception, classification: ErrorClassification, context: ErrorContext
    ) -> bool:
        if context.retry_count >= classification.max_retries:
            return False

        backoff_time = classification.backoff_seconds * (2**context.retry_count)
        await asyncio.sleep(min(backoff_time, 60))  # Cap at 60 seconds
        return True


class RetryWithJitterHandler(ErrorRecoveryHandler):
    """Handler for retry with jitter to prevent thundering herd."""

    async def can_handle(self, classification: ErrorClassification, context: ErrorContext) -> bool:
        return (
            classification.recovery_strategy == RecoveryStrategy.RETRY_WITH_JITTER
            and classification.is_retryable
        )

    async def handle(
        self, error: Exception, classification: ErrorClassification, context: ErrorContext
    ) -> bool:
        if context.retry_count >= classification.max_retries:
            return False

        import random

        backoff_time = classification.backoff_seconds * (2**context.retry_count)
        jitter = random.uniform(0.1, 0.5) * backoff_time
        await asyncio.sleep(min(backoff_time + jitter, 60))
        return True


class SwitchEndpointHandler(ErrorRecoveryHandler):
    """Handler for switching to fallback endpoints."""

    def __init__(self, endpoint_switcher: Callable[[str], Awaitable[bool]]) -> None:
        self.endpoint_switcher = endpoint_switcher

    async def can_handle(self, classification: ErrorClassification, context: ErrorContext) -> bool:
        return classification.recovery_strategy == RecoveryStrategy.SWITCH_ENDPOINT

    async def handle(
        self, error: Exception, classification: ErrorClassification, context: ErrorContext
    ) -> bool:
        if context.endpoint:
            return await self.endpoint_switcher(context.endpoint)
        return False


class CircuitBreakerHandler(ErrorRecoveryHandler):
    """Handler for circuit breaker pattern."""

    def __init__(self) -> None:
        self.failure_counts: Dict[str, int] = {}
        self.circuit_open_until: Dict[str, float] = {}
        self.failure_threshold = 5
        self.recovery_timeout = 60

    async def can_handle(self, classification: ErrorClassification, context: ErrorContext) -> bool:
        return classification.recovery_strategy == RecoveryStrategy.CIRCUIT_BREAKER

    async def handle(
        self, error: Exception, classification: ErrorClassification, context: ErrorContext
    ) -> bool:
        endpoint_key = context.endpoint or context.operation

        # Check if circuit is open
        if endpoint_key in self.circuit_open_until:
            if time.time() < self.circuit_open_until[endpoint_key]:
                return False  # Circuit still open
            else:
                # Try to close circuit
                del self.circuit_open_until[endpoint_key]
                self.failure_counts[endpoint_key] = 0

        # Increment failure count
        self.failure_counts[endpoint_key] = self.failure_counts.get(endpoint_key, 0) + 1

        # Open circuit if threshold exceeded
        if self.failure_counts[endpoint_key] >= self.failure_threshold:
            self.circuit_open_until[endpoint_key] = time.time() + self.recovery_timeout
            return False

        return True


class StellarErrorManager:
    """Main error management system for Stellar connector."""

    def __init__(self) -> None:
        self.logger = get_stellar_logger()
        self.classifier = StellarErrorClassifier()
        self.handlers: Dict[RecoveryStrategy, ErrorRecoveryHandler] = {}
        self._error_stats: Dict[str, int] = {}

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default error recovery handlers."""
        self.handlers[RecoveryStrategy.RETRY_WITH_BACKOFF] = RetryWithBackoffHandler()
        self.handlers[RecoveryStrategy.RETRY_WITH_JITTER] = RetryWithJitterHandler()
        self.handlers[RecoveryStrategy.CIRCUIT_BREAKER] = CircuitBreakerHandler()

    def register_handler(self, strategy: RecoveryStrategy, handler: ErrorRecoveryHandler) -> None:
        """Register a custom error recovery handler."""
        self.handlers[strategy] = handler

    def register_endpoint_switcher(self, switcher: Callable[[str], Awaitable[bool]]) -> None:
        """Register endpoint switcher for fallback handling."""
        self.handlers[RecoveryStrategy.SWITCH_ENDPOINT] = SwitchEndpointHandler(switcher)

    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        operation_callback: Optional[Callable[[], Awaitable[Any]]] = None,
    ) -> Tuple[bool, Any]:
        """
        Handle an error with appropriate recovery strategy.

        Args:
            error: The exception that occurred
            context: Error context information
            operation_callback: Optional callback to retry the operation

        Returns:
            Tuple of (success, result)
        """
        # Classify the error
        classification = self.classifier.classify_error(error, context)

        # Log the error
        self.logger.error(
            f"Error in {context.operation}",
            category=LogCategory.ERROR_HANDLING,
            exception=error,
            classification=classification.category.name,
            severity=classification.severity.name,
            recovery_strategy=classification.recovery_strategy.name,
            is_retryable=classification.is_retryable,
            retry_count=context.retry_count,
            **context.metadata,
        )

        # Update error statistics
        error_key = f"{type(error).__name__}:{context.operation}"
        self._error_stats[error_key] = self._error_stats.get(error_key, 0) + 1

        # If not retryable, return immediately
        if not classification.is_retryable:
            return False, None

        # Find appropriate handler
        handler = self.handlers.get(classification.recovery_strategy)
        if not handler:
            self.logger.warning(
                f"No handler found for recovery strategy: {classification.recovery_strategy}",
                category=LogCategory.ERROR_HANDLING,
            )
            return False, None

        # Check if handler can handle this error
        if not await handler.can_handle(classification, context):
            return False, None

        # Attempt recovery
        recovery_success = await handler.handle(error, classification, context)
        if not recovery_success:
            return False, None

        # If we have an operation callback, try to retry the operation
        if operation_callback:
            try:
                context.retry_count += 1
                result = await operation_callback()

                self.logger.info(
                    f"Error recovery successful for {context.operation}",
                    category=LogCategory.ERROR_HANDLING,
                    retry_count=context.retry_count,
                    recovery_strategy=classification.recovery_strategy.name,
                )

                return True, result

            except Exception as retry_error:
                # Recursive call for retry error handling
                return await self.handle_error(retry_error, context, operation_callback)

        return True, None

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        total_errors = sum(self._error_stats.values())
        return {
            "total_errors": total_errors,
            "error_breakdown": dict(self._error_stats),
            "most_common_errors": sorted(
                self._error_stats.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }
