"""
Stellar WebAssistant Factory Implementation
Modern Hummingbot v1.27+ web assistant patterns for Stellar API integration
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

try:
    from hummingbot.core.web_assistant.auth.auth_base import AuthBase
    from hummingbot.core.web_assistant.connections.data_types import (
        RESTMethod,
        RESTRequest,
        RESTResponse,
    )
    from hummingbot.core.web_assistant.rest_assistant import RESTAssistant
    from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
except ImportError:
    # Fallback for development/testing
    class WebAssistantsFactory:
        def __init__(self, **kwargs):
            pass

        def get_rest_assistant(self) -> "RESTAssistant":
            return RESTAssistant()

    class RESTAssistant:
        async def execute_request(self, request: "RESTRequest") -> "RESTResponse":
            pass

    class RESTMethod:
        GET = "GET"
        POST = "POST"
        PUT = "PUT"
        DELETE = "DELETE"

    @dataclass
    class RESTRequest:
        method: RESTMethod
        url: str
        headers: Optional[Dict[str, str]] = None
        params: Optional[Dict[str, Any]] = None
        data: Optional[Union[str, bytes, Dict]] = None
        is_auth_required: bool = False
        throttler_limit_id: Optional[str] = None

    @dataclass
    class RESTResponse:
        status: int
        headers: Dict[str, str]
        data: Any
        url: str


import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

from .stellar_error_classification import ErrorContext, StellarErrorManager
from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_throttler import create_stellar_throttler, StellarAPIEndpoint, StellarThrottler


@dataclass
class StellarEndpointConfig:
    """Configuration for Stellar API endpoints."""

    base_url: str
    timeout: int = 30
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    enable_ssl_verify: bool = True
    user_agent: str = "Hummingbot-Stellar-Connector/3.0"
    headers: Dict[str, str] = field(default_factory=dict)


class StellarAuthenticator:
    """Handle authentication for Stellar API requests."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key
        self.logger = get_stellar_logger()

    async def apply_auth(self, request: RESTRequest) -> RESTRequest:
        """Apply authentication to request if required."""
        if not request.is_auth_required:
            return request

        if not self.api_key:
            self.logger.warning(
                "Authentication required but no API key provided",
                category=LogCategory.SECURITY,
                url=request.url,
            )
            return request

        # Add API key to headers
        if request.headers is None:
            request.headers = {}

        request.headers["Authorization"] = f"Bearer {self.api_key}"

        return request


class StellarRESTAssistant:
    """
    Enhanced REST assistant for Stellar API with throttling and error handling.
    """

    def __init__(
        self,
        throttler: StellarThrottler,
        endpoint_config: StellarEndpointConfig,
        authenticator: Optional[StellarAuthenticator] = None,
        session: Optional[ClientSession] = None,
    ) -> None:
        self.throttler = throttler
        self.endpoint_config = endpoint_config
        self.authenticator = authenticator
        self.session = session
        self.logger = get_stellar_logger()
        self.error_manager = StellarErrorManager()

        # Request tracking
        self._active_requests: Dict[str, float] = {}
        self._request_id_counter = 0

    async def execute_request(
        self, request: RESTRequest, timeout: Optional[int] = None, **kwargs
    ) -> RESTResponse:
        """
        Execute REST request with throttling, retries, and error handling.

        Args:
            request: The REST request to execute
            timeout: Request timeout override
            **kwargs: Additional arguments

        Returns:
            RESTResponse with response data

        Raises:
            Exception: On request failure after retries
        """
        request_id = f"req_{self._request_id_counter}"
        self._request_id_counter += 1

        start_time = time.time()
        self._active_requests[request_id] = start_time

        try:
            # Apply authentication if required
            if self.authenticator:
                request = await self.authenticator.apply_auth(request)

            # Acquire throttling token
            endpoint = self._map_url_to_endpoint(request.url)
            if endpoint and request.throttler_limit_id:
                await self.throttler.acquire_token(endpoint)

            # Execute with retries
            response = await self._execute_with_retries(request, timeout)

            # Log successful request
            duration = time.time() - start_time
            self.logger.debug(
                "Request completed successfully",
                category=LogCategory.NETWORK,
                method=request.method,
                url=request.url,
                status=response.status,
                duration=duration,
                request_id=request_id,
            )

            return response

        except Exception as e:
            # Handle and classify error
            duration = time.time() - start_time
            error_context = ErrorContext(
                operation=f"{request.method} {request.url}",
                error_type=type(e).__name__,
                metadata={
                    "request_id": request_id,
                    "duration": duration,
                    "url": request.url,
                    "method": request.method,
                },
            )

            classified_error = self.error_manager.classify_error(e, error_context)

            self.logger.error(
                f"Request failed: {classified_error.message}",
                category=LogCategory.ERROR,
                method=request.method,
                url=request.url,
                error_type=classified_error.error_type.value,
                duration=duration,
                request_id=request_id,
                retry_count=getattr(self, "_current_retry", 0),
            )

            raise

        finally:
            # Clean up request tracking
            self._active_requests.pop(request_id, None)

    async def _execute_with_retries(
        self, request: RESTRequest, timeout: Optional[int] = None
    ) -> RESTResponse:
        """Execute request with retry logic."""
        max_retries = self.endpoint_config.max_retries
        backoff_factor = self.endpoint_config.retry_backoff_factor

        last_exception = None

        for retry_count in range(max_retries + 1):
            self._current_retry = retry_count

            try:
                return await self._single_request(request, timeout)

            except Exception as e:
                last_exception = e

                # Don't retry on certain errors
                if not self._should_retry_error(e):
                    raise

                if retry_count < max_retries:
                    # Calculate backoff delay
                    delay = backoff_factor**retry_count

                    self.logger.warning(
                        f"Request failed, retrying in {delay:.1f}s (attempt {retry_count + 1}/{max_retries + 1})",
                        category=LogCategory.NETWORK,
                        url=request.url,
                        retry_count=retry_count,
                        delay=delay,
                        error=str(e),
                    )

                    await asyncio.sleep(delay)

        # All retries exhausted
        raise last_exception

    async def _single_request(
        self, request: RESTRequest, timeout: Optional[int] = None
    ) -> RESTResponse:
        """Execute single HTTP request."""
        request_timeout = timeout or self.endpoint_config.timeout

        # Prepare request parameters
        method = getattr(aiohttp.ClientSession, request.method.lower())
        url = self._build_url(request.url)

        headers = dict(self.endpoint_config.headers)
        if request.headers:
            headers.update(request.headers)

        # Set user agent
        headers["User-Agent"] = self.endpoint_config.user_agent

        # Use provided session or create new one
        if self.session:
            session = self.session
            close_session = False
        else:
            session = aiohttp.ClientSession(
                timeout=ClientTimeout(total=request_timeout),
                connector=TCPConnector(verify_ssl=self.endpoint_config.enable_ssl_verify),
            )
            close_session = True

        try:
            async with method(
                url, headers=headers, params=request.params, data=request.data
            ) as response:
                # Read response data
                if response.content_type == "application/json":
                    data = await response.json()
                else:
                    data = await response.text()

                return RESTResponse(
                    status=response.status,
                    headers=dict(response.headers),
                    data=data,
                    url=str(response.url),
                )

        finally:
            if close_session:
                await session.close()

    def _build_url(self, path: str) -> str:
        """Build complete URL from path."""
        if path.startswith(("http://", "https://")):
            return path
        return urljoin(self.endpoint_config.base_url, path)

    def _map_url_to_endpoint(self, url: str) -> Optional[StellarAPIEndpoint]:
        """Map URL to Stellar API endpoint for throttling."""
        # Extract path from URL
        parsed = urlparse(url)
        path = parsed.path.lower().strip("/")

        # Map common paths to endpoints
        endpoint_mapping = {
            "accounts": StellarAPIEndpoint.ACCOUNT_DETAILS,
            "transactions": (
                StellarAPIEndpoint.SUBMIT_TRANSACTION
                if parsed.query
                else StellarAPIEndpoint.TRANSACTION_DETAILS
            ),
            "order_book": StellarAPIEndpoint.ORDERBOOK,
            "trades": StellarAPIEndpoint.TRADES,
            "assets": StellarAPIEndpoint.ASSETS,
            "paths": StellarAPIEndpoint.PATHS,
            "trade_aggregations": StellarAPIEndpoint.TRADE_AGGREGATIONS,
            "fee_stats": StellarAPIEndpoint.FEE_STATS,
        }

        for path_segment, endpoint in endpoint_mapping.items():
            if path_segment in path:
                return endpoint

        return None

    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if error should trigger retry."""
        # Retry on network/temporary errors
        retry_exceptions = (
            aiohttp.ClientConnectionError,
            aiohttp.ClientTimeoutError,
            aiohttp.ServerTimeoutError,
            asyncio.TimeoutError,
        )

        if isinstance(error, retry_exceptions):
            return True

        # Retry on certain HTTP status codes
        if hasattr(error, "status"):
            retry_statuses = {429, 500, 502, 503, 504}
            return error.status in retry_statuses

        return False

    def get_active_request_count(self) -> int:
        """Get number of active requests."""
        return len(self._active_requests)

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on REST assistant."""
        return {
            "active_requests": len(self._active_requests),
            "endpoint_config": {
                "base_url": self.endpoint_config.base_url,
                "timeout": self.endpoint_config.timeout,
                "max_retries": self.endpoint_config.max_retries,
            },
            "throttler_healthy": (
                (await self.throttler.health_check())["healthy"] if self.throttler else True
            ),
        }


class StellarWebAssistantsFactory:
    """
    Factory for creating Stellar-specific web assistants with proper configuration.

    Follows Hummingbot v1.27+ patterns for web assistant management.
    """

    def __init__(
        self,
        endpoint_config: Optional[StellarEndpointConfig] = None,
        throttler: Optional[StellarThrottler] = None,
        api_key: Optional[str] = None,
        shared_session: Optional[ClientSession] = None,
        # Compatibility parameters for tests
        auth: Optional[Any] = None,
    ) -> None:
        self.logger = get_stellar_logger()

        # Default configuration for Stellar Mainnet
        self.endpoint_config = endpoint_config or StellarEndpointConfig(
            base_url="https://horizon.stellar.org",
            timeout=30,
            max_retries=3,
            retry_backoff_factor=2.0,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

        # Create throttler if not provided
        self.throttler = throttler or create_stellar_throttler()

        # Create authenticator if API key provided
        self.authenticator = StellarAuthenticator(api_key) if api_key else None

        # Shared session for connection pooling
        self.shared_session = shared_session

        self.logger.info(
            "Initialized Stellar WebAssistants Factory",
            category=LogCategory.NETWORK,
            base_url=self.endpoint_config.base_url,
            has_authenticator=self.authenticator is not None,
            has_shared_session=self.shared_session is not None,
        )

    def get_rest_assistant(self) -> StellarRESTAssistant:
        """
        Create a new REST assistant instance.

        Returns:
            Configured StellarRESTAssistant
        """
        return StellarRESTAssistant(
            throttler=self.throttler,
            endpoint_config=self.endpoint_config,
            authenticator=self.authenticator,
            session=self.shared_session,
        )

    async def create_shared_session(self) -> ClientSession:
        """
        Create a shared session for connection pooling.

        Returns:
            Configured aiohttp ClientSession
        """
        connector = TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Connections per host
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            verify_ssl=self.endpoint_config.enable_ssl_verify,
            enable_cleanup_closed=True,
        )

        timeout = ClientTimeout(total=self.endpoint_config.timeout)

        session = ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": self.endpoint_config.user_agent},
        )

        self.shared_session = session

        self.logger.info(
            "Created shared HTTP session",
            category=LogCategory.NETWORK,
            max_connections=100,
            timeout=self.endpoint_config.timeout,
        )

        return session

    async def close_shared_session(self) -> None:
        """Close shared session and cleanup resources."""
        if self.shared_session and not self.shared_session.closed:
            await self.shared_session.close()
            self.shared_session = None

            self.logger.info("Closed shared HTTP session", category=LogCategory.NETWORK)

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        throttler_health = await self.throttler.health_check()

        return {
            "factory_healthy": True,
            "endpoint_config": {
                "base_url": self.endpoint_config.base_url,
                "timeout": self.endpoint_config.timeout,
            },
            "throttler_health": throttler_health,
            "shared_session_active": self.shared_session is not None
            and not self.shared_session.closed,
            "authenticator_configured": self.authenticator is not None,
        }


# Alias for backward compatibility with test expectations
StellarWebAssistantFactory = StellarWebAssistantsFactory


# Convenience functions for easy integration
def create_stellar_web_factory(
    base_url: str = "https://horizon.stellar.org",
    api_key: Optional[str] = None,
    timeout: int = 30,
    max_retries: int = 3,
) -> StellarWebAssistantsFactory:
    """
    Create a configured Stellar web assistants factory.

    Args:
        base_url: Stellar Horizon server URL
        api_key: Optional API key for authenticated requests
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        Configured StellarWebAssistantsFactory
    """
    endpoint_config = StellarEndpointConfig(
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )

    return StellarWebAssistantsFactory(endpoint_config=endpoint_config, api_key=api_key)


def create_testnet_web_factory(
    api_key: Optional[str] = None, **kwargs
) -> StellarWebAssistantsFactory:
    """Create factory configured for Stellar testnet."""
    return create_stellar_web_factory(
        base_url="https://horizon-testnet.stellar.org", api_key=api_key, **kwargs
    )
