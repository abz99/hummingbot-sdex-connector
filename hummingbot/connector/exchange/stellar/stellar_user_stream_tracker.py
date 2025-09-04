"""
Stellar User Stream Tracker
Real-time user data tracking and WebSocket management.
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from decimal import Decimal
import time


class StreamEventType(Enum):
    """Stream event types."""

    ACCOUNT_UPDATE = "account_update"
    TRANSACTION = "transaction"
    OPERATION = "operation"
    PAYMENT = "payment"
    OFFER_UPDATE = "offer_update"
    TRUSTLINE_UPDATE = "trustline_update"
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"


class StellarUserStreamData:
    """User stream data container."""

    def __init__(
        self,
        event_type: StreamEventType,
        account_id: str,
        data: Dict[str, Any],
        timestamp: float = None,
    ):
        self.event_type = event_type
        self.account_id = account_id
        self.data = data
        self.timestamp = timestamp or time.time()


class StellarUserStreamTracker:
    """Real-time user data tracking with WebSocket management."""

    def __init__(
        self,
        chain_interface: "ModernStellarChainInterface",
        observability: "StellarObservabilityFramework",
    ):
        self.chain_interface = chain_interface
        self.observability = observability

        # Stream management
        self._tracked_accounts: Set[str] = set()
        self._stream_sessions: Dict[str, aiohttp.ClientSession] = {}
        self._stream_tasks: Dict[str, asyncio.Task] = {}
        self._event_handlers: List[Callable[[StellarUserStreamData], None]] = []

        # Connection state
        self._connected: bool = False
        self._reconnect_attempts: Dict[str, int] = {}
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 5

        # Event queues
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start user stream tracker."""
        try:
            self._processing_task = asyncio.create_task(self._process_events())
            self._connected = True

            await self.observability.log_event(
                "user_stream_tracker_started", {"tracked_accounts": len(self._tracked_accounts)}
            )

        except Exception as e:
            await self.observability.log_error("user_stream_start_failed", e)
            raise

    async def stop(self):
        """Stop user stream tracker and cleanup."""
        self._connected = False

        # Stop all stream tasks
        for account_id, task in self._stream_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Close all sessions
        for session in self._stream_sessions.values():
            await session.close()

        # Stop processing task
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        self._stream_tasks.clear()
        self._stream_sessions.clear()

        await self.observability.log_event("user_stream_tracker_stopped")

    async def add_account(self, account_id: str):
        """Add account to stream tracking."""
        if account_id in self._tracked_accounts:
            return

        self._tracked_accounts.add(account_id)

        # Start streaming for this account
        if self._connected:
            await self._start_account_stream(account_id)

        await self.observability.log_event(
            "account_added_to_stream",
            {"account_id": account_id, "total_tracked": len(self._tracked_accounts)},
        )

    async def remove_account(self, account_id: str):
        """Remove account from stream tracking."""
        if account_id not in self._tracked_accounts:
            return

        self._tracked_accounts.discard(account_id)

        # Stop streaming for this account
        if account_id in self._stream_tasks:
            self._stream_tasks[account_id].cancel()
            del self._stream_tasks[account_id]

        if account_id in self._stream_sessions:
            await self._stream_sessions[account_id].close()
            del self._stream_sessions[account_id]

        await self.observability.log_event(
            "account_removed_from_stream",
            {"account_id": account_id, "total_tracked": len(self._tracked_accounts)},
        )

    def add_event_handler(self, handler: Callable[[StellarUserStreamData], None]):
        """Add event handler for stream data."""
        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: Callable[[StellarUserStreamData], None]):
        """Remove event handler."""
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    async def _start_account_stream(self, account_id: str):
        """Start streaming for a specific account."""
        if account_id in self._stream_tasks:
            return

        # Create session for this account
        session = aiohttp.ClientSession()
        self._stream_sessions[account_id] = session

        # Start streaming task
        task = asyncio.create_task(self._stream_account_events(account_id, session))
        self._stream_tasks[account_id] = task

    async def _stream_account_events(self, account_id: str, session: aiohttp.ClientSession):
        """Stream events for a specific account."""
        reconnect_attempts = 0

        while self._connected and reconnect_attempts < self._max_reconnect_attempts:
            try:
                # Build Horizon streaming URL
                # In real implementation, this would be the actual Horizon streaming endpoint
                horizon_url = self.chain_interface.config.horizon_urls[0]
                stream_url = f"{horizon_url}/accounts/{account_id}/effects"

                async with session.get(
                    stream_url,
                    params={"order": "desc", "cursor": "now"},
                    headers={"Accept": "text/event-stream"},
                ) as response:

                    if response.status == 200:
                        reconnect_attempts = 0  # Reset on successful connection

                        async for line in response.content:
                            if not self._connected:
                                break

                            try:
                                # Parse SSE data (simplified implementation)
                                line_str = line.decode("utf-8").strip()
                                if line_str.startswith("data: "):
                                    data_str = line_str[6:]  # Remove "data: " prefix
                                    await self._handle_stream_data(account_id, data_str)

                            except Exception as e:
                                await self.observability.log_error(
                                    "stream_data_parse_error", e, {"account_id": account_id}
                                )
                    else:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                        )

            except Exception as e:
                reconnect_attempts += 1

                await self.observability.log_error(
                    "stream_connection_error",
                    e,
                    {"account_id": account_id, "attempt": reconnect_attempts},
                )

                if reconnect_attempts < self._max_reconnect_attempts:
                    await asyncio.sleep(self._reconnect_delay * reconnect_attempts)
                else:
                    break

        # Connection failed permanently
        await self._event_queue.put(
            StellarUserStreamData(
                StreamEventType.CONNECTION_LOST,
                account_id,
                {"reason": "max_reconnect_attempts_exceeded"},
            )
        )

    async def _handle_stream_data(self, account_id: str, data_str: str):
        """Handle incoming stream data."""
        try:
            # In real implementation, this would parse actual Horizon SSE data
            # For now, create a stub event
            stream_data = StellarUserStreamData(
                StreamEventType.ACCOUNT_UPDATE, account_id, {"raw_data": data_str}
            )

            await self._event_queue.put(stream_data)

        except Exception as e:
            await self.observability.log_error(
                "stream_data_handle_error", e, {"account_id": account_id}
            )

    async def _process_events(self):
        """Process events from the queue."""
        while self._connected:
            try:
                # Get event with timeout to allow for shutdown
                stream_data = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)

                # Call all event handlers
                for handler in self._event_handlers:
                    try:
                        await handler(stream_data)
                    except Exception as e:
                        await self.observability.log_error(
                            "event_handler_error",
                            e,
                            {"handler": str(handler), "event_type": stream_data.event_type.value},
                        )

                # Mark task as done
                self._event_queue.task_done()

            except asyncio.TimeoutError:
                # Normal timeout, continue processing
                continue
            except Exception as e:
                await self.observability.log_error("event_processing_error", e)

    def get_connection_status(self) -> Dict[str, Any]:
        """Get stream connection status."""
        return {
            "connected": self._connected,
            "tracked_accounts": len(self._tracked_accounts),
            "active_streams": len(self._stream_tasks),
            "queued_events": self._event_queue.qsize(),
        }
