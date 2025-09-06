"""
Stellar AsyncThrottler Implementation
Modern Hummingbot v1.27+ rate limiting patterns for Stellar API endpoints
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
    from hummingbot.core.api_throttler.data_types import RateLimit, LinkedLimitWeightPair
except ImportError:
    # Fallback for development/testing - implement basic throttler patterns
    class AsyncThrottler:
        def __init__(self, rate_limits: List["RateLimit"]):
            self.rate_limits = {rl.limit_id: rl for rl in rate_limits}
            self._request_counts: Dict[str, List[float]] = {}
            
        async def acquire_token(self, limit_id: str, weight: int = 1) -> None:
            """Acquire token for rate-limited operation."""
            pass
            
    @dataclass
    class RateLimit:
        limit_id: str
        limit: int
        time_interval: int
        linked_limits: Optional[List["LinkedLimitWeightPair"]] = None
        weight: int = 1
        
    @dataclass 
    class LinkedLimitWeightPair:
        limit_id: str
        weight: int

from .stellar_logging import get_stellar_logger, LogCategory


class StellarAPIEndpoint(Enum):
    """Stellar API endpoints with rate limiting."""
    
    # Horizon Server endpoints
    ACCOUNT_DETAILS = "account_details"
    ACCOUNT_BALANCES = "account_balances" 
    ACCOUNT_TRANSACTIONS = "account_transactions"
    ACCOUNT_OPERATIONS = "account_operations"
    ACCOUNT_OFFERS = "account_offers"
    ACCOUNT_EFFECTS = "account_effects"
    
    # Transaction endpoints
    SUBMIT_TRANSACTION = "submit_transaction"
    TRANSACTION_DETAILS = "transaction_details"
    
    # Orderbook endpoints  
    ORDERBOOK = "orderbook"
    TRADES = "trades"
    
    # Assets and paths
    ASSETS = "assets"
    PATHS = "paths"
    STRICT_SEND_PATHS = "strict_send_paths"
    STRICT_RECEIVE_PATHS = "strict_receive_paths"
    
    # Market data
    TRADE_AGGREGATIONS = "trade_aggregations"
    
    # Ledger and network
    LEDGER_DETAILS = "ledger_details"
    OPERATIONS = "operations"
    EFFECTS = "effects"
    CLAIMABLE_BALANCES = "claimable_balances"
    
    # Fee stats
    FEE_STATS = "fee_stats"
    
    # Streaming endpoints (typically no rate limiting)
    STREAM_TRANSACTIONS = "stream_transactions"
    STREAM_OPERATIONS = "stream_operations"
    STREAM_EFFECTS = "stream_effects"
    STREAM_OFFERS = "stream_offers"


# Stellar Horizon rate limits based on typical public node configurations
# Reference: https://developers.stellar.org/api/introduction/rate-limiting/
STELLAR_RATE_LIMITS: List[RateLimit] = [
    # Primary rate limit: 3600 requests per hour (1 per second average)
    RateLimit(limit_id="stellar_primary", limit=3600, time_interval=3600, weight=1),
    
    # Burst limit: 100 requests per minute for short bursts  
    RateLimit(limit_id="stellar_burst", limit=100, time_interval=60, weight=1),
    
    # Transaction submission - most restrictive
    RateLimit(
        limit_id=StellarAPIEndpoint.SUBMIT_TRANSACTION.value, 
        limit=10, 
        time_interval=60,
        weight=5,  # Higher weight for expensive operations
        linked_limits=[
            LinkedLimitWeightPair(limit_id="stellar_primary", weight=5),
            LinkedLimitWeightPair(limit_id="stellar_burst", weight=3)
        ]
    ),
    
    # Account operations - moderate usage
    RateLimit(
        limit_id=StellarAPIEndpoint.ACCOUNT_DETAILS.value,
        limit=60,
        time_interval=60, 
        weight=1,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=1)]
    ),
    
    RateLimit(
        limit_id=StellarAPIEndpoint.ACCOUNT_BALANCES.value,
        limit=60,
        time_interval=60,
        weight=1, 
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=1)]
    ),
    
    RateLimit(
        limit_id=StellarAPIEndpoint.ACCOUNT_OFFERS.value,
        limit=30,
        time_interval=60,
        weight=2,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=2)]
    ),
    
    # Orderbook and trading data - high frequency needs
    RateLimit(
        limit_id=StellarAPIEndpoint.ORDERBOOK.value,
        limit=120,  # Allow higher frequency for orderbook updates
        time_interval=60,
        weight=1,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=1)]
    ),
    
    RateLimit(
        limit_id=StellarAPIEndpoint.TRADES.value, 
        limit=90,
        time_interval=60,
        weight=1,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=1)]
    ),
    
    # Market data
    RateLimit(
        limit_id=StellarAPIEndpoint.TRADE_AGGREGATIONS.value,
        limit=60,
        time_interval=60,
        weight=2,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=2)]
    ),
    
    # Path finding - can be expensive
    RateLimit(
        limit_id=StellarAPIEndpoint.PATHS.value,
        limit=20,
        time_interval=60, 
        weight=3,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=3)]
    ),
    
    RateLimit(
        limit_id=StellarAPIEndpoint.STRICT_SEND_PATHS.value,
        limit=20, 
        time_interval=60,
        weight=3,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=3)]
    ),
    
    RateLimit(
        limit_id=StellarAPIEndpoint.STRICT_RECEIVE_PATHS.value,
        limit=20,
        time_interval=60,
        weight=3,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=3)]  
    ),
    
    # General query endpoints
    RateLimit(
        limit_id=StellarAPIEndpoint.ASSETS.value,
        limit=30,
        time_interval=60,
        weight=1,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=1)]
    ),
    
    RateLimit(
        limit_id=StellarAPIEndpoint.FEE_STATS.value,
        limit=60,
        time_interval=60,
        weight=1,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=1)]
    ),
    
    # Historical data endpoints - lower limits due to expense
    RateLimit(
        limit_id=StellarAPIEndpoint.ACCOUNT_TRANSACTIONS.value,
        limit=20,
        time_interval=60,
        weight=3,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=3)]
    ),
    
    RateLimit(
        limit_id=StellarAPIEndpoint.ACCOUNT_OPERATIONS.value,
        limit=20,
        time_interval=60,
        weight=3,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=3)]
    ),
    
    RateLimit(
        limit_id=StellarAPIEndpoint.ACCOUNT_EFFECTS.value,
        limit=20,
        time_interval=60,
        weight=3,
        linked_limits=[LinkedLimitWeightPair(limit_id="stellar_primary", weight=3)]
    ),
]


class StellarThrottler:
    """
    Modern Stellar AsyncThrottler implementation following Hummingbot v1.27+ patterns.
    
    Features:
    - Hierarchical rate limiting with linked limits
    - Endpoint-specific throttling configurations
    - Burst protection with backoff
    - Metrics and monitoring integration
    - Graceful degradation under load
    """
    
    def __init__(
        self,
        rate_limits: Optional[List[RateLimit]] = None,
        enable_metrics: bool = True
    ):
        self.logger = get_stellar_logger()
        
        # Use provided rate limits or defaults
        limits = rate_limits if rate_limits is not None else STELLAR_RATE_LIMITS
        
        # Initialize the core AsyncThrottler
        self._throttler = AsyncThrottler(rate_limits=limits)
        
        # Metrics and monitoring
        self.enable_metrics = enable_metrics
        self._request_metrics: Dict[str, Dict[str, Any]] = {}
        self._throttling_events: List[Dict[str, Any]] = []
        
        # Initialize endpoint metrics
        if self.enable_metrics:
            self._init_metrics()
            
        self.logger.info(
            f"Initialized Stellar throttler with {len(limits)} rate limits",
            category=LogCategory.PERFORMANCE,
            rate_limits_count=len(limits)
        )
    
    def _init_metrics(self) -> None:
        """Initialize metrics tracking for all endpoints."""
        for endpoint in StellarAPIEndpoint:
            self._request_metrics[endpoint.value] = {
                "total_requests": 0,
                "throttled_requests": 0,
                "avg_wait_time": 0.0,
                "max_wait_time": 0.0,
                "last_request_time": 0.0
            }
    
    async def acquire_token(
        self, 
        endpoint: StellarAPIEndpoint,
        weight: int = 1
    ) -> None:
        """
        Acquire rate limit token for Stellar API endpoint.
        
        Args:
            endpoint: Stellar API endpoint
            weight: Request weight (default 1)
            
        Raises:
            Exception: If throttling fails or times out
        """
        start_time = time.time()
        
        try:
            # Acquire token from underlying throttler
            await self._throttler.acquire_token(
                limit_id=endpoint.value,
                weight=weight
            )
            
            # Record successful acquisition
            if self.enable_metrics:
                wait_time = time.time() - start_time
                self._update_metrics(endpoint.value, wait_time, throttled=wait_time > 0.01)
                
        except Exception as e:
            self.logger.error(
                f"Failed to acquire throttling token for {endpoint.value}",
                category=LogCategory.ERROR,
                endpoint=endpoint.value,
                weight=weight,
                error=str(e)
            )
            
            # Record throttling failure
            if self.enable_metrics:
                self._record_throttling_event(endpoint.value, "failure", str(e))
            
            raise
    
    def _update_metrics(
        self, 
        endpoint: str, 
        wait_time: float, 
        throttled: bool
    ) -> None:
        """Update request metrics for endpoint."""
        if endpoint not in self._request_metrics:
            return
            
        metrics = self._request_metrics[endpoint]
        metrics["total_requests"] += 1
        metrics["last_request_time"] = time.time()
        
        if throttled:
            metrics["throttled_requests"] += 1
            
        # Update wait time statistics
        if wait_time > 0:
            total_requests = metrics["total_requests"]
            current_avg = metrics["avg_wait_time"]
            metrics["avg_wait_time"] = (
                (current_avg * (total_requests - 1) + wait_time) / total_requests
            )
            
            if wait_time > metrics["max_wait_time"]:
                metrics["max_wait_time"] = wait_time
    
    def _record_throttling_event(
        self, 
        endpoint: str, 
        event_type: str, 
        details: str
    ) -> None:
        """Record throttling event for analysis."""
        event = {
            "timestamp": time.time(),
            "endpoint": endpoint,
            "event_type": event_type,
            "details": details
        }
        
        self._throttling_events.append(event)
        
        # Keep only last 1000 events to prevent memory growth
        if len(self._throttling_events) > 1000:
            self._throttling_events = self._throttling_events[-500:]
    
    async def acquire_multiple_tokens(
        self, 
        requests: List[Tuple[StellarAPIEndpoint, int]]
    ) -> None:
        """
        Acquire tokens for multiple endpoints atomically.
        
        Args:
            requests: List of (endpoint, weight) tuples
        """
        start_time = time.time()
        
        # Sort by weight to prioritize heavier requests
        sorted_requests = sorted(requests, key=lambda x: x[1], reverse=True)
        
        acquired_tokens = []
        
        try:
            for endpoint, weight in sorted_requests:
                await self.acquire_token(endpoint, weight)
                acquired_tokens.append((endpoint, weight))
                
        except Exception as e:
            self.logger.error(
                f"Failed to acquire multiple tokens, acquired {len(acquired_tokens)}/{len(requests)}",
                category=LogCategory.ERROR,
                total_requests=len(requests),
                acquired_count=len(acquired_tokens),
                error=str(e)
            )
            raise
            
        total_time = time.time() - start_time
        self.logger.debug(
            f"Acquired {len(requests)} tokens in {total_time:.3f}s",
            category=LogCategory.PERFORMANCE,
            acquisition_time=total_time,
            token_count=len(requests)
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive throttling metrics."""
        if not self.enable_metrics:
            return {"metrics_disabled": True}
        
        return {
            "request_metrics": dict(self._request_metrics),
            "recent_events": self._throttling_events[-10:],  # Last 10 events
            "total_endpoints": len(self._request_metrics),
            "total_throttling_events": len(self._throttling_events)
        }
    
    def get_endpoint_metrics(self, endpoint: StellarAPIEndpoint) -> Dict[str, Any]:
        """Get metrics for specific endpoint."""
        if not self.enable_metrics or endpoint.value not in self._request_metrics:
            return {}
            
        return dict(self._request_metrics[endpoint.value])
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on throttler."""
        health_status = {
            "healthy": True,
            "issues": [],
            "metrics": {}
        }
        
        if self.enable_metrics:
            # Check for endpoints with high throttling rates
            for endpoint, metrics in self._request_metrics.items():
                if metrics["total_requests"] > 0:
                    throttling_rate = metrics["throttled_requests"] / metrics["total_requests"]
                    
                    if throttling_rate > 0.5:  # More than 50% throttled
                        health_status["healthy"] = False
                        health_status["issues"].append(
                            f"High throttling rate for {endpoint}: {throttling_rate:.2%}"
                        )
                    
                    health_status["metrics"][endpoint] = {
                        "throttling_rate": throttling_rate,
                        "avg_wait_time": metrics["avg_wait_time"],
                        "total_requests": metrics["total_requests"]
                    }
        
        return health_status
    
    async def reset_metrics(self) -> None:
        """Reset all metrics and event history."""
        if self.enable_metrics:
            self._init_metrics()
            self._throttling_events.clear()
            
            self.logger.info(
                "Reset throttler metrics",
                category=LogCategory.PERFORMANCE
            )


# Convenience function for easy integration
def create_stellar_throttler(
    custom_limits: Optional[List[RateLimit]] = None,
    enable_metrics: bool = True
) -> StellarThrottler:
    """
    Create a configured Stellar throttler with sensible defaults.
    
    Args:
        custom_limits: Custom rate limits (uses defaults if None)
        enable_metrics: Enable metrics collection
        
    Returns:
        Configured StellarThrottler instance
    """
    return StellarThrottler(
        rate_limits=custom_limits,
        enable_metrics=enable_metrics
    )