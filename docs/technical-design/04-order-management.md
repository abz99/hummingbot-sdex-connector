# Stellar SDEX Connector: Order Management & Trading Logic

> **Part 4 of 7** - Technical Design Document v3.0
> Split from: `stellar_sdex_tdd_v3.md` (Lines 1072-1531)

## Advanced Order Management System

### 4.1 Enhanced Order Lifecycle Management

**Modern Order Management with Full Lifecycle Tracking**:

```python
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from typing import Optional, Dict, List
import uuid
from stellar_sdk.operation import ManageSellOffer, ManageBuyOffer

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"

@dataclass
class EnhancedStellarOrder:
    """Enhanced order representation with full lifecycle tracking"""

    # Core order data
    order_id: str
    trading_pair: str
    order_type: OrderType
    trade_type: TradeType
    amount: Decimal
    price: Decimal

    # Stellar-specific data
    stellar_offer_id: Optional[int] = None
    sequence_number: Optional[int] = None
    base_asset: Optional[Asset] = None
    counter_asset: Optional[Asset] = None

    # Lifecycle tracking
    status: OrderStatus = OrderStatus.PENDING
    created_timestamp: float = 0
    submitted_timestamp: Optional[float] = None
    last_update_timestamp: float = 0

    # Fill tracking
    filled_amount: Decimal = Decimal("0")
    remaining_amount: Optional[Decimal] = None
    average_fill_price: Optional[Decimal] = None
    fills: List[Dict] = None

    # Error tracking
    failure_reason: Optional[str] = None
    retry_count: int = 0

    def __post_init__(self):
        if self.fills is None:
            self.fills = []
        if self.remaining_amount is None:
            self.remaining_amount = self.amount

class ModernStellarOrderManager:
    """Enhanced order management with modern patterns"""

    def __init__(self, chain_interface, metrics_collector, logger):
        self.chain_interface = chain_interface
        self.metrics_collector = metrics_collector
        self.logger = logger

        # Order tracking
        self.active_orders: Dict[str, EnhancedStellarOrder] = {}
        self.order_history: Dict[str, EnhancedStellarOrder] = {}

        # Stellar-specific tracking
        self.stellar_offer_to_order: Dict[int, str] = {}
        self.sequence_locks: Dict[str, asyncio.Lock] = {}

        # Circuit breakers for order operations
        self.order_submission_cb = CircuitBreaker(failure_threshold=3, timeout=30)
        self.order_cancellation_cb = CircuitBreaker(failure_threshold=5, timeout=60)

    async def create_order(
        self,
        trading_pair: str,
        order_type: OrderType,
        trade_type: TradeType,
        amount: Decimal,
        price: Optional[Decimal] = None
    ) -> str:
        """Create order with enhanced validation and tracking"""

        # Generate unique order ID
        order_id = f"stellar_{uuid.uuid4().hex[:8]}"

        # Parse trading pair to Stellar assets
        base_asset, counter_asset = await self._parse_trading_pair(trading_pair)

        # Create enhanced order object
        order = EnhancedStellarOrder(
            order_id=order_id,
            trading_pair=trading_pair,
            order_type=order_type,
            trade_type=trade_type,
            amount=amount,
            price=price or Decimal("0"),
            base_asset=base_asset,
            counter_asset=counter_asset,
            created_timestamp=time.time()
        )

        # Validate order
        await self._validate_order(order)

        # Store order
        self.active_orders[order_id] = order

        # Log order creation
        self.logger.log_order_lifecycle(order_id, "created", {
            "trading_pair": trading_pair,
            "order_type": order_type.name,
            "trade_type": trade_type.name,
            "amount": str(amount),
            "price": str(price) if price else None
        })

        return order_id

    async def submit_order(self, order_id: str) -> bool:
        """Submit order to Stellar network with circuit breaker protection"""

        if order_id not in self.active_orders:
            raise ValueError(f"Order {order_id} not found")

        order = self.active_orders[order_id]

        try:
            # Submit with circuit breaker protection
            success = await self.order_submission_cb.call(
                self._submit_order_to_stellar, order
            )

            if success:
                order.status = OrderStatus.SUBMITTED
                order.submitted_timestamp = time.time()

                # Record metrics
                self.metrics_collector.record_order_placed(
                    order.trading_pair, order.trade_type.name
                )

                self.logger.log_order_lifecycle(order_id, "submitted", {
                    "stellar_offer_id": order.stellar_offer_id,
                    "sequence_number": order.sequence_number
                })

            return success

        except Exception as e:
            order.status = OrderStatus.FAILED
            order.failure_reason = str(e)
            order.retry_count += 1

            self.logger.log_error_with_context(e, {
                "order_id": order_id,
                "operation": "submit_order"
            })

            return False

    async def _submit_order_to_stellar(self, order: EnhancedStellarOrder) -> bool:
        """Submit order to Stellar network"""

        # Get account for sequence number
        account = await self.chain_interface.get_account_with_caching(
            self.chain_interface.keypair.public_key
        )

        # Build appropriate Stellar operation
        if order.trade_type == TradeType.BUY:
            operation = ManageBuyOffer(
                selling=order.counter_asset,
                buying=order.base_asset,
                amount=str(order.amount),
                price=str(order.price),
                offer_id=0  # 0 for new offer
            )
        else:  # SELL
            operation = ManageSellOffer(
                selling=order.base_asset,
                buying=order.counter_asset,
                amount=str(order.amount),
                price=str(order.price),
                offer_id=0  # 0 for new offer
            )

        # Build and sign transaction
        transaction = (
            TransactionBuilder(
                source_account=account,
                network_passphrase=self.chain_interface.network_passphrase,
                base_fee=self.chain_interface.base_fee
            )
            .add_operation(operation)
            .set_timeout(30)
            .build()
        )

        # Sign transaction securely
        signed_tx = await self.chain_interface.security_framework.sign_transaction_secure(
            transaction, self.chain_interface.keypair.public_key
        )

        # Submit transaction
        response = await self.chain_interface.submit_transaction_with_retry(signed_tx)

        # Extract offer ID from response
        if response.get("successful"):
            offer_id = self._extract_offer_id_from_response(response)
            order.stellar_offer_id = offer_id
            order.sequence_number = int(response.get("ledger", 0))

            # Map Stellar offer ID to our order ID
            if offer_id:
                self.stellar_offer_to_order[offer_id] = order.order_id

            return True

        return False

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order with enhanced error handling"""

        if order_id not in self.active_orders:
            self.logger.log_error_with_context(
                Exception("Order not found"),
                {"order_id": order_id, "operation": "cancel_order"}
            )
            return False

        order = self.active_orders[order_id]

        if not order.stellar_offer_id:
            # Order not yet submitted to network
            order.status = OrderStatus.CANCELLED
            self.active_orders.pop(order_id)
            return True

        try:
            # Cancel with circuit breaker protection
            success = await self.order_cancellation_cb.call(
                self._cancel_order_on_stellar, order
            )

            if success:
                order.status = OrderStatus.CANCELLED
                order.last_update_timestamp = time.time()

                # Move to history
                self.order_history[order_id] = order
                self.active_orders.pop(order_id)

                # Clean up mappings
                if order.stellar_offer_id in self.stellar_offer_to_order:
                    del self.stellar_offer_to_order[order.stellar_offer_id]

                # Record metrics
                self.metrics_collector.record_order_cancelled(order.trading_pair)

                self.logger.log_order_lifecycle(order_id, "cancelled", {
                    "stellar_offer_id": order.stellar_offer_id
                })

            return success

        except Exception as e:
            self.logger.log_error_with_context(e, {
                "order_id": order_id,
                "operation": "cancel_order"
            })
            return False

    async def _cancel_order_on_stellar(self, order: EnhancedStellarOrder) -> bool:
        """Cancel order on Stellar network"""

        account = await self.chain_interface.get_account_with_caching(
            self.chain_interface.keypair.public_key
        )

        # Build cancellation operation (amount=0 cancels offer)
        if order.trade_type == TradeType.BUY:
            operation = ManageBuyOffer(
                selling=order.counter_asset,
                buying=order.base_asset,
                amount="0",  # 0 amount cancels the offer
                price=str(order.price),
                offer_id=order.stellar_offer_id
            )
        else:
            operation = ManageSellOffer(
                selling=order.base_asset,
                buying=order.counter_asset,
                amount="0",  # 0 amount cancels the offer
                price=str(order.price),
                offer_id=order.stellar_offer_id
            )

        # Build and submit cancellation transaction
        transaction = (
            TransactionBuilder(
                source_account=account,
                network_passphrase=self.chain_interface.network_passphrase,
                base_fee=self.chain_interface.base_fee
            )
            .add_operation(operation)
            .set_timeout(30)
            .build()
        )

        signed_tx = await self.chain_interface.security_framework.sign_transaction_secure(
            transaction, self.chain_interface.keypair.public_key
        )

        response = await self.chain_interface.submit_transaction_with_retry(signed_tx)

        return response.get("successful", False)

    async def process_fill_event(self, offer_id: int, fill_data: Dict):
        """Process order fill event from network"""

        if offer_id not in self.stellar_offer_to_order:
            return  # Unknown offer

        order_id = self.stellar_offer_to_order[offer_id]
        order = self.active_orders.get(order_id)

        if not order:
            return  # Order no longer active

        # Process fill
        fill_amount = Decimal(str(fill_data.get("amount", "0")))
        fill_price = Decimal(str(fill_data.get("price", "0")))

        # Update order fill data
        order.filled_amount += fill_amount
        order.remaining_amount -= fill_amount
        order.last_update_timestamp = time.time()

        # Add fill to history
        order.fills.append({
            "amount": fill_amount,
            "price": fill_price,
            "timestamp": time.time(),
            "trade_id": fill_data.get("id")
        })

        # Calculate average fill price
        total_fill_value = sum(
            fill["amount"] * fill["price"] for fill in order.fills
        )
        order.average_fill_price = total_fill_value / order.filled_amount

        # Update status
        if order.remaining_amount <= Decimal("0.0000001"):  # Account for precision
            order.status = OrderStatus.FILLED

            # Move to history
            self.order_history[order_id] = order
            self.active_orders.pop(order_id)

            # Clean up mappings
            del self.stellar_offer_to_order[offer_id]

            # Record metrics
            self.metrics_collector.record_order_filled(order.trading_pair, fill_amount)

        else:
            order.status = OrderStatus.PARTIALLY_FILLED

        # Log fill event
        self.logger.log_order_lifecycle(order_id, "filled", {
            "fill_amount": str(fill_amount),
            "fill_price": str(fill_price),
            "total_filled": str(order.filled_amount),
            "remaining": str(order.remaining_amount),
            "status": order.status.value
        })

    def get_order_status(self, order_id: str) -> Optional[EnhancedStellarOrder]:
        """Get current order status"""
        return self.active_orders.get(order_id) or self.order_history.get(order_id)

    def get_active_orders(self) -> List[EnhancedStellarOrder]:
        """Get all active orders"""
        return list(self.active_orders.values())

    async def _validate_order(self, order: EnhancedStellarOrder):
        """Enhanced order validation"""

        # Validate trading pair
        if not order.base_asset or not order.counter_asset:
            raise ValueError(f"Invalid trading pair: {order.trading_pair}")

        # Validate amounts
        if order.amount <= 0:
            raise ValueError("Order amount must be positive")

        if order.order_type == OrderType.LIMIT and order.price <= 0:
            raise ValueError("Limit order price must be positive")

        # Check account balance and reserves
        account = await self.chain_interface.get_account_with_caching(
            self.chain_interface.keypair.public_key
        )

        # Validate sufficient balance
        if not await self._validate_sufficient_balance(order, account):
            raise ValueError("Insufficient balance for order")

        # Validate reserve requirements
        if not await self._validate_reserve_requirements(order, account):
            raise ValueError("Order would violate minimum reserve requirements")

    async def _validate_sufficient_balance(
        self,
        order: EnhancedStellarOrder,
        account: Account
    ) -> bool:
        """Validate sufficient balance for order"""

        required_asset = order.counter_asset if order.trade_type == TradeType.BUY else order.base_asset
        required_amount = order.amount * order.price if order.trade_type == TradeType.BUY else order.amount

        # Get balance for required asset
        balance = await self._get_asset_balance(account, required_asset)

        return balance >= required_amount

    async def _validate_reserve_requirements(
        self,
        order: EnhancedStellarOrder,
        account: Account
    ) -> bool:
        """Validate order doesn't violate reserve requirements"""

        # Calculate reserves after order placement
        estimated_reserves = await self.chain_interface.reserve_calculator.calculate_minimum_balance(account)

        # Add reserve for new offer
        estimated_reserves += Decimal("0.5")  # Base reserve for one offer

        # Check if account has sufficient XLM for reserves
        xlm_balance = await self._get_asset_balance(account, Asset.native())

        return xlm_balance >= estimated_reserves
```

---

## Related Documents

This document is part of the Stellar SDEX Connector Technical Design v3.0 series:

1. [01-architecture-foundation.md](./01-architecture-foundation.md) - Architecture & Technical Foundation
2. [02-security-framework.md](./02-security-framework.md) - Security Framework
3. [03-monitoring-observability.md](./03-monitoring-observability.md) - Monitoring & Observability
4. **[04-order-management.md](./04-order-management.md)** - Order Management & Trading Logic ⭐ *You are here*
5. [05-asset-management.md](./05-asset-management.md) - Asset Management & Risk
6. [06-deployment-operations.md](./06-deployment-operations.md) - Production Deployment & Operations
7. [07-implementation-guide.md](./07-implementation-guide.md) - Implementation Guide & Checklists

**Order Management-Specific References:**
- Order lifecycle state management
- Circuit breaker patterns for trading operations
- Stellar offer ID mapping and tracking
- Balance and reserve validation patterns