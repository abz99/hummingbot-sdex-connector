"""
Stellar Connection Manager
Optimized connection management with HTTP/2 support, connection pooling, and intelligent failover.
"""

import asyncio
import ssl
import time
from dataclasses import dataclass, field
from enum import auto, Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union
from urllib.parse import urlparse

import aiohttp

# import aiofiles  # Not used in current implementation
from aiohttp import ClientTimeout, TCPConnector, TraceConfig
from aiohttp.client_exceptions import ClientError

from .stellar_error_classification import ErrorContext, StellarErrorManager
from .stellar_logging import (
    get_request_logger,
    get_stellar_logger,
    LogCategory,
    with_correlation_id,
)
from .stellar_metrics import get_stellar_metrics


class ConnectionProtocol(Enum):
    """Supported connection protocols."""

    HTTP_1_1 = auto()
    HTTP_2 = auto()


class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = auto()
    LEAST_CONNECTIONS = auto()
    RESPONSE_TIME = auto()
    WEIGHTED = auto()


@dataclass
class ConnectionPool:
    """Connection pool configuration."""

    max_connections: int = 100
    max_connections_per_host: int = 30
    keepalive_timeout: int = 60
    enable_cleanup_closed: bool = True
    ttl_dns_cache: int = 300
    use_dns_cache: bool = True


@dataclass
class EndpointConfig:
    """Endpoint configuration with connection details."""

    url: str
    weight: float = 1.0
    max_retries: int = 3
    timeout: int = 30
    protocol: ConnectionProtocol = ConnectionProtocol.HTTP_2
    priority: int = 1  # Lower numbers = higher priority
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionMetrics:
    """Connection metrics tracking."""

    total_requests: int = 0
    active_connections: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_request_time: float = 0.0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0


class StellarConnectionManager:
    """
    Advanced connection manager with HTTP/2 support, intelligent load balancing,
    and automatic failover capabilities.
    """

    def __init__(
        self,
        pool_config: Optional[ConnectionPool] = None,
        load_balance_strategy: LoadBalanceStrategy = LoadBalanceStrategy.RESPONSE_TIME,
        enable_http2: bool = True,
    ):
        self.logger = get_stellar_logger()
        self.request_logger = get_request_logger()
        self.metrics = get_stellar_metrics()
        self.error_manager = StellarErrorManager()

        # Configuration
        self.pool_config = pool_config or ConnectionPool()
        self.load_balance_strategy = load_balance_strategy
        self.enable_http2 = enable_http2

        # Connection management
        self.sessions: Dict[str, aiohttp.ClientSession] = {}
        self.endpoints: Dict[str, List[EndpointConfig]] = {}
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}

        # Load balancing state
        self._round_robin_counters: Dict[str, int] = {}
        self._endpoint_health: Dict[str, Dict[str, float]] = (
            {}
        )  # service -> endpoint -> response_time

        # Circuit breakers
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the connection manager."""
        if self._running:
            return

        self._running = True

        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._connection_cleanup_loop())
        self._metrics_task = asyncio.create_task(self._metrics_collection_loop())

        self.logger.info(
            "Connection manager started",
            category=LogCategory.NETWORK,
            http2_enabled=self.enable_http2,
            load_balance_strategy=self.load_balance_strategy.name,
        )

    async def stop(self):
        """Stop the connection manager and clean up resources."""
        if not self._running:
            return

        self._running = False

        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._metrics_task:
            self._metrics_task.cancel()

        # Close all sessions
        for session in self.sessions.values():
            await session.close()

        self.sessions.clear()

        self.logger.info("Connection manager stopped", category=LogCategory.NETWORK)

    def add_endpoint_group(self, service_name: str, endpoints: List[EndpointConfig]):
        """Add a group of endpoints for a service."""
        self.endpoints[service_name] = sorted(endpoints, key=lambda x: x.priority)

        # Initialize metrics for each endpoint
        for endpoint in endpoints:
            endpoint_key = f"{service_name}:{endpoint.url}"
            if endpoint_key not in self.connection_metrics:
                self.connection_metrics[endpoint_key] = ConnectionMetrics()

        # Initialize health tracking
        if service_name not in self._endpoint_health:
            self._endpoint_health[service_name] = {}

        self.logger.info(
            f"Added endpoint group: {service_name}",
            category=LogCategory.NETWORK,
            endpoint_count=len(endpoints),
            endpoints=[ep.url for ep in endpoints],
        )

    def remove_endpoint_group(self, service_name: str):
        """Remove an endpoint group."""
        if service_name in self.endpoints:
            del self.endpoints[service_name]

        if service_name in self._endpoint_health:
            del self._endpoint_health[service_name]

        # Close session if exists
        if service_name in self.sessions:
            asyncio.create_task(self.sessions[service_name].close())
            del self.sessions[service_name]

        self.logger.info(f"Removed endpoint group: {service_name}", category=LogCategory.NETWORK)

    async def get_session(self, service_name: str) -> aiohttp.ClientSession:
        """Get or create a session for the service."""
        if service_name not in self.sessions:
            self.sessions[service_name] = await self._create_session(service_name)

        return self.sessions[service_name]

    async def _create_session(self, service_name: str) -> aiohttp.ClientSession:
        """Create an optimized HTTP session."""

        # SSL context with modern settings
        ssl_context = ssl.create_default_context()
        ssl_context.set_alpn_protocols(["h2", "http/1.1"] if self.enable_http2 else ["http/1.1"])
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        # TCP connector with optimizations
        connector = TCPConnector(
            limit=self.pool_config.max_connections,
            limit_per_host=self.pool_config.max_connections_per_host,
            keepalive_timeout=self.pool_config.keepalive_timeout,
            enable_cleanup_closed=self.pool_config.enable_cleanup_closed,
            ssl=ssl_context,
            use_dns_cache=self.pool_config.use_dns_cache,
            ttl_dns_cache=self.pool_config.ttl_dns_cache,
            # Enable HTTP/2 if supported
            force_close=not self.enable_http2,  # Keep connections open for HTTP/2
        )

        # Request timeout
        timeout = ClientTimeout(total=30, connect=10, sock_read=20, sock_connect=10)

        # Request tracing for metrics
        trace_config = TraceConfig()
        trace_config.on_request_start.append(self._on_request_start)
        trace_config.on_request_end.append(self._on_request_end)
        trace_config.on_request_exception.append(self._on_request_exception)
        trace_config.on_connection_create_start.append(self._on_connection_create)
        trace_config.on_connection_create_end.append(self._on_connection_created)

        # Create session
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "StellarConnector/3.0.0",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive" if self.enable_http2 else "close",
            },
            trace_configs=[trace_config],
            raise_for_status=False,  # Handle status codes manually
            read_bufsize=64 * 1024,  # 64KB read buffer
        )

        self.logger.info(
            f"Created session for {service_name}",
            category=LogCategory.NETWORK,
            http2_enabled=self.enable_http2,
            max_connections=self.pool_config.max_connections,
        )

        return session

    async def request(
        self, service_name: str, method: str, path: str = "", **kwargs: Any
    ) -> aiohttp.ClientResponse:
        """
        Make an HTTP request with intelligent endpoint selection and failover.
        """
        if service_name not in self.endpoints:
            raise ValueError(f"No endpoints configured for service: {service_name}")

        # Select best endpoint
        endpoint = await self._select_endpoint(service_name)
        if not endpoint:
            raise RuntimeError(f"No available endpoints for service: {service_name}")

        # Construct full URL
        url = endpoint.url.rstrip("/") + "/" + path.lstrip("/")

        # Get session
        session = await self.get_session(service_name)

        with with_correlation_id() as logger:
            # Log request start
            request_id = await self.request_logger.log_request(method, url, kwargs.get("headers"))

            # Create error context
            context = ErrorContext(
                operation=f"{method} {service_name}",
                endpoint=endpoint.url,
                network=service_name,
                request_id=request_id,
            )

            start_time = time.time()

            try:
                # Make the request
                async with session.request(method, url, **kwargs) as response:
                    response_time = time.time() - start_time

                    # Log response
                    await self.request_logger.log_response(
                        request_id, response.status, response_time
                    )

                    # Update metrics
                    await self._update_request_metrics(service_name, endpoint, True, response_time)

                    # Update endpoint health
                    self._update_endpoint_health(service_name, endpoint.url, response_time)

                    return response

            except Exception as e:
                response_time = time.time() - start_time

                # Log error
                await self.request_logger.log_request_error(request_id, e)

                # Update metrics
                await self._update_request_metrics(service_name, endpoint, False, response_time)

                # Handle error with recovery
                success, result = await self.error_manager.handle_error(
                    e,
                    context,
                    operation_callback=lambda: self._retry_request(
                        service_name, method, path, **kwargs
                    ),
                )

                if success and result:
                    return result

                # If error handling didn't succeed, re-raise
                raise

    async def _retry_request(
        self, service_name: str, method: str, path: str, **kwargs: Any
    ) -> aiohttp.ClientResponse:
        """Retry request with different endpoint selection."""
        # This will be called by error manager for retries
        return await self.request(service_name, method, path, **kwargs)

    async def _select_endpoint(self, service_name: str) -> Optional[EndpointConfig]:
        """Select the best endpoint using the configured load balancing strategy."""
        endpoints = [ep for ep in self.endpoints[service_name] if ep.enabled]

        if not endpoints:
            return None

        # Filter out circuit-broken endpoints
        available_endpoints = []
        for endpoint in endpoints:
            circuit_key = f"{service_name}:{endpoint.url}"
            if not self._is_circuit_open(circuit_key):
                available_endpoints.append(endpoint)

        if not available_endpoints:
            # All endpoints are circuit broken, try the primary
            return endpoints[0]

        if self.load_balance_strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin_select(service_name, available_endpoints)

        elif self.load_balance_strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(service_name, available_endpoints)

        elif self.load_balance_strategy == LoadBalanceStrategy.RESPONSE_TIME:
            return self._response_time_select(service_name, available_endpoints)

        elif self.load_balance_strategy == LoadBalanceStrategy.WEIGHTED:
            return self._weighted_select(service_name, available_endpoints)

        else:
            # Default to first available endpoint
            return available_endpoints[0]

    def _round_robin_select(
        self, service_name: str, endpoints: List[EndpointConfig]
    ) -> EndpointConfig:
        """Select endpoint using round-robin strategy."""
        if service_name not in self._round_robin_counters:
            self._round_robin_counters[service_name] = 0

        index = self._round_robin_counters[service_name] % len(endpoints)
        self._round_robin_counters[service_name] += 1

        return endpoints[index]

    def _least_connections_select(
        self, service_name: str, endpoints: List[EndpointConfig]
    ) -> EndpointConfig:
        """Select endpoint with least active connections."""
        min_connections = float("inf")
        selected_endpoint = endpoints[0]

        for endpoint in endpoints:
            endpoint_key = f"{service_name}:{endpoint.url}"
            metrics = self.connection_metrics.get(endpoint_key, ConnectionMetrics())

            if metrics.active_connections < min_connections:
                min_connections = metrics.active_connections
                selected_endpoint = endpoint

        return selected_endpoint

    def _response_time_select(
        self, service_name: str, endpoints: List[EndpointConfig]
    ) -> EndpointConfig:
        """Select endpoint with best response time."""
        if service_name not in self._endpoint_health:
            return endpoints[0]

        health_data = self._endpoint_health[service_name]
        best_time = float("inf")
        selected_endpoint = endpoints[0]

        for endpoint in endpoints:
            response_time = health_data.get(endpoint.url, float("inf"))
            if response_time < best_time:
                best_time = response_time
                selected_endpoint = endpoint

        return selected_endpoint

    def _weighted_select(
        self, service_name: str, endpoints: List[EndpointConfig]
    ) -> EndpointConfig:
        """Select endpoint using weighted random selection."""
        import random

        weights = [ep.weight for ep in endpoints]
        return random.choices(endpoints, weights=weights, k=1)[0]

    def _update_endpoint_health(self, service_name: str, endpoint_url: str, response_time: float):
        """Update endpoint health metrics."""
        if service_name not in self._endpoint_health:
            self._endpoint_health[service_name] = {}

        current_time = self._endpoint_health[service_name].get(endpoint_url, 0.0)

        # Exponential moving average
        alpha = 0.3
        new_time = alpha * response_time + (1 - alpha) * current_time
        self._endpoint_health[service_name][endpoint_url] = new_time

    def _is_circuit_open(self, circuit_key: str) -> bool:
        """Check if circuit breaker is open for an endpoint."""
        if circuit_key not in self._circuit_breakers:
            return False

        circuit = self._circuit_breakers[circuit_key]

        # Check if circuit is in timeout
        if circuit.get("open_until", 0) > time.time():
            return True

        # Reset circuit if timeout expired
        if "open_until" in circuit:
            del circuit["open_until"]
            circuit["failure_count"] = 0

        return False

    def _trigger_circuit_breaker(self, circuit_key: str):
        """Trigger circuit breaker for an endpoint."""
        if circuit_key not in self._circuit_breakers:
            self._circuit_breakers[circuit_key] = {"failure_count": 0}

        circuit = self._circuit_breakers[circuit_key]
        circuit["failure_count"] += 1

        # Open circuit after threshold failures
        if circuit["failure_count"] >= 5:
            circuit["open_until"] = time.time() + 60  # 60 second timeout

            self.logger.warning(
                f"Circuit breaker opened: {circuit_key}",
                category=LogCategory.NETWORK,
                failure_count=circuit["failure_count"],
            )

    async def _update_request_metrics(
        self, service_name: str, endpoint: EndpointConfig, success: bool, response_time: float
    ):
        """Update request metrics."""
        endpoint_key = f"{service_name}:{endpoint.url}"
        metrics = self.connection_metrics.get(endpoint_key, ConnectionMetrics())

        metrics.total_requests += 1
        metrics.last_request_time = time.time()

        if success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1
            # Trigger circuit breaker on failure
            self._trigger_circuit_breaker(endpoint_key)

        # Update average response time
        total_requests = metrics.total_requests
        current_avg = metrics.avg_response_time
        metrics.avg_response_time = (
            (current_avg * (total_requests - 1)) + response_time
        ) / total_requests

        self.connection_metrics[endpoint_key] = metrics

        # Update Prometheus metrics
        status = "success" if success else "error"
        self.metrics.record_network_request(service_name, "http", status, response_time)

    async def _connection_cleanup_loop(self):
        """Background task to clean up stale connections."""
        while self._running:
            try:
                current_time = time.time()

                # Clean up stale metrics
                for endpoint_key, metrics in list(self.connection_metrics.items()):
                    if current_time - metrics.last_request_time > 300:  # 5 minutes
                        metrics.active_connections = 0

                await asyncio.sleep(60)  # Run every minute

            except Exception as e:
                self.logger.error(
                    "Error in connection cleanup loop", category=LogCategory.NETWORK, exception=e
                )
                await asyncio.sleep(60)

    async def _metrics_collection_loop(self):
        """Background task to collect and report metrics."""
        while self._running:
            try:
                # Report connection metrics to Prometheus
                for endpoint_key, metrics in self.connection_metrics.items():
                    service_name = endpoint_key.split(":", 1)[0]
                    self.metrics.set_active_connections(service_name, metrics.active_connections)

                await asyncio.sleep(30)  # Report every 30 seconds

            except Exception as e:
                self.logger.error(
                    "Error in metrics collection loop", category=LogCategory.NETWORK, exception=e
                )
                await asyncio.sleep(30)

    # Request tracing callbacks
    async def _on_request_start(self, session, trace_config_ctx, params):
        """Called when request starts."""
        trace_config_ctx.start_time = time.time()

        # Update active connections
        service_name = getattr(trace_config_ctx, "service_name", "unknown")
        endpoint_key = f"{service_name}:{params.url}"

        if endpoint_key in self.connection_metrics:
            self.connection_metrics[endpoint_key].active_connections += 1

    async def _on_request_end(self, session, trace_config_ctx, params):
        """Called when request ends."""
        if hasattr(trace_config_ctx, "start_time"):
            duration = time.time() - trace_config_ctx.start_time

            # Update metrics would be handled in the main request method
            pass

    async def _on_request_exception(self, session, trace_config_ctx, params):
        """Called when request raises an exception."""
        # Update active connections
        service_name = getattr(trace_config_ctx, "service_name", "unknown")
        endpoint_key = f"{service_name}:{params.url}"

        if endpoint_key in self.connection_metrics:
            self.connection_metrics[endpoint_key].active_connections = max(
                0, self.connection_metrics[endpoint_key].active_connections - 1
            )

    async def _on_connection_create(self, session, trace_config_ctx, params):
        """Called when new connection is being created."""
        self.logger.debug(
            f"Creating new connection to {params.host}:{params.port}", category=LogCategory.NETWORK
        )

    async def _on_connection_created(self, session, trace_config_ctx, params):
        """Called when new connection is created."""
        self.logger.debug(
            f"Connection created to {params.host}:{params.port}", category=LogCategory.NETWORK
        )

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics."""
        total_connections = sum(m.active_connections for m in self.connection_metrics.values())
        total_requests = sum(m.total_requests for m in self.connection_metrics.values())
        successful_requests = sum(m.successful_requests for m in self.connection_metrics.values())

        return {
            "total_active_connections": total_connections,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "success_rate": successful_requests / max(total_requests, 1),
            "endpoints_configured": sum(len(eps) for eps in self.endpoints.values()),
            "sessions_active": len(self.sessions),
            "circuit_breakers_open": sum(
                1 for cb in self._circuit_breakers.values() if cb.get("open_until", 0) > time.time()
            ),
        }
