"""
Stellar Order Manager Implementation
Handle order lifecycle management for Stellar DEX
"""

import time
import hashlib
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from fractions import Fraction
from stellar_sdk import Asset, ManageBuyOffer, TransactionBuilder, Price
from enum import Enum
import logging


class OrderType(Enum):
    LIMIT = "LIMIT"


class TradeType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class StellarInFlightOrder:
    client_order_id: str
    trading_pair: str
    order_type: OrderType
    trade_type: TradeType
    amount: Decimal
    price: Decimal
    creation_timestamp: float
    stellar_offer_id: Optional[str] = None
    transaction_hash: Optional[str] = None
    last_state: str = "PENDING"
    cancel_tx_hash: Optional[str] = None


@dataclass
class PlaceOrderParams:
    trading_pair: str
    side: str
    amount: str
    price: str
    address: str
    base_asset: Asset
    counter_asset: Asset


class StellarOrderManager:
    """Handle order lifecycle management for Stellar DEX"""

    def __init__(self, chain_interface, wallet_address: str):
        self.chain = chain_interface
        self.wallet_address = wallet_address
        self.in_flight_orders: Dict[str, StellarInFlightOrder] = {}
        self.order_status_tracker = OrderStatusTracker()
        self.logger = logging.getLogger(__name__)

    async def create_order(
        self,
        trading_pair: str,
        order_type: OrderType,
        trade_type: TradeType,
        amount: Decimal,
        price: Decimal,
        **kwargs,
    ) -> str:
        """Create new order on Stellar DEX"""

        # Parse trading pair into Stellar assets
        base_asset, quote_asset = await self.parse_trading_pair(trading_pair)

        # Validate order parameters
        await self.validate_order_request(base_asset, quote_asset, trade_type, amount, price)

        # Generate order ID
        order_id = self.generate_order_id()

        # Determine order assets based on trade type
        if trade_type == TradeType.BUY:
            selling_asset = quote_asset
            buying_asset = base_asset
            selling_amount = str(amount * price)
        else:
            selling_asset = base_asset
            buying_asset = quote_asset
            selling_amount = str(amount)

        # Create manage offer operation
        operation = ManageBuyOffer(
            selling=selling_asset,
            buying=buying_asset,
            amount=selling_amount,
            price=self.convert_price_to_stellar_format(price),
            offer_id=0,  # 0 creates new offer
        )

        # Build and submit transaction
        try:
            account = await self.chain.load_account(self.wallet_address)

            transaction = (
                TransactionBuilder(
                    source_account=account,
                    network_passphrase=self.chain.network_passphrase,
                    base_fee=await self.chain.calculate_fee(),
                )
                .append_operation(operation)
                .set_timeout(30)
                .build()
            )

            # Sign transaction securely
            signed_transaction = await self.chain.key_manager.sign_transaction(
                transaction, self.wallet_address
            )

            # Submit to network
            result = await self.chain.submit_transaction(signed_transaction)

            # Track in-flight order
            in_flight_order = StellarInFlightOrder(
                client_order_id=order_id,
                trading_pair=trading_pair,
                order_type=order_type,
                trade_type=trade_type,
                amount=amount,
                price=price,
                creation_timestamp=time.time(),
                stellar_offer_id=self.extract_offer_id_from_result(result),
                transaction_hash=result.hash,
            )

            self.in_flight_orders[order_id] = in_flight_order

            return order_id

        except Exception as e:
            self.logger.error(f"Failed to create order: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel existing order"""

        if order_id not in self.in_flight_orders:
            raise ValueError(f"Order {order_id} not found")

        in_flight_order = self.in_flight_orders[order_id]

        try:
            # Create cancel offer operation (amount = 0 cancels)
            operation = ManageBuyOffer(
                selling=in_flight_order.selling_asset,
                buying=in_flight_order.buying_asset,
                amount="0",
                price=in_flight_order.price_stellar_format,
                offer_id=in_flight_order.stellar_offer_id,
            )

            # Build and submit cancellation transaction
            account = await self.chain.load_account(self.wallet_address)

            transaction = (
                TransactionBuilder(
                    source_account=account,
                    network_passphrase=self.chain.network_passphrase,
                    base_fee=await self.chain.calculate_fee(),
                )
                .append_operation(operation)
                .set_timeout(30)
                .build()
            )

            signed_transaction = await self.chain.key_manager.sign_transaction(
                transaction, self.wallet_address
            )

            result = await self.chain.submit_transaction(signed_transaction)

            # Update order status
            in_flight_order.last_state = "CANCELLED"
            in_flight_order.cancel_tx_hash = result.hash

            return True

        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def convert_price_to_stellar_format(self, price: Decimal) -> Price:
        """Convert decimal price to Stellar's rational price format"""

        # Stellar uses rational numbers (n/d) for precise price representation
        # This prevents floating point precision issues

        # Convert decimal to fraction with appropriate precision
        fraction = Fraction(price).limit_denominator(10000000)

        return Price(n=fraction.numerator, d=fraction.denominator)

    async def validate_order_request(
        self,
        base_asset: Asset,
        quote_asset: Asset,
        trade_type: TradeType,
        amount: Decimal,
        price: Decimal,
    ) -> None:
        """Validate order parameters before submission"""

        # Validate minimum order size
        if amount < Decimal("0.0000001"):
            raise ValueError("Amount below minimum precision")

        # Validate price precision
        if price <= Decimal("0"):
            raise ValueError("Price must be positive")

        # Validate assets are different
        if base_asset == quote_asset:
            raise ValueError("Base and quote assets cannot be the same")

        # Check trustlines exist for non-native assets
        if not base_asset.is_native():
            has_trustline = await self.check_trustline(self.wallet_address, base_asset)
            if not has_trustline:
                raise ValueError(f"No trustline found for {base_asset.code}")

        if not quote_asset.is_native():
            has_trustline = await self.check_trustline(self.wallet_address, quote_asset)
            if not has_trustline:
                raise ValueError(f"No trustline found for {quote_asset.code}")

    async def check_trustline(self, address: str, asset: Asset) -> bool:
        """Check if account has trustline for specific asset"""

        if asset.is_native():
            return True

        try:
            account = await self.chain.load_account(address)

            for balance in account.balances:
                if (
                    balance.asset_type != "native"
                    and balance.asset_code == asset.code
                    and balance.asset_issuer == asset.issuer
                ):
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Trustline check failed: {e}")
            return False

    async def parse_trading_pair(self, trading_pair: str) -> Tuple[Asset, Asset]:
        """Parse trading pair string into Stellar Asset objects"""

        base_symbol, quote_symbol = trading_pair.split("-")

        # Convert symbols to Stellar assets
        base_asset = await self.symbol_to_stellar_asset(base_symbol)
        quote_asset = await self.symbol_to_stellar_asset(quote_symbol)

        return base_asset, quote_asset

    async def symbol_to_stellar_asset(self, symbol: str) -> Asset:
        """Convert trading symbol to Stellar Asset object"""

        if symbol == "XLM":
            return Asset.native()

        # For other assets, resolve issuer from asset directory
        asset_info = await self.resolve_asset_issuer(symbol)

        if not asset_info:
            raise ValueError(f"Unable to resolve asset issuer for {symbol}")

        return Asset(asset_info["code"], asset_info["issuer"])

    async def resolve_asset_issuer(self, symbol: str) -> Optional[Dict]:
        """Resolve asset issuer from asset directory or configuration"""

        # This would typically query a configured asset directory
        # For now, return example USDC configuration
        asset_directory = {
            "USDC": {
                "code": "USDC",
                "issuer": "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN",
            }
        }

        return asset_directory.get(symbol)

    def generate_order_id(self) -> str:
        """Generate unique order identifier"""
        return hashlib.sha256(f"{self.wallet_address}{time.time()}{id(self)}".encode()).hexdigest()[
            :16
        ]

    def extract_offer_id_from_result(self, result) -> Optional[str]:
        """Extract Stellar offer ID from transaction result"""

        # Parse transaction result to find created offer ID
        # This would parse the transaction meta to find the offer ID
        # Simplified for now
        return f"offer_{int(time.time())}"


class OrderStatusTracker:
    """Track order status updates from Stellar network"""

    def __init__(self):
        self.tracked_orders: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)

    def track_order(self, order: StellarInFlightOrder) -> None:
        """Start tracking order status"""

        self.tracked_orders[order.client_order_id] = {
            "order": order,
            "last_check": time.time(),
            "check_interval": 5.0,  # Check every 5 seconds
        }

    async def update_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Update order status from network"""

        if order_id not in self.tracked_orders:
            return None

        tracking_info = self.tracked_orders[order_id]
        order = tracking_info["order"]

        try:
            # Query offer status from network
            if order.stellar_offer_id:
                offer_status = await self.query_offer_status(order.stellar_offer_id)

                if offer_status:
                    new_status = self.determine_order_status(offer_status)

                    if new_status != order.last_state:
                        order.last_state = new_status
                        tracking_info["last_check"] = time.time()

                        return OrderStatus(new_status)

            return None

        except Exception as e:
            self.logger.error(f"Order status update failed for {order_id}: {e}")
            return None

    async def query_offer_status(self, stellar_offer_id: str) -> Optional[Dict]:
        """Query offer status from Stellar network"""

        # This would query the Stellar network for offer status
        # Implementation depends on Stellar SDK methods
        # Simplified for now
        return {"id": stellar_offer_id, "amount": "100"}

    def determine_order_status(self, offer_data: Dict) -> str:
        """Determine order status from Stellar offer data"""

        if "amount" in offer_data:
            amount = Decimal(offer_data["amount"])

            if amount == 0:
                return "FILLED"
            else:
                return "OPEN"

        return "UNKNOWN"
