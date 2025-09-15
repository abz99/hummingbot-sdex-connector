"""
AI Trading Data Pipeline for Stellar Hummingbot Connector v3.0
Advanced data collection and processing for AI/ML trading models
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging
from abc import ABC, abstractmethod

from stellar_sdk import Server, Asset, Keypair
from stellar_sdk.exceptions import BaseRequestError


@dataclass
class MarketDataPoint:
    """Structured market data point for AI processing."""

    timestamp: datetime
    asset_pair: str
    price: float
    volume: float
    spread: float
    bid: float
    ask: float
    trades_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SentimentData:
    """Social sentiment data structure."""

    timestamp: datetime
    source: str
    sentiment_score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    text_sample: str
    keywords: List[str] = field(default_factory=list)


@dataclass
class OnChainMetrics:
    """On-chain blockchain metrics."""

    timestamp: datetime
    network: str
    transaction_count: int
    unique_addresses: int
    total_volume: float
    avg_fee: float
    network_congestion: float
    soroban_activity: Dict[str, Any] = field(default_factory=dict)


class DataSource(ABC):
    """Abstract base class for data sources."""

    @abstractmethod
    async def collect_data(self, start_time: datetime, end_time: datetime) -> List[Any]:
        """Collect data from the source."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of the data source."""
        pass


class StellarDEXDataSource(DataSource):
    """Stellar DEX data collection."""

    def __init__(self, horizon_url: str = "https://horizon.stellar.org"):
        self.server = Server(horizon_url=horizon_url)
        self.logger = logging.getLogger(__name__)

    async def collect_data(self, start_time: datetime, end_time: datetime) -> List[MarketDataPoint]:
        """Collect Stellar DEX orderbook and trade data."""
        data_points = []

        try:
            # Get major trading pairs
            trading_pairs = [
                (
                    Asset.native(),
                    Asset("USDC", "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN"),
                ),
                (Asset.native(), Asset("yXLM", "GARDNV3Q7YGT4AKSDF25LT32YSCCW67UNSQA")),
            ]

            for base_asset, counter_asset in trading_pairs:
                try:
                    # Get orderbook
                    orderbook = self.server.orderbook(base_asset, counter_asset).call()

                    if orderbook["bids"] and orderbook["asks"]:
                        best_bid = float(orderbook["bids"][0]["price"])
                        best_ask = float(orderbook["asks"][0]["price"])
                        spread = best_ask - best_bid
                        mid_price = (best_bid + best_ask) / 2

                        # Calculate volume
                        bid_volume = sum(float(bid["amount"]) for bid in orderbook["bids"][:10])
                        ask_volume = sum(float(ask["amount"]) for ask in orderbook["asks"][:10])
                        total_volume = bid_volume + ask_volume

                        # Get recent trades
                        trades = (
                            self.server.trades()
                            .for_asset_pair(base_asset, counter_asset)
                            .order(desc=True)
                            .limit(50)
                            .call()
                        )

                        trades_count = len(trades["_embedded"]["records"])

                        data_point = MarketDataPoint(
                            timestamp=datetime.now(),
                            asset_pair=f"{base_asset.code or 'XLM'}/{counter_asset.code}",
                            price=mid_price,
                            volume=total_volume,
                            spread=spread,
                            bid=best_bid,
                            ask=best_ask,
                            trades_count=trades_count,
                            metadata={
                                "orderbook_depth": len(orderbook["bids"]) + len(orderbook["asks"]),
                                "source": "stellar_dex",
                            },
                        )

                        data_points.append(data_point)

                except Exception as e:
                    self.logger.warning(
                        f"Failed to collect data for pair {base_asset.code}/{counter_asset.code}: {e}"
                    )
                    continue

        except BaseRequestError as e:
            self.logger.error(f"Stellar SDK error in data collection: {e}")

        return data_points

    def get_source_name(self) -> str:
        return "stellar_dex"


class SorobanDataSource(DataSource):
    """Soroban smart contract data collection."""

    def __init__(self, soroban_rpc_url: str = "https://soroban-testnet.stellar.org"):
        self.rpc_url = soroban_rpc_url
        self.logger = logging.getLogger(__name__)

    async def collect_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Collect Soroban contract activity data."""
        data_points = []

        try:
            async with aiohttp.ClientSession() as session:
                # Get network info
                payload = {"jsonrpc": "2.0", "id": 1, "method": "getNetwork", "params": {}}

                async with session.post(self.rpc_url, json=payload) as response:
                    if response.status == 200:
                        network_data = await response.json()

                        data_points.append(
                            {
                                "timestamp": datetime.now(),
                                "type": "soroban_network_info",
                                "data": network_data.get("result", {}),
                                "source": "soroban_rpc",
                            }
                        )

                # Get latest ledger for activity metrics
                ledger_payload = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "getLatestLedger",
                    "params": {},
                }

                async with session.post(self.rpc_url, json=ledger_payload) as response:
                    if response.status == 200:
                        ledger_data = await response.json()

                        data_points.append(
                            {
                                "timestamp": datetime.now(),
                                "type": "soroban_ledger_info",
                                "data": ledger_data.get("result", {}),
                                "source": "soroban_rpc",
                            }
                        )

        except Exception as e:
            self.logger.error(f"Failed to collect Soroban data: {e}")

        return data_points

    def get_source_name(self) -> str:
        return "soroban_defi"


class SentimentDataSource(DataSource):
    """Social sentiment data collection (mock implementation)."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def collect_data(self, start_time: datetime, end_time: datetime) -> List[SentimentData]:
        """Collect social sentiment data (mock implementation)."""
        # Mock sentiment data - in production would connect to Twitter API, Reddit, etc.
        mock_sentiments = [
            SentimentData(
                timestamp=datetime.now(),
                source="twitter_mock",
                sentiment_score=0.3,
                confidence=0.7,
                text_sample="Stellar network showing strong fundamentals",
                keywords=["stellar", "xlm", "positive", "fundamentals"],
            ),
            SentimentData(
                timestamp=datetime.now() - timedelta(minutes=30),
                source="reddit_mock",
                sentiment_score=-0.1,
                confidence=0.6,
                text_sample="Market volatility concerning some investors",
                keywords=["market", "volatility", "concern", "investors"],
            ),
        ]

        self.logger.info(f"Generated {len(mock_sentiments)} mock sentiment data points")
        return mock_sentiments

    def get_source_name(self) -> str:
        return "sentiment_data"


class OnChainDataSource(DataSource):
    """On-chain metrics data collection."""

    def __init__(self, horizon_url: str = "https://horizon.stellar.org"):
        self.server = Server(horizon_url=horizon_url)
        self.logger = logging.getLogger(__name__)

    async def collect_data(self, start_time: datetime, end_time: datetime) -> List[OnChainMetrics]:
        """Collect on-chain network metrics."""
        data_points = []

        try:
            # Get ledger information
            ledgers = self.server.ledgers().order(desc=True).limit(10).call()

            for ledger_record in ledgers["_embedded"]["records"]:
                ledger = ledger_record

                metrics = OnChainMetrics(
                    timestamp=datetime.fromisoformat(ledger["closed_at"].replace("Z", "+00:00")),
                    network="stellar_mainnet",
                    transaction_count=int(ledger["transaction_count"]),
                    unique_addresses=int(ledger["operation_count"]),  # Approximation
                    total_volume=float(ledger.get("total_coins", 0)),
                    avg_fee=float(ledger.get("base_fee_in_stroops", 100)) / 10_000_000,
                    network_congestion=min(int(ledger["transaction_count"]) / 1000, 1.0),
                    soroban_activity={
                        "ledger_sequence": ledger["sequence"],
                        "base_reserve": ledger.get("base_reserve_in_stroops", 5000000),
                    },
                )

                data_points.append(metrics)

        except BaseRequestError as e:
            self.logger.error(f"Failed to collect on-chain data: {e}")

        return data_points

    def get_source_name(self) -> str:
        return "on_chain_metrics"


class TechnicalIndicators:
    """Technical analysis indicators for feature engineering."""

    @staticmethod
    def moving_average(prices: List[float], window: int) -> List[float]:
        """Calculate simple moving average."""
        if len(prices) < window:
            return []

        return [sum(prices[i : i + window]) / window for i in range(len(prices) - window + 1)]

    @staticmethod
    def rsi(prices: List[float], window: int = 14) -> List[float]:
        """Calculate Relative Strength Index."""
        if len(prices) < window + 1:
            return []

        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]

        avg_gain = sum(gains[:window]) / window
        avg_loss = sum(losses[:window]) / window

        rsi_values = []

        for i in range(window, len(deltas)):
            avg_gain = (avg_gain * (window - 1) + gains[i]) / window
            avg_loss = (avg_loss * (window - 1) + losses[i]) / window

            rs = avg_gain / avg_loss if avg_loss != 0 else 100
            rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)

        return rsi_values

    @staticmethod
    def bollinger_bands(
        prices: List[float], window: int = 20, num_std: float = 2
    ) -> Dict[str, List[float]]:
        """Calculate Bollinger Bands."""
        if len(prices) < window:
            return {"upper": [], "middle": [], "lower": []}

        moving_avg = TechnicalIndicators.moving_average(prices, window)

        upper_band = []
        lower_band = []

        for i in range(len(moving_avg)):
            price_window = prices[i : i + window]
            std_dev = np.std(price_window)

            upper_band.append(moving_avg[i] + (num_std * std_dev))
            lower_band.append(moving_avg[i] - (num_std * std_dev))

        return {"upper": upper_band, "middle": moving_avg, "lower": lower_band}


class TradingDataPipeline:
    """Main data pipeline for AI trading system."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.data_sources: Dict[str, DataSource] = {}
        self.logger = logging.getLogger(__name__)

        # Initialize data sources
        self._initialize_sources()

        # Feature engineering configuration
        self.feature_config = {
            "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"],
            "lookback_periods": [20, 50, 100, 200],
            "technical_indicators": ["sma", "ema", "rsi", "bollinger", "macd"],
        }

    def _initialize_sources(self):
        """Initialize all data sources."""
        horizon_url = self.config.get("horizon_url", "https://horizon.stellar.org")
        soroban_url = self.config.get("soroban_url", "https://soroban-testnet.stellar.org")

        self.data_sources = {
            "stellar_dex": StellarDEXDataSource(horizon_url),
            "soroban_defi": SorobanDataSource(soroban_url),
            "sentiment": SentimentDataSource(),
            "on_chain": OnChainDataSource(horizon_url),
        }

        self.logger.info(f"Initialized {len(self.data_sources)} data sources")

    async def collect_market_data(self, timeframe: str = "1h") -> Dict[str, List[Any]]:
        """Collect data from all sources."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)  # Last 24 hours

        collected_data = {}

        for source_name, source in self.data_sources.items():
            try:
                self.logger.info(f"Collecting data from {source_name}")
                data = await source.collect_data(start_time, end_time)
                collected_data[source_name] = data
                self.logger.info(f"Collected {len(data)} data points from {source_name}")

            except Exception as e:
                self.logger.error(f"Failed to collect data from {source_name}: {e}")
                collected_data[source_name] = []

        return collected_data

    def feature_engineering(self, raw_data: Dict[str, List[Any]]) -> pd.DataFrame:
        """Advanced feature extraction for ML models."""
        features = []

        # Process market data
        if "stellar_dex" in raw_data and raw_data["stellar_dex"]:
            market_features = self._extract_market_features(raw_data["stellar_dex"])
            features.extend(market_features)

        # Process sentiment data
        if "sentiment" in raw_data and raw_data["sentiment"]:
            sentiment_features = self._extract_sentiment_features(raw_data["sentiment"])
            features.extend(sentiment_features)

        # Process on-chain data
        if "on_chain" in raw_data and raw_data["on_chain"]:
            network_features = self._extract_network_features(raw_data["on_chain"])
            features.extend(network_features)

        if not features:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(features)

        # Add technical indicators
        if "price" in df.columns:
            df = self._add_technical_indicators(df)

        return df

    def _extract_market_features(self, market_data: List[MarketDataPoint]) -> List[Dict[str, Any]]:
        """Extract features from market data."""
        features = []

        for data_point in market_data:
            feature = {
                "timestamp": data_point.timestamp,
                "asset_pair": data_point.asset_pair,
                "price": data_point.price,
                "volume": data_point.volume,
                "spread": data_point.spread,
                "spread_pct": (data_point.spread / data_point.price) * 100,
                "bid_ask_ratio": data_point.bid / data_point.ask if data_point.ask > 0 else 0,
                "trades_count": data_point.trades_count,
                "orderbook_depth": data_point.metadata.get("orderbook_depth", 0),
            }
            features.append(feature)

        return features

    def _extract_sentiment_features(
        self, sentiment_data: List[SentimentData]
    ) -> List[Dict[str, Any]]:
        """Extract features from sentiment data."""
        if not sentiment_data:
            return []

        # Aggregate sentiment scores
        total_sentiment = sum(s.sentiment_score * s.confidence for s in sentiment_data)
        total_confidence = sum(s.confidence for s in sentiment_data)

        avg_sentiment = total_sentiment / total_confidence if total_confidence > 0 else 0

        return [
            {
                "timestamp": datetime.now(),
                "avg_sentiment": avg_sentiment,
                "sentiment_confidence": total_confidence / len(sentiment_data),
                "sentiment_samples": len(sentiment_data),
                "positive_sentiment_ratio": len(
                    [s for s in sentiment_data if s.sentiment_score > 0]
                )
                / len(sentiment_data),
            }
        ]

    def _extract_network_features(self, network_data: List[OnChainMetrics]) -> List[Dict[str, Any]]:
        """Extract features from network/on-chain data."""
        features = []

        for metrics in network_data:
            feature = {
                "timestamp": metrics.timestamp,
                "transaction_count": metrics.transaction_count,
                "unique_addresses": metrics.unique_addresses,
                "total_volume": metrics.total_volume,
                "avg_fee": metrics.avg_fee,
                "network_congestion": metrics.network_congestion,
                "network_activity_score": min(metrics.transaction_count / 1000, 1.0),
            }
            features.append(feature)

        return features

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the feature DataFrame."""
        if "price" not in df.columns or len(df) < 20:
            return df

        prices = df["price"].tolist()

        # Simple Moving Averages
        df["sma_20"] = pd.Series(TechnicalIndicators.moving_average(prices, 20))
        df["sma_50"] = pd.Series(TechnicalIndicators.moving_average(prices, 50))

        # RSI
        rsi_values = TechnicalIndicators.rsi(prices)
        if rsi_values:
            df.loc[df.index[-len(rsi_values) :], "rsi"] = rsi_values

        # Bollinger Bands
        if len(prices) >= 20:
            bands = TechnicalIndicators.bollinger_bands(prices, 20)
            if bands["middle"]:
                df.loc[df.index[-len(bands["middle"]) :], "bb_upper"] = bands["upper"]
                df.loc[df.index[-len(bands["middle"]) :], "bb_middle"] = bands["middle"]
                df.loc[df.index[-len(bands["middle"]) :], "bb_lower"] = bands["lower"]

        return df

    async def get_features_for_prediction(self, asset_pair: str = "XLM/USDC") -> pd.DataFrame:
        """Get processed features ready for ML model prediction."""
        raw_data = await self.collect_market_data()
        features_df = self.feature_engineering(raw_data)

        # Filter for specific asset pair if requested
        if "asset_pair" in features_df.columns:
            features_df = features_df[features_df["asset_pair"] == asset_pair]

        # Forward fill missing values
        features_df = features_df.fillna(method="ffill")

        # Drop non-numeric columns for model input
        numeric_columns = features_df.select_dtypes(include=[np.number]).columns
        model_features = features_df[numeric_columns]

        return model_features

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "sources_count": len(self.data_sources),
            "active_sources": list(self.data_sources.keys()),
            "feature_config": self.feature_config,
            "status": "operational",
            "last_updated": datetime.now().isoformat(),
        }


# Example usage and testing
async def main():
    """Example usage of the data pipeline."""
    logging.basicConfig(level=logging.INFO)

    pipeline = TradingDataPipeline()

    print("🔄 Starting data collection...")
    raw_data = await pipeline.collect_market_data()

    print(f"📊 Collected data from {len(raw_data)} sources")
    for source, data in raw_data.items():
        print(f"  {source}: {len(data)} data points")

    print("\n🔧 Processing features...")
    features_df = pipeline.feature_engineering(raw_data)

    if not features_df.empty:
        print(
            f"✅ Generated {len(features_df)} feature rows with {len(features_df.columns)} columns"
        )
        print(f"📈 Feature columns: {list(features_df.columns)}")
    else:
        print("⚠️  No features generated")

    print("\n📊 Pipeline Status:")
    status = pipeline.get_pipeline_status()
    for key, value in status.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
