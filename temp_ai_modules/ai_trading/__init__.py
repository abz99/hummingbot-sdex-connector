"""
AI Trading Module for Stellar Hummingbot Connector v3.0
Advanced AI/ML capabilities for autonomous trading intelligence
"""

from .data_pipeline import (
    TradingDataPipeline,
    MarketDataPoint,
    SentimentData,
    OnChainMetrics,
    TechnicalIndicators,
)

from .ai_models import (
    TradingAIModels,
    LSTMPricePredictor,
    VolatilityForecaster,
    ModelPrediction,
    ModelPerformance,
    BaseAIModel,
)

__version__ = "1.0.0"
__author__ = "Stellar Hummingbot Connector Team"

__all__ = [
    # Data Pipeline
    "TradingDataPipeline",
    "MarketDataPoint",
    "SentimentData",
    "OnChainMetrics",
    "TechnicalIndicators",
    # AI Models
    "TradingAIModels",
    "LSTMPricePredictor",
    "VolatilityForecaster",
    "ModelPrediction",
    "ModelPerformance",
    "BaseAIModel",
]
