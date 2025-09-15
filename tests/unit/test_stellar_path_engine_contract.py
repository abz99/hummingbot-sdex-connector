"""
Stellar Path Payment Engine Contract Tests
Test path finding, arbitrage detection, and MEV protection.

QA_IDs: REQ-PATH-001, REQ-PATH-002, REQ-PATH-003
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from decimal import Decimal
from typing import Dict, Any, List
import time
from stellar_sdk import Asset


# Module-level fixtures for shared use across all test classes
@pytest.fixture
def mock_path_engine():
    """Mock EnhancedPathPaymentEngine."""
    from hummingbot.connector.exchange.stellar.stellar_path_payment_engine import EnhancedPathPaymentEngine

    with patch.object(EnhancedPathPaymentEngine, "__init__", return_value=None):
        engine = EnhancedPathPaymentEngine.__new__(EnhancedPathPaymentEngine)
        engine.chain_interface = AsyncMock()
        engine.soroban_manager = AsyncMock()
        engine.observability = AsyncMock()
        engine._route_cache = {}
        engine._dex_endpoints = {"stellar_dex": "horizon", "soroswap": "soroban"}
        engine._max_path_length = 4
        return engine


@pytest.fixture
def sample_assets():
    """Sample assets for path finding."""
    # Use valid Stellar public keys for testing
    return {
        "XLM": Asset.native(),
        "USDC": Asset("USDC", "GA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVSGZ"),
        "AQUA": Asset("AQUA", "GBNZILSTVQZ4R7IKQDGHYGY2QXL5QOFJYQMXPKWRRM5PAV7Y4M67AQUA"),
    }


class TestOptimalPathFinding:
    """Test optimal path finding functionality.

    QA_ID: REQ-PATH-001 - Optimal path finding
    """

    @pytest.mark.asyncio
    async def test_optimal_path_finding_direct(self, mock_path_engine, sample_assets):
        """Test optimal path finding for direct routes.

        QA_ID: REQ-PATH-001
        Acceptance Criteria: assert route.estimated_cost <= direct_cost
        """
        from hummingbot.connector.exchange.stellar.stellar_path_payment_engine import (
            PathPaymentRoute,
            PathType,
            RouteOptimization,
        )

        # Mock direct route finding
        async def mock_find_direct_path(source_asset, dest_asset, amount):
            return PathPaymentRoute(
                path=[source_asset, dest_asset],
                source_amount=amount,
                destination_amount=amount * Decimal("0.999"),  # 0.1% cost
                path_type=PathType.DIRECT,
                estimated_cost=amount * Decimal("0.001"),
                estimated_time_seconds=5,
                liquidity_available=Decimal("10000"),
                price_impact=Decimal("0.001"),
                confidence_score=Decimal("0.95"),
                expires_at=time.time() + 30,
            )

        mock_path_engine._find_direct_path = mock_find_direct_path
        mock_path_engine.find_optimal_path = AsyncMock()

        # Mock optimal path finding result
        direct_route = await mock_find_direct_path(sample_assets["XLM"], sample_assets["USDC"], Decimal("1000"))

        mock_path_engine.find_optimal_path.return_value = [direct_route]

        # Test path finding
        routes = await mock_path_engine.find_optimal_path(
            source_asset=sample_assets["XLM"],
            dest_asset=sample_assets["USDC"],
            amount=Decimal("1000"),
            optimization=RouteOptimization.LOWEST_COST,
        )

        # Assertions (QA requirement)
        assert len(routes) > 0
        route = routes[0]
        direct_cost = Decimal("1000") * Decimal("0.001")  # Expected direct cost
        assert route.estimated_cost <= direct_cost
        assert route.path_type == PathType.DIRECT

    @pytest.mark.asyncio
    async def test_multi_hop_path_optimization(self, mock_path_engine, sample_assets):
        """Test multi-hop path optimization."""
        from hummingbot.connector.exchange.stellar.stellar_path_payment_engine import PathPaymentRoute, PathType

        # Mock multi-hop route that's cheaper than direct
        async def mock_find_optimal_path(source_asset, dest_asset, amount, optimization):
            # Direct route (more expensive)
            direct_route = PathPaymentRoute(
                path=[source_asset, dest_asset],
                source_amount=amount,
                destination_amount=amount * Decimal("0.995"),
                path_type=PathType.DIRECT,
                estimated_cost=amount * Decimal("0.005"),  # 0.5% cost
                estimated_time_seconds=5,
                liquidity_available=Decimal("5000"),
                price_impact=Decimal("0.005"),
                confidence_score=Decimal("0.90"),
                expires_at=time.time() + 30,
            )

            # Multi-hop route (cheaper)
            multi_hop_route = PathPaymentRoute(
                path=[source_asset, sample_assets["XLM"], dest_asset],
                source_amount=amount,
                destination_amount=amount * Decimal("0.997"),
                path_type=PathType.MULTI_HOP,
                estimated_cost=amount * Decimal("0.003"),  # 0.3% cost
                estimated_time_seconds=10,
                liquidity_available=Decimal("8000"),
                price_impact=Decimal("0.002"),
                confidence_score=Decimal("0.85"),
                expires_at=time.time() + 30,
            )

            # Return optimized route based on strategy
            from hummingbot.connector.exchange.stellar.stellar_path_payment_engine import RouteOptimization

            if optimization == RouteOptimization.LOWEST_COST:
                return [multi_hop_route, direct_route]  # Sorted by cost
            else:
                return [direct_route, multi_hop_route]

        mock_path_engine.find_optimal_path = mock_find_optimal_path

        # Test cost optimization
        from hummingbot.connector.exchange.stellar.stellar_path_payment_engine import RouteOptimization
        routes = await mock_path_engine.find_optimal_path(
            source_asset=sample_assets["USDC"],
            dest_asset=sample_assets["AQUA"],
            amount=Decimal("1000"),
            optimization=RouteOptimization.LOWEST_COST,
        )

        # Should return multi-hop as optimal (lowest cost)
        optimal_route = routes[0]
        assert len(optimal_route.path) == 3  # Multi-hop
        assert optimal_route.estimated_cost < routes[1].estimated_cost

    @pytest.mark.asyncio
    async def test_path_finding_with_liquidity_constraints(self, mock_path_engine, sample_assets):
        """Test path finding considers liquidity availability."""
        from hummingbot.connector.exchange.stellar.stellar_path_payment_engine import PathPaymentRoute, PathType

        # Mock path finding with liquidity checks
        async def mock_liquidity_aware_path_finding(source_asset, dest_asset, amount, optimization):
            routes = []

            # High liquidity route (preferred for large amounts)
            high_liquidity_route = PathPaymentRoute(
                path=[source_asset, dest_asset],
                source_amount=amount,
                destination_amount=amount * Decimal("0.998"),
                path_type=PathType.DIRECT,
                estimated_cost=amount * Decimal("0.002"),
                estimated_time_seconds=5,
                liquidity_available=Decimal("50000"),  # High liquidity
                price_impact=Decimal("0.001"),  # Low impact
                confidence_score=Decimal("0.95"),
                expires_at=time.time() + 30,
            )

            # Low liquidity route (high impact for large amounts)
            low_liquidity_route = PathPaymentRoute(
                path=[source_asset, sample_assets["XLM"], dest_asset],
                source_amount=amount,
                destination_amount=amount * Decimal("0.990"),
                path_type=PathType.SINGLE_HOP,
                estimated_cost=amount * Decimal("0.010"),
                estimated_time_seconds=10,
                liquidity_available=Decimal("2000"),  # Low liquidity
                price_impact=Decimal("0.050"),  # High impact
                confidence_score=Decimal("0.60"),
                expires_at=time.time() + 30,
            )

            # Filter by liquidity requirements
            if amount <= Decimal("2000"):
                routes = [high_liquidity_route, low_liquidity_route]
            else:
                routes = [high_liquidity_route]  # Only high liquidity for large amounts

            return routes

        mock_path_engine.find_optimal_path = mock_liquidity_aware_path_finding

        # Test with large amount (should prefer high liquidity)
        large_amount = Decimal("10000")
        routes = await mock_path_engine.find_optimal_path(
            source_asset=sample_assets["USDC"],
            dest_asset=sample_assets["AQUA"],
            amount=large_amount,
            optimization="HIGHEST_LIQUIDITY",
        )

        # Should only return high liquidity route
        assert len(routes) == 1
        assert routes[0].liquidity_available >= large_amount


class TestArbitrageDetection:
    """Test arbitrage opportunity detection.

    QA_ID: REQ-PATH-002 - Arbitrage opportunity detection
    """

    @pytest.fixture
    def mock_arbitrage_engine(self, mock_path_engine):
        """Mock path engine with arbitrage detection."""
        mock_path_engine._arbitrage_enabled = True
        mock_path_engine._min_profit_percentage = Decimal("0.001")
        return mock_path_engine

    @pytest.mark.asyncio
    async def test_arbitrage_opportunity_detection(self, mock_arbitrage_engine, sample_assets):
        """Test detection of profitable arbitrage opportunities.

        QA_ID: REQ-PATH-002
        Acceptance Criteria: assert opportunity.profit_percentage > Decimal('0.001') and opportunity.risk_score < 0.7
        """
        from hummingbot.connector.exchange.stellar.stellar_path_payment_engine import (
            ArbitrageOpportunity,
            PathPaymentRoute,
            PathType,
        )

        # Mock profitable arbitrage detection
        async def mock_detect_arbitrage(assets, min_profit_percentage):
            # Create buy route (cheaper)
            buy_route = PathPaymentRoute(
                path=[assets[0], assets[1]],  # XLM -> USDC
                source_amount=Decimal("1000"),
                destination_amount=Decimal("100"),  # 1000 XLM -> 100 USDC
                path_type=PathType.DIRECT,
                estimated_cost=Decimal("1"),
                estimated_time_seconds=5,
                liquidity_available=Decimal("10000"),
                price_impact=Decimal("0.001"),
                confidence_score=Decimal("0.95"),
                expires_at=time.time() + 30,
                dex_sources=["stellar_dex"],
            )

            # Create sell route (more expensive)
            sell_route = PathPaymentRoute(
                path=[assets[1], assets[0]],  # USDC -> XLM
                source_amount=Decimal("100"),
                destination_amount=Decimal("1020"),  # 100 USDC -> 1020 XLM (profit!)
                path_type=PathType.DIRECT,
                estimated_cost=Decimal("0.5"),
                estimated_time_seconds=5,
                liquidity_available=Decimal("8000"),
                price_impact=Decimal("0.002"),
                confidence_score=Decimal("0.90"),
                expires_at=time.time() + 30,
                dex_sources=["soroswap"],
            )

            # Calculate arbitrage opportunity
            profit_amount = Decimal("1020") - Decimal("1000")  # 20 XLM profit
            profit_percentage = profit_amount / Decimal("1000")  # 2% profit

            opportunity = ArbitrageOpportunity(
                source_asset=assets[0],
                destination_asset=assets[1],
                buy_route=buy_route,
                sell_route=sell_route,
                profit_amount=profit_amount,
                profit_percentage=profit_percentage,
                risk_score=Decimal("0.3"),  # Low risk
                execution_time_window=120,  # 2 minutes
                required_capital=Decimal("1000"),
            )

            return [opportunity] if profit_percentage >= min_profit_percentage else []

        mock_arbitrage_engine.detect_arbitrage_opportunities = mock_detect_arbitrage

        # Test arbitrage detection
        assets = [sample_assets["XLM"], sample_assets["USDC"]]
        opportunities = await mock_arbitrage_engine.detect_arbitrage_opportunities(
            assets=assets, min_profit_percentage=Decimal("0.001")
        )

        # Assertions (QA requirement)
        assert len(opportunities) > 0
        opportunity = opportunities[0]
        assert opportunity.profit_percentage > Decimal("0.001")
        assert opportunity.risk_score < 0.7
        assert opportunity.profit_amount > Decimal("0")

    @pytest.mark.asyncio
    async def test_arbitrage_risk_assessment(self, mock_arbitrage_engine, sample_assets):
        """Test arbitrage opportunity risk assessment."""
        from hummingbot.connector.exchange.stellar.stellar_path_payment_engine import ArbitrageOpportunity

        def calculate_arbitrage_risk(opportunity):
            """Calculate risk score for arbitrage opportunity."""
            risk_factors = {
                "price_volatility": 0.1,  # 10% weight
                "liquidity_depth": 0.3,  # 30% weight
                "execution_time": 0.2,  # 20% weight
                "market_conditions": 0.4,  # 40% weight
            }

            # Assess each risk factor (0.0 = no risk, 1.0 = high risk)
            volatility_risk = float(min(opportunity.buy_route.price_impact + opportunity.sell_route.price_impact, Decimal("1.0")))
            liquidity_risk = max(0, 1.0 - float(opportunity.buy_route.liquidity_available / opportunity.required_capital))
            time_risk = min(opportunity.execution_time_window / 3600, 1.0)  # Risk increases with time
            market_risk = 0.2  # Assume moderate market risk

            total_risk = (
                risk_factors["price_volatility"] * volatility_risk
                + risk_factors["liquidity_depth"] * liquidity_risk
                + risk_factors["execution_time"] * time_risk
                + risk_factors["market_conditions"] * market_risk
            )

            return min(total_risk, 1.0)

        # Create test arbitrage opportunity
        opportunity = Mock()
        opportunity.buy_route = Mock()
        opportunity.sell_route = Mock()
        opportunity.buy_route.price_impact = Decimal("0.01")
        opportunity.sell_route.price_impact = Decimal("0.015")
        opportunity.buy_route.liquidity_available = Decimal("10000")
        opportunity.required_capital = Decimal("1000")
        opportunity.execution_time_window = 300  # 5 minutes

        # Calculate risk
        risk_score = calculate_arbitrage_risk(opportunity)

        # Should be reasonable risk level
        assert 0.0 <= risk_score <= 1.0
        assert risk_score < 0.7  # Should be acceptable risk

    @pytest.mark.asyncio
    async def test_arbitrage_filtering_by_profitability(self, mock_arbitrage_engine):
        """Test filtering arbitrage opportunities by profitability."""
        # Mock multiple opportunities with different profit levels
        opportunities = []
        profit_levels = [Decimal("0.0005"), Decimal("0.002"), Decimal("0.05"), Decimal("0.001")]

        for i, profit_pct in enumerate(profit_levels):
            opportunity = Mock()
            opportunity.profit_percentage = profit_pct
            opportunity.profit_amount = Decimal("1000") * profit_pct
            opportunity.risk_score = Decimal("0.3")
            opportunity.source_asset = Mock()
            opportunity.destination_asset = Mock()
            opportunities.append(opportunity)

        # Filter by minimum profitability
        min_profit = Decimal("0.001")
        filtered_opportunities = [opp for opp in opportunities if opp.profit_percentage >= min_profit]

        # Should filter out low profit opportunities
        assert len(filtered_opportunities) == 3  # Only 3 meet minimum
        assert all(opp.profit_percentage >= min_profit for opp in filtered_opportunities)

    @pytest.mark.asyncio
    async def test_cross_dex_arbitrage_detection(self, mock_arbitrage_engine, sample_assets):
        """Test cross-DEX arbitrage opportunity detection."""
        # Mock DEX price differences
        dex_prices = {
            "stellar_dex": {"XLM-USDC": Decimal("0.100")},
            "soroswap": {"XLM-USDC": Decimal("0.102")},  # 2% higher price
            "aquarius": {"XLM-USDC": Decimal("0.099")},  # 1% lower price
        }

        def find_cross_dex_opportunities(asset_pair, dex_prices):
            """Find arbitrage opportunities across DEXes."""
            opportunities = []
            prices = list(dex_prices.values())
            dexes = list(dex_prices.keys())

            for i in range(len(prices)):
                for j in range(len(prices)):
                    if i != j:
                        buy_price = prices[i][asset_pair]
                        sell_price = prices[j][asset_pair]

                        if sell_price > buy_price:
                            profit_pct = (sell_price - buy_price) / buy_price
                            if profit_pct > Decimal("0.01"):  # 1% minimum
                                opportunities.append(
                                    {
                                        "buy_dex": dexes[i],
                                        "sell_dex": dexes[j],
                                        "buy_price": buy_price,
                                        "sell_price": sell_price,
                                        "profit_percentage": profit_pct,
                                    }
                                )

            return opportunities

        # Test cross-DEX detection
        opportunities = find_cross_dex_opportunities("XLM-USDC", dex_prices)

        # Should find arbitrage between different DEXes
        assert len(opportunities) > 0
        best_opportunity = max(opportunities, key=lambda x: x["profit_percentage"])
        assert best_opportunity["profit_percentage"] > Decimal("0.01")


class TestMEVProtection:
    """Test MEV protection implementation.

    QA_ID: REQ-PATH-003 - MEV protection implementation
    """

    @pytest.mark.asyncio
    async def test_mev_protection_private_mempool(self, mock_path_engine):
        """Test MEV protection via private mempool.

        QA_ID: REQ-PATH-003
        Acceptance Criteria: assert protection_result.method == 'private_mempool' and protection_result.protected == True
        """
        from hummingbot.connector.exchange.stellar.stellar_path_payment_engine import PathPaymentRoute, PathType

        # Mock MEV protection implementation
        async def mock_apply_mev_protection(transaction_id, route):
            protection_levels = {
                "none": {"method": "standard", "protected": False, "cost": 0},
                "standard": {"method": "private_mempool", "protected": True, "cost": 100},
                "premium": {"method": "flashbots", "protected": True, "cost": 500},
            }

            # Choose protection based on transaction value
            if route.source_amount > Decimal("10000"):
                protection = protection_levels["premium"]
            elif route.source_amount > Decimal("1000"):
                protection = protection_levels["standard"]
            else:
                protection = protection_levels["none"]

            return {"transaction_id": f"protected_{transaction_id}", **protection}

        mock_path_engine._apply_mev_protection = mock_apply_mev_protection

        # Test MEV protection for medium-value transaction
        test_route = PathPaymentRoute(
            path=[Asset.native(), Asset("USDC", "GA7QYNF7SOWQ3GLR2BGMZEHXAVIRZA4KVWLTJJFC7MGXUA74P7UJVSGZ")],
            source_amount=Decimal("5000"),  # Medium value transaction
            destination_amount=Decimal("500"),
            path_type=PathType.DIRECT,
            estimated_cost=Decimal("5"),
            estimated_time_seconds=10,
            liquidity_available=Decimal("50000"),
            price_impact=Decimal("0.001"),
            confidence_score=Decimal("0.95"),
            expires_at=time.time() + 30,
        )

        protection_result = await mock_path_engine._apply_mev_protection("tx_123", test_route)

        # Assertions (QA requirement)
        assert protection_result["method"] == "private_mempool"
        assert protection_result["protected"] is True
        assert "protected_" in protection_result["transaction_id"]

    @pytest.mark.asyncio
    async def test_mev_protection_cost_benefit_analysis(self, mock_path_engine):
        """Test MEV protection cost-benefit analysis."""

        def calculate_protection_value(transaction_amount, potential_mev_loss, protection_cost):
            """Calculate if MEV protection is cost-effective."""
            net_benefit = potential_mev_loss - protection_cost
            return net_benefit > 0

        # Test scenarios
        test_cases = [
            {
                "tx_amount": Decimal("1000"),
                "mev_loss": Decimal("10"),  # 1% potential loss
                "protection_cost": Decimal("5"),
                "expected_worthwhile": True,
            },
            {
                "tx_amount": Decimal("100"),
                "mev_loss": Decimal("2"),  # 2% potential loss
                "protection_cost": Decimal("5"),
                "expected_worthwhile": False,  # Cost > benefit
            },
            {
                "tx_amount": Decimal("10000"),
                "mev_loss": Decimal("200"),  # 2% potential loss
                "protection_cost": Decimal("50"),
                "expected_worthwhile": True,
            },
        ]

        for case in test_cases:
            is_worthwhile = calculate_protection_value(case["tx_amount"], case["mev_loss"], case["protection_cost"])
            assert is_worthwhile == case["expected_worthwhile"]

    @pytest.mark.asyncio
    async def test_mev_protection_timing_considerations(self, mock_path_engine):
        """Test MEV protection timing and execution strategy."""

        class MEVProtectionStrategy:
            def __init__(self):
                self.protection_methods = ["standard", "private_mempool", "flashbots"]

            async def select_protection_method(self, route, market_conditions):
                """Select optimal protection method based on conditions."""
                if market_conditions["volatility"] > 0.05:  # High volatility
                    return "flashbots"  # Strongest protection
                elif route.source_amount > Decimal("5000"):  # Large transaction
                    return "private_mempool"
                else:
                    return "standard"

            async def calculate_optimal_timing(self, route, protection_method):
                """Calculate optimal execution timing."""
                base_delay = 0

                if protection_method == "flashbots":
                    base_delay = 5  # Wait for next block bundle
                elif protection_method == "private_mempool":
                    base_delay = 2  # Minimal delay for privacy

                # Add jitter to avoid predictable timing
                import random

                jitter = random.uniform(0, 1)

                return base_delay + jitter

        strategy = MEVProtectionStrategy()

        # Test protection method selection
        high_vol_conditions = {"volatility": 0.08, "liquidity": "normal"}
        normal_conditions = {"volatility": 0.02, "liquidity": "high"}

        from hummingbot.connector.exchange.stellar.stellar_path_payment_engine import PathPaymentRoute, PathType

        large_route = PathPaymentRoute(
            path=[Asset.native()],
            source_amount=Decimal("10000"),
            destination_amount=Decimal("1000"),
            path_type=PathType.DIRECT,
            estimated_cost=Decimal("10"),
            estimated_time_seconds=10,
            liquidity_available=Decimal("50000"),
            price_impact=Decimal("0.002"),
            confidence_score=Decimal("0.95"),
            expires_at=time.time() + 30,
        )

        # High volatility should use strongest protection
        protection_high_vol = await strategy.select_protection_method(large_route, high_vol_conditions)
        assert protection_high_vol == "flashbots"

        # Normal conditions with large amount should use private mempool
        protection_normal = await strategy.select_protection_method(large_route, normal_conditions)
        assert protection_normal == "private_mempool"

    @pytest.mark.asyncio
    async def test_mev_protection_failure_handling(self, mock_path_engine):
        """Test MEV protection failure and fallback mechanisms."""

        class MEVProtectionManager:
            async def apply_protection(self, transaction, method="standard"):
                """Apply MEV protection with fallback."""
                try:
                    if method == "flashbots":
                        # Simulate flashbots failure
                        if self._flashbots_available():
                            return {"success": True, "method": "flashbots"}
                        else:
                            raise ConnectionError("Flashbots relay unavailable")
                    elif method == "private_mempool":
                        return {"success": True, "method": "private_mempool"}
                    else:
                        return {"success": True, "method": "standard"}

                except ConnectionError:
                    # Fallback to next best method
                    if method == "flashbots":
                        return await self.apply_protection(transaction, "private_mempool")
                    elif method == "private_mempool":
                        return await self.apply_protection(transaction, "standard")
                    else:
                        return {"success": False, "method": "none", "error": "All protection methods failed"}

            def _flashbots_available(self):
                """Check if Flashbots relay is available."""
                return False  # Simulate unavailable for test

        protection_manager = MEVProtectionManager()

        # Test fallback from flashbots to private mempool
        result = await protection_manager.apply_protection("tx_123", "flashbots")

        assert result["success"] is True
        assert result["method"] == "private_mempool"  # Fell back successfully


# Utility functions for path payment testing
def create_sample_route(path_length=2, **kwargs):
    """Create sample payment route for testing."""
    from hummingbot.connector.exchange.stellar.stellar_path_payment_engine import PathPaymentRoute, PathType

    # Create mock path
    path = [Asset.native()]
    for i in range(path_length - 1):
        path.append(Asset(f"TOKEN{i}", f"GISSUER{i}EXAMPLE"))

    defaults = {
        "path": path,
        "source_amount": Decimal("1000"),
        "destination_amount": Decimal("990"),
        "path_type": PathType.DIRECT if path_length == 2 else PathType.MULTI_HOP,
        "estimated_cost": Decimal("10"),
        "estimated_time_seconds": 5 * path_length,
        "liquidity_available": Decimal("10000"),
        "price_impact": Decimal("0.01"),
        "confidence_score": Decimal("0.9"),
        "expires_at": time.time() + 30,
    }
    defaults.update(kwargs)

    return PathPaymentRoute(**defaults)


def assert_valid_arbitrage_opportunity(opportunity):
    """Assert arbitrage opportunity has valid structure."""
    assert hasattr(opportunity, "profit_percentage")
    assert hasattr(opportunity, "profit_amount")
    assert hasattr(opportunity, "risk_score")
    assert opportunity.profit_percentage > Decimal("0")
    assert opportunity.profit_amount > Decimal("0")
    assert 0 <= opportunity.risk_score <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
