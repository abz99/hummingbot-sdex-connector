"""
Stellar Structured Logging
Enhanced logging with correlation IDs and structured output.
"""

import asyncio
import json
import time
import uuid
from contextvars import ContextVar
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import structlog
from structlog import BoundLogger
from structlog.typing import EventDict, Processor, WrappedLogger


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """Log categories for better organization."""

    NETWORK = "network"
    TRADING = "trading"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"
    HEALTH_CHECK = "health_check"
    ERROR_HANDLING = "error_handling"
    METRICS = "metrics"


# Context variables for correlation tracking
correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
session_id: ContextVar[Optional[str]] = ContextVar("session_id", default=None)


def add_correlation_id(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add correlation ID to log entries."""
    if correlation_id.get():
        event_dict["correlation_id"] = correlation_id.get()
    if request_id.get():
        event_dict["request_id"] = request_id.get()
    if user_id.get():
        event_dict["user_id"] = user_id.get()
    if session_id.get():
        event_dict["session_id"] = session_id.get()
    return event_dict


def add_timestamp(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add ISO timestamp to log entries."""
    event_dict["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime())
    return event_dict


def add_process_info(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add process information to log entries."""
    import os

    event_dict["process_id"] = os.getpid()

    # Add asyncio task information if available
    try:
        task = asyncio.current_task()
        if task:
            event_dict["task_name"] = getattr(task, "get_name", lambda: "unknown")()
    except RuntimeError:
        pass  # No event loop running

    return event_dict


def add_stellar_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add Stellar-specific context to log entries."""
    event_dict["component"] = "stellar_connector"
    event_dict["version"] = "3.0.0"
    return event_dict


def format_exception(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Format exception information for structured logging."""
    if "exception" in event_dict:
        exc = event_dict["exception"]
        if isinstance(exc, Exception):
            event_dict["exception"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "module": getattr(exc, "__module__", "unknown"),
            }

            # Add traceback if available
            import traceback

            if hasattr(exc, "__traceback__") and exc.__traceback__:
                event_dict["exception"]["traceback"] = traceback.format_tb(exc.__traceback__)

    return event_dict


class StellarLogger:
    """Enhanced structured logger for Stellar connector."""

    def __init__(self, logger_name: str = "stellar_connector") -> None:
        """Initialize structured logger."""
        self.logger_name = logger_name
        self._configure_structlog()
        self.logger = structlog.get_logger(logger_name)

    def _configure_structlog(self) -> None:
        """Configure structlog with our processors."""
        processors: List[str][Processor] = [
            structlog.contextvars.merge_contextvars,
            add_correlation_id,
            add_timestamp,
            add_process_info,
            add_stellar_context,
            format_exception,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
        ]

        # Add JSON processor for production, console for development
        import os

        if os.getenv("STELLAR_LOG_FORMAT", "json").lower() == "json":
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(
                int(os.getenv("STELLAR_LOG_LEVEL", "20"))  # INFO level
            ),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def bind(self, **kwargs: Any) -> BoundLogger:
        """Bind additional context to logger."""
        return self.logger.bind(**kwargs)  # type: ignore[no-any-return]

    def with_correlation_id(self, corr_id: Optional[str] = None) -> "CorrelatedLogger":
        """Create logger with correlation ID."""
        if not corr_id:
            corr_id = str(uuid.uuid4())
        return CorrelatedLogger(self.logger, corr_id)

    def with_context(self, **context: Any) -> BoundLogger:
        """Create logger with additional context."""
        return self.logger.bind(**context)  # type: ignore[no-any-return]

    def debug(self, message: str, category: Optional[LogCategory] = None, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, category, **kwargs)

    def info(self, message: str, category: Optional[LogCategory] = None, **kwargs: Any) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, category, **kwargs)

    def warning(self, message: str, category: Optional[LogCategory] = None, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, category, **kwargs)

    def error(
        self,
        message: str,
        category: Optional[LogCategory] = None,
        exception: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        """Log error message."""
        if exception:
            kwargs["exception"] = exception
        self._log(LogLevel.ERROR, message, category, **kwargs)

    def critical(
        self,
        message: str,
        category: Optional[LogCategory] = None,
        exception: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        """Log critical message."""
        if exception:
            kwargs["exception"] = exception
        self._log(LogLevel.CRITICAL, message, category, **kwargs)

    def _log(
        self, level: LogLevel, message: str, category: Optional[LogCategory] = None, **kwargs: Any
    ) -> None:
        """Internal logging method."""
        log_data = kwargs.copy()
        if category:
            log_data["category"] = category.value

        method = getattr(self.logger, level.value.lower())
        method(message, **log_data)


class CorrelatedLogger:
    """Logger with correlation ID context."""

    def __init__(self, logger: structlog.BoundLogger, corr_id: str) -> None:
        self.logger = logger
        self.correlation_id = corr_id
        self.bound_logger = logger.bind(correlation_id=corr_id)

    def __enter__(self) -> "CorrelatedLogger":
        """Enter correlation context."""
        correlation_id.set(self.correlation_id)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit correlation context."""
        correlation_id.set(None)

    def debug(self, message: str, category: Optional[LogCategory] = None, **kwargs: Any) -> None:
        """Log debug message with correlation ID."""
        self._log(LogLevel.DEBUG, message, category, **kwargs)

    def info(self, message: str, category: Optional[LogCategory] = None, **kwargs: Any) -> None:
        """Log info message with correlation ID."""
        self._log(LogLevel.INFO, message, category, **kwargs)

    def warning(self, message: str, category: Optional[LogCategory] = None, **kwargs: Any) -> None:
        """Log warning message with correlation ID."""
        self._log(LogLevel.WARNING, message, category, **kwargs)

    def error(
        self,
        message: str,
        category: Optional[LogCategory] = None,
        exception: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        """Log error message with correlation ID."""
        if exception:
            kwargs["exception"] = exception
        self._log(LogLevel.ERROR, message, category, **kwargs)

    def critical(
        self,
        message: str,
        category: Optional[LogCategory] = None,
        exception: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        """Log critical message with correlation ID."""
        if exception:
            kwargs["exception"] = exception
        self._log(LogLevel.CRITICAL, message, category, **kwargs)

    def _log(
        self, level: LogLevel, message: str, category: Optional[LogCategory] = None, **kwargs: Any
    ) -> None:
        """Internal logging method with correlation ID."""
        log_data = kwargs.copy()
        if category:
            log_data["category"] = category.value

        method = getattr(self.bound_logger, level.value.lower())
        method(message, **log_data)


class RequestLogger:
    """Logger for HTTP request/response tracking."""

    def __init__(self, base_logger: StellarLogger) -> None:
        self.base_logger = base_logger

    async def log_request(
        self, method: str, url: str, headers: Optional[Dict[str, str]] = None, **kwargs: Any
    ) -> str:
        """Log HTTP request and return request ID."""
        req_id = str(uuid.uuid4())

        token = request_id.set(req_id)
        try:
            self.base_logger.info(
                f"HTTP {method} request started",
                category=LogCategory.NETWORK,
                request_id=req_id,
                method=method,
                url=url,
                headers=headers,
                **kwargs,
            )
        finally:
            request_id.reset(token)

        return req_id

    async def log_response(
        self, req_id: str, status_code: int, response_time: float, **kwargs: Any
    ) -> None:
        """Log HTTP response."""
        token = request_id.set(req_id)
        try:
            level = LogLevel.INFO if 200 <= status_code < 400 else LogLevel.WARNING

            self.base_logger._log(
                level,
                "HTTP response received",
                category=LogCategory.NETWORK,
                request_id=req_id,
                status_code=status_code,
                response_time_ms=round(response_time * 1000, 2),
                **kwargs,
            )
        finally:
            request_id.reset(token)

    async def log_request_error(self, req_id: str, error: Exception, **kwargs: Any) -> None:
        """Log HTTP request error."""
        token = request_id.set(req_id)
        try:
            self.base_logger.error(
                "HTTP request failed",
                category=LogCategory.NETWORK,
                request_id=req_id,
                exception=error,
                **kwargs,
            )
        finally:
            request_id.reset(token)


class PerformanceLogger:
    """Logger for performance metrics."""

    def __init__(self, base_logger: StellarLogger) -> None:
        self.base_logger = base_logger

    async def log_operation_start(self, operation: str, **context: Any) -> str:
        """Log operation start and return operation ID."""
        op_id = str(uuid.uuid4())

        self.base_logger.info(
            f"Operation started: {operation}",
            category=LogCategory.PERFORMANCE,
            operation_id=op_id,
            operation=operation,
            start_time=time.time(),
            **context,
        )

        return op_id

    async def log_operation_end(
        self, op_id: str, operation: str, duration: float, success: bool = True, **context: Any
    ) -> None:
        """Log operation completion."""
        level = LogLevel.INFO if success else LogLevel.WARNING

        self.base_logger._log(
            level,
            f"Operation completed: {operation}",
            category=LogCategory.PERFORMANCE,
            operation_id=op_id,
            operation=operation,
            duration_ms=round(duration * 1000, 2),
            success=success,
            **context,
        )


# Global logger instances
_stellar_logger: Optional[StellarLogger] = None
_request_logger: Optional[RequestLogger] = None
_performance_logger: Optional[PerformanceLogger] = None


def get_stellar_logger(name: str = "stellar_connector") -> StellarLogger:
    """Get or create global Stellar logger."""
    global _stellar_logger
    if not _stellar_logger:
        _stellar_logger = StellarLogger(name)
    return _stellar_logger


def get_request_logger() -> RequestLogger:
    """Get or create global request logger."""
    global _request_logger
    if not _request_logger:
        _request_logger = RequestLogger(get_stellar_logger())
    return _request_logger


def get_performance_logger() -> PerformanceLogger:
    """Get or create global performance logger."""
    global _performance_logger
    if not _performance_logger:
        _performance_logger = PerformanceLogger(get_stellar_logger())
    return _performance_logger


# Convenience functions for direct usage
def log_info(message: str, category: Optional[LogCategory] = None, **kwargs: Any) -> None:
    """Log info message using global logger."""
    get_stellar_logger().info(message, category, **kwargs)


def log_error(
    message: str,
    exception: Optional[Exception] = None,
    category: Optional[LogCategory] = None,
    **kwargs: Any,
) -> None:
    """Log error message using global logger."""
    get_stellar_logger().error(message, category, exception, **kwargs)


def log_warning(message: str, category: Optional[LogCategory] = None, **kwargs: Any) -> None:
    """Log warning message using global logger."""
    get_stellar_logger().warning(message, category, **kwargs)


def with_correlation_id(corr_id: Optional[str] = None) -> CorrelatedLogger:
    """Create correlated logger context."""
    return get_stellar_logger().with_correlation_id(corr_id)
