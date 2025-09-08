"""
Security validation and hardening utilities for Stellar connector.
Implements input validation, rate limiting, and error sanitization.
"""

import asyncio
import hashlib
import ipaddress
import re
import secrets
import time
from dataclasses import dataclass, field
from enum import auto, Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Pattern, Set, Union

from .stellar_logging import get_stellar_logger, LogCategory


class ValidationLevel(Enum):
    """Security validation levels."""

    BASIC = auto()
    STRICT = auto()
    PARANOID = auto()


class RateLimitScope(Enum):
    """Rate limiting scopes."""

    GLOBAL = auto()
    PER_IP = auto()
    PER_USER = auto()
    PER_OPERATION = auto()


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    max_requests: int
    time_window_seconds: int
    scope: RateLimitScope = RateLimitScope.GLOBAL
    burst_allowance: int = 0


@dataclass
class ValidationRule:
    """Input validation rule."""

    field_name: str
    pattern: Optional[Pattern[str]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[Set[str]] = None
    custom_validator: Optional[Callable[[Any], bool]] = None
    required: bool = True


class SecurityValidator:
    """Input validation and sanitization for security-critical operations."""

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STRICT):
        self.validation_level = validation_level
        self.logger = get_stellar_logger()

        # Compile common patterns
        self._compile_validation_patterns()

    def _compile_validation_patterns(self) -> None:
        """Compile regex patterns for common validations."""
        self.patterns = {
            "stellar_public_key": re.compile(r"^G[A-Z2-7]{55}$"),
            "stellar_secret_key": re.compile(r"^S[A-Z2-7]{55}$"),
            "stellar_account_id": re.compile(r"^G[A-Z2-7]{55}$"),
            "key_id": re.compile(r"^[a-zA-Z0-9_-]{1,64}$"),
            "session_id": re.compile(r"^[a-zA-Z0-9_-]{16,128}$"),
            "derivation_path": re.compile(r"^m(/[0-9]+\'?){1,10}$"),
            "network_name": re.compile(r"^[a-zA-Z0-9_-]{1,32}$"),
            "safe_string": re.compile(r"^[a-zA-Z0-9_\s\-\.]{1,256}$"),
            "hex_string": re.compile(r"^[0-9a-fA-F]+$"),
            "base64_string": re.compile(r"^[A-Za-z0-9+/]*={0,2}$"),
        }

    def validate_stellar_public_key(self, public_key: str) -> bool:
        """Validate Stellar public key format."""
        if not isinstance(public_key, str):
            return False

        return bool(self.patterns["stellar_public_key"].match(public_key))

    def validate_stellar_secret_key(self, secret_key: str) -> bool:
        """Validate Stellar secret key format."""
        if not isinstance(secret_key, str):
            return False

        return bool(self.patterns["stellar_secret_key"].match(secret_key))

    def validate_key_id(self, key_id: str) -> bool:
        """Validate key ID format."""
        if not isinstance(key_id, str):
            return False

        return bool(self.patterns["key_id"].match(key_id))

    def validate_session_id(self, session_id: str) -> bool:
        """Validate session ID format."""
        if not isinstance(session_id, str):
            return False

        return bool(self.patterns["session_id"].match(session_id))

    def validate_derivation_path(self, path: str) -> bool:
        """Validate BIP-44 derivation path."""
        if not isinstance(path, str):
            return False

        return bool(self.patterns["derivation_path"].match(path))

    def validate_network_name(self, network: str) -> bool:
        """Validate network name."""
        if not isinstance(network, str):
            return False

        allowed_networks = {"testnet", "futurenet", "mainnet", "sandbox"}
        return network.lower() in allowed_networks

    def validate_input_length(self, value: Any, min_len: int = 0, max_len: int = 1000) -> bool:
        """Validate input length constraints."""
        if value is None:
            return min_len == 0

        length = len(str(value))
        return min_len <= length <= max_len

    def sanitize_string(self, value: str, max_length: int = 256) -> str:
        """Sanitize string input to prevent injection attacks."""
        if not isinstance(value, str):
            return ""

        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\'\\\x00-\x1F\x7F-\x9F]', "", value)

        # Truncate to max length
        sanitized = sanitized[:max_length]

        # Strip whitespace
        return sanitized.strip()

    def sanitize_error_message(self, error: Exception, operation: str) -> str:
        """Sanitize error messages to prevent information leakage."""
        error_str = str(error)

        # Remove potentially sensitive information
        sensitive_patterns = [
            r'password[=:]\s*[\'"]?[^\s\'"]+',  # Passwords
            r'token[=:]\s*[\'"]?[^\s\'"]+',  # Tokens
            r'key[=:]\s*[\'"]?[^\s\'"]+',  # Keys
            r'secret[=:]\s*[\'"]?[^\s\'"]+',  # Secrets
            r"/[a-zA-Z0-9_\-/]+\.key",  # File paths to keys
            r"S[A-Z2-7]{55}",  # Stellar secret keys
        ]

        sanitized = error_str
        for pattern in sensitive_patterns:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

        # Generic error for production
        if self.validation_level == ValidationLevel.PARANOID:
            return f"Operation failed: {operation}"

        return sanitized

    def validate_ip_address(self, ip_str: str) -> bool:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False

    def validate_rate_limit_config(self, config: RateLimitConfig) -> List[str]:
        """Validate rate limit configuration."""
        errors = []

        if config.max_requests <= 0:
            errors.append("max_requests must be positive")

        if config.time_window_seconds <= 0:
            errors.append("time_window_seconds must be positive")

        if config.burst_allowance < 0:
            errors.append("burst_allowance cannot be negative")

        return errors


class RateLimiter:
    """Rate limiter for security-critical operations."""

    def __init__(self) -> None:
        self.logger = get_stellar_logger()
        self._request_counts: Dict[str, Dict[str, int]] = {}
        self._window_starts: Dict[str, Dict[str, float]] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._lock = asyncio.Lock()

    def configure_operation(self, operation: str, config: RateLimitConfig) -> None:
        """Configure rate limiting for an operation."""
        validator = SecurityValidator()
        errors = validator.validate_rate_limit_config(config)

        if errors:
            raise ValueError(f"Invalid rate limit config: {', '.join(errors)}")

        self._configs[operation] = config
        self.logger.info(
            f"Configured rate limiting for operation: {operation}",
            category=LogCategory.SECURITY,
            operation=operation,
            max_requests=config.max_requests,
            time_window=config.time_window_seconds,
            scope=config.scope.name,
        )

    async def check_rate_limit(
        self, operation: str, identifier: Optional[str] = None, ip_address: Optional[str] = None
    ) -> bool:
        """Check if operation is within rate limits."""
        if operation not in self._configs:
            # No rate limiting configured - allow
            return True

        config = self._configs[operation]

        # Determine rate limit key based on scope
        if config.scope == RateLimitScope.GLOBAL:
            key = f"global:{operation}"
        elif config.scope == RateLimitScope.PER_IP and ip_address:
            key = f"ip:{ip_address}:{operation}"
        elif config.scope == RateLimitScope.PER_USER and identifier:
            key = f"user:{identifier}:{operation}"
        elif config.scope == RateLimitScope.PER_OPERATION:
            key = f"op:{operation}"
        else:
            key = f"global:{operation}"  # Fallback

        async with self._lock:
            current_time = time.time()

            # Initialize tracking if not exists
            if operation not in self._request_counts:
                self._request_counts[operation] = {}
                self._window_starts[operation] = {}

            # Check if time window has expired
            if key in self._window_starts[operation]:
                window_age = current_time - self._window_starts[operation][key]
                if window_age >= config.time_window_seconds:
                    # Reset window
                    self._request_counts[operation][key] = 0
                    self._window_starts[operation][key] = current_time
            else:
                # First request in this window
                self._request_counts[operation][key] = 0
                self._window_starts[operation][key] = current_time

            # Check current count
            current_count = self._request_counts[operation][key]
            max_allowed = config.max_requests + config.burst_allowance

            if current_count >= max_allowed:
                self.logger.warning(
                    f"Rate limit exceeded for operation: {operation}",
                    category=LogCategory.SECURITY,
                    operation=operation,
                    key=key,
                    current_count=current_count,
                    max_allowed=max_allowed,
                )
                return False

            # Increment counter
            self._request_counts[operation][key] += 1

            return True

    async def record_request(
        self, operation: str, identifier: Optional[str] = None, ip_address: Optional[str] = None
    ) -> None:
        """Record a request for rate limiting purposes."""
        # This is handled in check_rate_limit
        pass

    def get_rate_limit_status(self, operation: str) -> Dict[str, Any]:
        """Get current rate limit status for an operation."""
        if operation not in self._configs:
            return {"configured": False}

        config = self._configs[operation]
        op_counts = self._request_counts.get(operation, {})

        return {
            "configured": True,
            "max_requests": config.max_requests,
            "time_window_seconds": config.time_window_seconds,
            "scope": config.scope.name,
            "active_keys": len(op_counts),
            "total_requests": sum(op_counts.values()),
        }


def require_validation(
    public_key: Optional[str] = None,
    key_id: Optional[str] = None,
    session_id: Optional[str] = None,
    network: Optional[str] = None,
    max_length: int = 256,
) -> Callable[[Callable], Callable]:
    """Decorator to add input validation to methods."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            validator = SecurityValidator()

            # Validate public key if provided
            if public_key and public_key in kwargs:
                if not validator.validate_stellar_public_key(kwargs[public_key]):
                    raise ValueError(f"Invalid public key format: {public_key}")

            # Validate key ID if provided
            if key_id and key_id in kwargs:
                if not validator.validate_key_id(kwargs[key_id]):
                    raise ValueError(f"Invalid key ID format: {key_id}")

            # Validate session ID if provided
            if session_id and session_id in kwargs:
                if not validator.validate_session_id(kwargs[session_id]):
                    raise ValueError(f"Invalid session ID format: {session_id}")

            # Validate network if provided
            if network and network in kwargs:
                if not validator.validate_network_name(kwargs[network]):
                    raise ValueError(f"Invalid network name: {network}")

            # Length validation for string parameters
            for key, value in kwargs.items():
                if isinstance(value, str):
                    if not validator.validate_input_length(value, max_len=max_length):
                        raise ValueError(f"Input too long: {key}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_rate_limit(
    operation: str, scope: RateLimitScope = RateLimitScope.GLOBAL
) -> Callable[[Callable], Callable]:
    """Decorator to add rate limiting to methods."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get rate limiter instance (would need to be injected or global)
            # This is a placeholder - in real implementation, you'd need
            # access to a shared rate limiter instance
            rate_limiter = getattr(args[0], "_rate_limiter", None) if args else None

            if rate_limiter:
                # Extract identifier and IP from context if available
                identifier = kwargs.get("user_id") or kwargs.get("session_id")
                ip_address = kwargs.get("ip_address") or kwargs.get("client_ip")

                allowed = await rate_limiter.check_rate_limit(operation, identifier, ip_address)

                if not allowed:
                    raise Exception(f"Rate limit exceeded for operation: {operation}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Security configuration helpers


def create_default_rate_limits() -> Dict[str, RateLimitConfig]:
    """Create default rate limiting configuration."""
    return {
        "generate_keypair": RateLimitConfig(
            max_requests=10,
            time_window_seconds=60,
            scope=RateLimitScope.PER_USER,
            burst_allowance=2,
        ),
        "derive_key": RateLimitConfig(
            max_requests=50,
            time_window_seconds=60,
            scope=RateLimitScope.PER_USER,
            burst_allowance=5,
        ),
        "sign_transaction": RateLimitConfig(
            max_requests=100,
            time_window_seconds=60,
            scope=RateLimitScope.PER_USER,
            burst_allowance=10,
        ),
        "create_session": RateLimitConfig(
            max_requests=5,
            time_window_seconds=300,  # 5 minutes
            scope=RateLimitScope.PER_IP,
            burst_allowance=0,
        ),
        "backup_keys": RateLimitConfig(
            max_requests=1,
            time_window_seconds=3600,  # 1 hour
            scope=RateLimitScope.GLOBAL,
            burst_allowance=0,
        ),
    }


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize data for logging to prevent information leakage."""
    # validator = SecurityValidator()  # Unused
    sanitized = {}

    for key, value in data.items():
        if key.lower() in ["password", "secret", "key", "token", "private"]:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str) and len(value) > 100:
            sanitized[key] = value[:100] + "..."
        else:
            sanitized[key] = value

    return sanitized


async def test_security_validation() -> bool:
    """Test security validation components."""
    validator = SecurityValidator()
    rate_limiter = RateLimiter()

    # Configure rate limiting
    rate_limiter.configure_operation(
        "test_operation", RateLimitConfig(max_requests=3, time_window_seconds=10)
    )

    # Test validation
    tests = [
        ("valid_public_key", "GAHK7EEG2WWHVKDNT4CEQFZGKF2LGDSW2IVM4S5DP42RBW3K6BTODB4A", True),
        ("invalid_public_key", "invalid_key", False),
        ("valid_key_id", "stellar_test_123", True),
        ("invalid_key_id", "invalid key with spaces!", False),
    ]

    for test_name, value, expected in tests:
        if "public_key" in test_name:
            result = validator.validate_stellar_public_key(value)
        elif "key_id" in test_name:
            result = validator.validate_key_id(value)
        else:
            result = True

        print(f"{test_name}: {result == expected}")

    # Test rate limiting
    for i in range(5):
        allowed = await rate_limiter.check_rate_limit("test_operation")
        print(f"Request {i+1}: {'allowed' if allowed else 'blocked'}")
        await asyncio.sleep(0.1)

    return True
