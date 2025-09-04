"""
Performance Optimizer
Connection pooling, caching, and request batching.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from decimal import Decimal
import aiohttp
from collections import defaultdict, deque
import hashlib
import json


@dataclass
class CacheEntry:
    """Cache entry with TTL."""

    data: Any
    expires_at: float
    hits: int = 0


@dataclass
class RequestBatch:
    """Batch of similar requests."""

    requests: List[Tuple[str, Dict[str, Any]]]  # (endpoint, params)
    callbacks: List[Callable[[Any], None]]
    created_at: float
    batch_id: str


class ConnectionPool:
    """Advanced connection pool manager."""

    def __init__(self, max_connections: int = 50, max_keepalive: int = 10):
        self.max_connections = max_connections
        self.max_keepalive = max_keepalive
        self._pools: Dict[str, aiohttp.ClientSession] = {}
        self._connection_counts: Dict[str, int] = defaultdict(int)

    async def get_session(self, base_url: str) -> aiohttp.ClientSession:
        """Get or create session for base URL."""
        if base_url not in self._pools:
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=self.max_keepalive,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )

            timeout = aiohttp.ClientTimeout(total=30, connect=10)

            self._pools[base_url] = aiohttp.ClientSession(
                connector=connector, timeout=timeout, headers={"User-Agent": "StellarConnector/3.0"}
            )

        return self._pools[base_url]

    async def close_all(self):
        """Close all connection pools."""
        for session in self._pools.values():
            await session.close()
        self._pools.clear()
        self._connection_counts.clear()


class RequestCache:
    """Intelligent request caching with TTL and LRU eviction."""

    def __init__(self, max_entries: int = 1000, default_ttl: int = 60):
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: deque = deque()  # LRU tracking

    def _generate_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key from endpoint and parameters."""
        key_data = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached response if valid."""
        key = self._generate_key(endpoint, params)

        if key in self._cache:
            entry = self._cache[key]

            if time.time() < entry.expires_at:
                # Valid cache hit
                entry.hits += 1
                self._access_order.remove(key)
                self._access_order.append(key)  # Move to end (most recent)
                return entry.data
            else:
                # Expired entry
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)

        return None

    def set(self, endpoint: str, params: Dict[str, Any], data: Any, ttl: Optional[int] = None):
        """Cache response data."""
        key = self._generate_key(endpoint, params)
        expires_at = time.time() + (ttl or self.default_ttl)

        # Evict oldest entries if at max capacity
        while len(self._cache) >= self.max_entries and self._access_order:
            oldest_key = self._access_order.popleft()
            if oldest_key in self._cache:
                del self._cache[oldest_key]

        self._cache[key] = CacheEntry(data=data, expires_at=expires_at, hits=0)

        # Track access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()
        self._access_order.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = time.time()
        valid_entries = sum(1 for entry in self._cache.values() if now < entry.expires_at)
        total_hits = sum(entry.hits for entry in self._cache.values())

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "total_hits": total_hits,
            "hit_rate": total_hits / max(len(self._cache), 1),
        }


class RequestBatcher:
    """Batch similar requests for efficiency."""

    def __init__(self, batch_size: int = 10, batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._pending_batches: Dict[str, RequestBatch] = {}
        self._batch_tasks: Dict[str, asyncio.Task] = {}

    async def add_request(
        self, batch_key: str, endpoint: str, params: Dict[str, Any], callback: Callable[[Any], None]
    ):
        """Add request to batch."""
        if batch_key not in self._pending_batches:
            # Create new batch
            self._pending_batches[batch_key] = RequestBatch(
                requests=[(endpoint, params)],
                callbacks=[callback],
                created_at=time.time(),
                batch_id=f"{batch_key}_{time.time()}",
            )

            # Schedule batch execution
            self._batch_tasks[batch_key] = asyncio.create_task(
                self._execute_batch_after_timeout(batch_key)
            )
        else:
            # Add to existing batch
            batch = self._pending_batches[batch_key]
            batch.requests.append((endpoint, params))
            batch.callbacks.append(callback)

            # Execute immediately if batch is full
            if len(batch.requests) >= self.batch_size:
                if batch_key in self._batch_tasks:
                    self._batch_tasks[batch_key].cancel()
                await self._execute_batch(batch_key)

    async def _execute_batch_after_timeout(self, batch_key: str):
        """Execute batch after timeout."""
        try:
            await asyncio.sleep(self.batch_timeout)
            await self._execute_batch(batch_key)
        except asyncio.CancelledError:
            pass  # Batch was executed early

    async def _execute_batch(self, batch_key: str):
        """Execute batched requests."""
        if batch_key not in self._pending_batches:
            return

        batch = self._pending_batches[batch_key]

        # Execute all requests in batch (simplified - would be optimized in real implementation)
        results = []
        for endpoint, params in batch.requests:
            # Placeholder result - real implementation would make actual API calls
            results.append({"status": "success", "data": params})

        # Call all callbacks with results
        for callback, result in zip(batch.callbacks, results):
            try:
                callback(result)
            except Exception:
                pass  # Don't let callback errors affect other callbacks

        # Cleanup
        del self._pending_batches[batch_key]
        if batch_key in self._batch_tasks:
            del self._batch_tasks[batch_key]


class StellarPerformanceOptimizer:
    """Performance optimization manager with caching, pooling, and batching."""

    def __init__(self, observability: "StellarObservabilityFramework"):
        self.observability = observability

        # Performance components
        self.connection_pool = ConnectionPool(max_connections=50, max_keepalive=10)
        self.request_cache = RequestCache(max_entries=1000, default_ttl=60)
        self.request_batcher = RequestBatcher(batch_size=10, batch_timeout=0.1)

        # Performance metrics
        self._request_times: deque = deque(maxlen=1000)
        self._cache_hits = 0
        self._cache_misses = 0
        self._batched_requests = 0
        self._total_requests = 0

        # Rate limiting
        self._request_semaphore = asyncio.Semaphore(50)  # Max concurrent requests

    async def initialize(self):
        """Initialize performance optimizer."""
        await self.observability.log_event(
            "performance_optimizer_initialized",
            {
                "connection_pool_size": self.connection_pool.max_connections,
                "cache_max_entries": self.request_cache.max_entries,
                "batch_size": self.request_batcher.batch_size,
            },
        )

    async def cleanup(self):
        """Cleanup performance optimizer resources."""
        await self.connection_pool.close_all()
        self.request_cache.clear()

        await self.observability.log_event("performance_optimizer_cleaned_up")

    async def make_request(
        self,
        base_url: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ) -> Any:
        """Make optimized HTTP request with caching."""
        params = params or {}
        self._total_requests += 1

        # Check cache first
        if use_cache:
            cached_result = self.request_cache.get(endpoint, params)
            if cached_result is not None:
                self._cache_hits += 1
                return cached_result
            else:
                self._cache_misses += 1

        # Make actual request
        start_time = time.time()

        async with self._request_semaphore:
            try:
                session = await self.connection_pool.get_session(base_url)
                full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

                async with session.get(full_url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Cache successful response
                        if use_cache:
                            self.request_cache.set(endpoint, params, result, cache_ttl)

                        return result
                    else:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                        )

            except Exception as e:
                await self.observability.log_error(
                    "optimized_request_failed",
                    e,
                    {"endpoint": endpoint, "params": params, "base_url": base_url},
                )
                raise
            finally:
                # Record request time
                request_time = time.time() - start_time
                self._request_times.append(request_time)

    async def batch_request(
        self, batch_key: str, base_url: str, endpoint: str, params: Dict[str, Any]
    ) -> Any:
        """Make batched request for efficiency."""
        self._batched_requests += 1

        # Create future to wait for result
        future = asyncio.Future()

        def callback(result):
            if not future.done():
                future.set_result(result)

        await self.request_batcher.add_request(batch_key, endpoint, params, callback)

        return await future

    def preload_cache(self, endpoint: str, params_list: List[Dict[str, Any]], data_list: List[Any]):
        """Preload cache with known data."""
        for params, data in zip(params_list, data_list):
            self.request_cache.set(endpoint, params, data)

        await self.observability.log_event(
            "cache_preloaded", {"endpoint": endpoint, "entries": len(params_list)}
        )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        cache_stats = self.request_cache.get_stats()

        avg_request_time = 0
        if self._request_times:
            avg_request_time = sum(self._request_times) / len(self._request_times)

        hit_rate = 0
        if self._cache_hits + self._cache_misses > 0:
            hit_rate = self._cache_hits / (self._cache_hits + self._cache_misses)

        return {
            "total_requests": self._total_requests,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": hit_rate,
            "batched_requests": self._batched_requests,
            "avg_request_time": avg_request_time,
            "cache_stats": cache_stats,
            "active_connections": len(self.connection_pool._pools),
        }

    def optimize_for_pattern(self, pattern: str, settings: Dict[str, Any]):
        """Optimize settings for specific usage patterns."""
        if pattern == "high_frequency_trading":
            # Optimize for low latency
            self.connection_pool.max_connections = 100
            self.request_cache.default_ttl = 5  # Short cache TTL
            self.request_batcher.batch_size = 5  # Smaller batches

        elif pattern == "market_data_polling":
            # Optimize for throughput
            self.request_cache.default_ttl = 30  # Longer cache TTL
            self.request_batcher.batch_size = 20  # Larger batches

        elif pattern == "account_monitoring":
            # Optimize for efficiency
            self.request_cache.default_ttl = 60  # Long cache TTL
            self.request_batcher.batch_timeout = 0.5  # Longer batch timeout

        await self.observability.log_event(
            "performance_pattern_optimized", {"pattern": pattern, "settings": settings}
        )
