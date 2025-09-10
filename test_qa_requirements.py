#!/usr/bin/env python3
"""
Quick verification test for QA requirements REQ-ORD-001 through REQ-ORD-005
"""

import asyncio
import sys
import os
from datetime import datetime
sys.path.insert(0, 'src')

from unittest.mock import AsyncMock, Mock
from decimal import Decimal
from stellar_sdk import Asset, Keypair

# Generate a valid test issuer public key
TEST_ISSUER_KEYPAIR = Keypair.random()
TEST_ISSUER = TEST_ISSUER_KEYPAIR.public_key

# Import our implementation
from hummingbot.connector.exchange.stellar.stellar_order_manager import (
    ModernStellarOrderManager,
    OrderStatus,
    EnhancedStellarOrder,
    OrderCancellationResult,
    OrderValidationError,
)


async def test_req_ord_001_order_placement():
    """Test REQ-ORD-001: Order placement contract"""
    print("Testing REQ-ORD-001: Order placement contract...")
    
    # Mock dependencies
    mock_chain = AsyncMock()
    mock_asset = AsyncMock()
    mock_obs = AsyncMock()
    
    # Mock asset manager to return supported assets
    mock_asset.validate_asset = AsyncMock(return_value=True)
    
    # Mock chain interface for order submission
    mock_chain.create_manage_offer_transaction = AsyncMock()
    mock_chain.submit_transaction = AsyncMock()
    
    # Mock successful transaction result
    mock_result = Mock()
    mock_result.hash = "test_tx_hash_123"
    mock_result.operations_results = [Mock()]
    mock_result.operations_results[0].offer_id = 12345
    mock_chain.submit_transaction.return_value = mock_result
    
    manager = ModernStellarOrderManager(mock_chain, mock_asset, mock_obs, "test_account", TEST_ISSUER_KEYPAIR)
    
    # Test order placement
    selling_asset = Asset.native()
    buying_asset = Asset("USDC", TEST_ISSUER)
    amount = Decimal("1000")
    price = Decimal("0.1")
    
    order = await manager.place_order(selling_asset, buying_asset, amount, price)
    
    # Verify REQ-ORD-001 requirements
    assert order.status == OrderStatus.OPEN  # Maps to "NEW" in tests
    assert order.order_id is not None
    assert len(order.order_id) > 0
    assert order.correlation_id is not None
    
    print("✓ REQ-ORD-001 PASSED: Order placement returns proper state")


async def test_req_ord_002_status_transitions():
    """Test REQ-ORD-002: Order status transitions"""
    print("Testing REQ-ORD-002: Order status transitions...")
    
    # Create mock order manager
    mock_chain = AsyncMock()
    mock_asset = AsyncMock()
    mock_obs = AsyncMock()
    mock_asset.validate_asset = AsyncMock(return_value=True)
    
    manager = ModernStellarOrderManager(mock_chain, mock_asset, mock_obs, "test_account", TEST_ISSUER_KEYPAIR)
    
    # Create a test order directly
    order = EnhancedStellarOrder(
        order_id="test_order_123",
        account_id="test_account",
        selling_asset=Asset.native(),
        buying_asset=Asset("USDC", TEST_ISSUER),
        amount=Decimal("1000"),
        price=Decimal("0.1"),
        status=OrderStatus.OPEN,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    # Add to active orders
    manager.active_orders[order.order_id] = order
    
    # Test partial fill transition: NEW -> PARTIALLY_FILLED
    success = await manager.update_order_fill(
        order.order_id,
        filled_amount=Decimal("500"),  # 50% filled
        remaining_amount=Decimal("500")
    )
    
    assert success is True
    updated_order = manager.active_orders[order.order_id]
    assert updated_order.status == OrderStatus.PARTIALLY_FILLED
    assert updated_order.fill_amount == Decimal("500")
    assert updated_order.fill_amount > Decimal("0")  # QA requirement
    
    # Test full fill transition: PARTIALLY_FILLED -> FILLED
    success = await manager.update_order_fill(
        order.order_id,
        filled_amount=Decimal("1000"),  # 100% filled
        remaining_amount=Decimal("0")
    )
    
    assert success is True
    # Order should be moved to history when fully filled
    assert order.order_id in manager.order_history
    filled_order = manager.order_history[order.order_id]
    assert filled_order.status == OrderStatus.FILLED
    assert filled_order.fill_amount == filled_order.amount  # QA requirement
    
    print("✓ REQ-ORD-002 PASSED: Order status transitions work correctly")


async def test_req_ord_003_cancellation_idempotency():
    """Test REQ-ORD-003: Order cancellation idempotency"""
    print("Testing REQ-ORD-003: Order cancellation idempotency...")
    
    # Setup
    mock_chain = AsyncMock()
    mock_asset = AsyncMock()
    mock_obs = AsyncMock()
    
    manager = ModernStellarOrderManager(mock_chain, mock_asset, mock_obs, "test_account", TEST_ISSUER_KEYPAIR)
    
    # Create and track an order
    order_id = "test_order_idempotent"
    order = EnhancedStellarOrder(
        order_id=order_id,
        account_id="test_account",
        selling_asset=Asset.native(),
        buying_asset=Asset("USDC", TEST_ISSUER),
        amount=Decimal("1000"),
        price=Decimal("0.1"),
        status=OrderStatus.OPEN,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        stellar_offer_id="12345"
    )
    
    manager.active_orders[order_id] = order
    manager.connector_order_ids.add(order_id)
    
    # Mock successful cancellation
    mock_chain.create_manage_offer_transaction = AsyncMock()
    mock_chain.submit_transaction = AsyncMock(return_value=Mock(hash="cancel_hash"))
    
    # First cancellation
    result1 = await manager.cancel_order(order_id)
    assert result1.success is True  # QA requirement
    
    # Second cancellation (should be idempotent)
    result2 = await manager.cancel_order(order_id) 
    assert result2.success is True  # QA requirement - idempotent
    
    print("✓ REQ-ORD-003 PASSED: Order cancellation is idempotent")


async def test_req_ord_004_external_order_protection():
    """Test REQ-ORD-004: External order cancellation protection"""
    print("Testing REQ-ORD-004: External order cancellation protection...")
    
    # Setup
    mock_chain = AsyncMock()
    mock_asset = AsyncMock()
    mock_obs = AsyncMock()
    
    manager = ModernStellarOrderManager(mock_chain, mock_asset, mock_obs, "test_account", TEST_ISSUER_KEYPAIR)
    
    # Try to cancel an external order (not in connector_order_ids)
    external_order_id = "external_order_not_ours"
    
    result = await manager.cancel_order(external_order_id)
    
    # Verify QA requirement
    assert result.error_code == "ExternalOrderCancellationAttempt"  # QA requirement
    assert result.success is False
    assert "not created by this connector" in result.error_message
    
    print("✓ REQ-ORD-004 PASSED: External order cancellation protection works")


async def test_req_ord_005_correlation_tracking():
    """Test REQ-ORD-005: Order history correlation tracking"""
    print("Testing REQ-ORD-005: Order history correlation tracking...")
    
    # Setup
    mock_chain = AsyncMock()
    mock_asset = AsyncMock()
    mock_obs = AsyncMock()
    mock_asset.validate_asset = AsyncMock(return_value=True)
    
    # Mock transaction submission
    mock_result = Mock()
    mock_result.hash = "test_tx_hash"
    mock_result.operations_results = [Mock()]
    mock_result.operations_results[0].offer_id = 12345
    mock_chain.create_manage_offer_transaction = AsyncMock()
    mock_chain.submit_transaction = AsyncMock(return_value=mock_result)
    
    manager = ModernStellarOrderManager(mock_chain, mock_asset, mock_obs, "test_account", TEST_ISSUER_KEYPAIR)
    
    # Create order
    order = await manager.place_order(
        Asset.native(),
        Asset("USDC", TEST_ISSUER),
        Decimal("1000"),
        Decimal("0.1")
    )
    
    # Verify QA requirements
    assert order.correlation_id is not None  # QA requirement
    assert len(order.order_history) > 0  # QA requirement
    
    # All history entries should have the same correlation ID
    for entry in order.order_history:
        assert entry.correlation_id == order.correlation_id
    
    print("✓ REQ-ORD-005 PASSED: Order correlation tracking works")


async def run_all_tests():
    """Run all QA requirement tests"""
    print("=" * 60)
    print("STELLAR ORDER MANAGER QA REQUIREMENTS VERIFICATION")
    print("=" * 60)
    
    try:
        await test_req_ord_001_order_placement()
        await test_req_ord_002_status_transitions()
        await test_req_ord_003_cancellation_idempotency()
        await test_req_ord_004_external_order_protection()
        await test_req_ord_005_correlation_tracking()
        
        print("=" * 60)
        print("🎉 ALL QA REQUIREMENTS PASSED!")
        print("✓ REQ-ORD-001: Order placement contract")
        print("✓ REQ-ORD-002: Order status transitions")  
        print("✓ REQ-ORD-003: Order cancellation idempotency")
        print("✓ REQ-ORD-004: External order cancellation protection")
        print("✓ REQ-ORD-005: Order history correlation tracking")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)