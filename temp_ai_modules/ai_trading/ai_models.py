"""
AI Trading Models for Stellar Hummingbot Connector v3.0
Machine learning models for price prediction, strategy optimization, and risk management
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import logging
from abc import ABC, abstractmethod
import joblib
import json

# ML model imports (fallback to basic implementations if not available)
try:
    from sklearn.preprocessing import StandardScaler, MinMaxScaler  # type: ignore
    from sklearn.model_selection import train_test_split, cross_val_score  # type: ignore
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor  # type: ignore
    from sklearn.linear_model import LinearRegression, Ridge  # type: ignore
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score  # type: ignore

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import torch  # type: ignore
    import torch.nn as nn  # type: ignore
    import torch.optim as optim  # type: ignore

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class ModelPrediction:
    """AI model prediction result."""

    timestamp: datetime
    model_name: str
    prediction_type: str
    value: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelPerformance:
    """Model performance metrics."""

    model_name: str
    mse: float
    mae: float
    r2_score: float
    accuracy: float
    total_predictions: int
    last_updated: datetime


class BaseAIModel(ABC):
    """Abstract base class for AI trading models."""

    def __init__(self, model_name: str, model_type: str):
        self.model_name = model_name
        self.model_type = model_type
        self.is_trained = False
        self.training_data_size = 0
        self.last_training_time = None
        self.performance_metrics = None
        self.logger = logging.getLogger(f"{__name__}.{model_name}")

    @abstractmethod
    async def train(self, training_data: pd.DataFrame, target_column: str) -> bool:
        """Train the model with provided data."""
        pass

    @abstractmethod
    async def predict(self, input_data: pd.DataFrame) -> ModelPrediction:
        """Make predictions using the trained model."""
        pass

    @abstractmethod
    def save_model(self, filepath: str) -> bool:
        """Save the trained model to disk."""
        pass

    @abstractmethod
    def load_model(self, filepath: str) -> bool:
        """Load a trained model from disk."""
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and status."""
        return {
            "name": self.model_name,
            "type": self.model_type,
            "is_trained": self.is_trained,
            "training_data_size": self.training_data_size,
            "last_training_time": (
                self.last_training_time.isoformat() if self.last_training_time else None
            ),
            "performance": self.performance_metrics.__dict__ if self.performance_metrics else None,
        }


class LSTMPricePredictor(BaseAIModel):
    """LSTM-based price prediction model."""

    def __init__(self, sequence_length: int = 50, hidden_size: int = 64):
        super().__init__("lstm_price_predictor", "deep_learning")
        self.sequence_length = sequence_length
        self.hidden_size = hidden_size
        self.model = None
        self.scaler = None

        if TORCH_AVAILABLE:
            self._initialize_model()
        else:
            self.logger.warning("PyTorch not available. Using fallback implementation.")

    def _initialize_model(self):
        """Initialize the LSTM model architecture."""
        if not TORCH_AVAILABLE:
            return

        class LSTMModel(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers=2, dropout=0.2):
                super(LSTMModel, self).__init__()
                self.hidden_size = hidden_size
                self.num_layers = num_layers

                self.lstm = nn.LSTM(
                    input_size, hidden_size, num_layers, batch_first=True, dropout=dropout
                )
                self.dropout = nn.Dropout(dropout)
                self.fc = nn.Linear(hidden_size, 1)

            def forward(self, x):
                lstm_out, _ = self.lstm(x)
                lstm_out = self.dropout(lstm_out)
                prediction = self.fc(lstm_out[:, -1, :])
                return prediction

        self.model_class = LSTMModel

    async def train(self, training_data: pd.DataFrame, target_column: str = "price") -> bool:
        """Train the LSTM model."""
        try:
            if not TORCH_AVAILABLE:
                return await self._train_fallback(training_data, target_column)

            # Prepare and validate data
            if not self._validate_training_data(training_data, target_column):
                return False

            # Process training data
            X_tensor, y_tensor = await self._prepare_training_data(training_data, target_column)
            if X_tensor is None:
                return False

            # Train the model
            success = await self._execute_training(X_tensor, y_tensor)
            return success

        except Exception as e:
            self.logger.error(f"Training failed: {e}")
            return False

    def _validate_training_data(self, training_data: pd.DataFrame, target_column: str) -> bool:
        """Validate training data requirements."""
        if target_column not in training_data.columns:
            self.logger.error(f"Target column '{target_column}' not found in training data")
            return False

        numeric_columns = training_data.select_dtypes(include=[np.number]).columns
        feature_data = training_data[numeric_columns].dropna()

        if len(feature_data) < self.sequence_length * 2:
            self.logger.error(
                f"Insufficient data for training. Need at least {self.sequence_length * 2} samples"
            )
            return False

        return True

    async def _prepare_training_data(self, training_data: pd.DataFrame, target_column: str):
        """Prepare data for LSTM training."""
        # Select numeric features
        numeric_columns = training_data.select_dtypes(include=[np.number]).columns
        feature_data = training_data[numeric_columns].dropna()

        # Scale the data
        self.scaler = MinMaxScaler() if SKLEARN_AVAILABLE else None
        if self.scaler:
            scaled_data = self.scaler.fit_transform(feature_data)
        else:
            # Simple normalization fallback
            scaled_data = (feature_data - feature_data.mean()) / feature_data.std()
            scaled_data = scaled_data.fillna(0).values

        # Create sequences
        X, y = self._create_sequences(scaled_data, target_column, feature_data.columns)

        if len(X) == 0:
            self.logger.error("No sequences created from training data")
            return None, None

        # Convert to PyTorch tensors
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.FloatTensor(y)

        return X_tensor, y_tensor

    async def _execute_training(self, X_tensor, y_tensor) -> bool:
        """Execute the actual model training."""
        # Initialize model
        input_size = X_tensor.shape[2]
        self.model = self.model_class(input_size, self.hidden_size)

        # Training setup
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)

        # Train the model
        self.model.train()
        num_epochs = 100
        batch_size = 32

        for epoch in range(num_epochs):
            total_loss = 0
            for i in range(0, len(X_tensor), batch_size):
                batch_X = X_tensor[i : i + batch_size]
                batch_y = y_tensor[i : i + batch_size]

                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs.squeeze(), batch_y)
                loss.backward()
                optimizer.step()

                total_loss += loss.item()

            if epoch % 20 == 0:
                avg_loss = total_loss / (len(X_tensor) // batch_size + 1)
                self.logger.info(f"Epoch {epoch}, Average Loss: {avg_loss:.6f}")

        # Update training status
        self.is_trained = True
        self.training_data_size = len(X_tensor)
        self.last_training_time = datetime.now()

        # Calculate performance metrics
        self._calculate_performance_metrics(X_tensor, y_tensor)

        return True

    def _calculate_performance_metrics(self, X_tensor, y_tensor):
        """Calculate and store model performance metrics."""
        self.model.eval()
        with torch.no_grad():
            train_predictions = self.model(X_tensor).squeeze().numpy()
            y_numpy = y_tensor.numpy()
            mse = mean_squared_error(y_numpy, train_predictions)
            mae = mean_absolute_error(y_numpy, train_predictions)
            r2 = r2_score(y_numpy, train_predictions)

            self.performance_metrics = ModelPerformance(
                model_name=self.model_name,
                mse=mse,
                mae=mae,
                r2_score=r2,
                accuracy=max(0, r2),
                total_predictions=len(y_numpy),
                last_updated=datetime.now(),
            )

        self.logger.info(f"LSTM model trained successfully. R² Score: {r2:.4f}")

    async def _train_fallback(self, training_data: pd.DataFrame, target_column: str) -> bool:
        """Fallback training using simple linear regression."""
        try:
            if not SKLEARN_AVAILABLE:
                self.logger.error("Neither PyTorch nor scikit-learn available for training")
                return False

            numeric_columns = training_data.select_dtypes(include=[np.number]).columns
            feature_columns = [col for col in numeric_columns if col != target_column]

            if not feature_columns:
                self.logger.error("No feature columns available for training")
                return False

            X = training_data[feature_columns].fillna(0)
            y = training_data[target_column].fillna(0)

            # Simple linear regression fallback
            self.model = LinearRegression()
            self.model.fit(X, y)

            self.is_trained = True
            self.training_data_size = len(training_data)
            self.last_training_time = datetime.now()

            # Calculate metrics
            predictions = self.model.predict(X)
            mse = mean_squared_error(y, predictions)
            mae = mean_absolute_error(y, predictions)
            r2 = r2_score(y, predictions)

            self.performance_metrics = ModelPerformance(
                model_name=self.model_name,
                mse=mse,
                mae=mae,
                r2_score=r2,
                accuracy=max(0, r2),
                total_predictions=len(y),
                last_updated=datetime.now(),
            )

            self.logger.info(f"Fallback model trained. R² Score: {r2:.4f}")
            return True

        except Exception as e:
            self.logger.error(f"Fallback training failed: {e}")
            return False

    def _create_sequences(
        self, data: np.ndarray, target_column: str, columns: pd.Index
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training."""
        try:
            # Find target column index
            target_idx = list(columns).index(target_column)

            X, y = [], []
            for i in range(self.sequence_length, len(data)):
                X.append(data[i - self.sequence_length : i])
                y.append(data[i, target_idx])

            return np.array(X), np.array(y)

        except Exception as e:
            self.logger.error(f"Sequence creation failed: {e}")
            return np.array([]), np.array([])

    async def predict(self, input_data: pd.DataFrame) -> ModelPrediction:
        """Make price predictions."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")

        try:
            if TORCH_AVAILABLE and hasattr(self.model, "eval"):
                return await self._predict_lstm(input_data)
            else:
                return await self._predict_fallback(input_data)

        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return ModelPrediction(
                timestamp=datetime.now(),
                model_name=self.model_name,
                prediction_type="price",
                value=0.0,
                confidence=0.0,
                metadata={"error": str(e)},
            )

    async def _predict_lstm(self, input_data: pd.DataFrame) -> ModelPrediction:
        """LSTM-based prediction."""
        numeric_columns = input_data.select_dtypes(include=[np.number]).columns
        feature_data = input_data[numeric_columns].fillna(0)

        if len(feature_data) < self.sequence_length:
            # Pad with zeros if insufficient data
            padding_needed = self.sequence_length - len(feature_data)
            padding = pd.DataFrame(0, index=range(padding_needed), columns=feature_data.columns)
            feature_data = pd.concat([padding, feature_data], ignore_index=True)

        # Scale data
        if self.scaler:
            scaled_data = self.scaler.transform(feature_data.tail(self.sequence_length))
        else:
            scaled_data = (
                feature_data.tail(self.sequence_length) - feature_data.mean()
            ) / feature_data.std()
            scaled_data = scaled_data.fillna(0).values

        # Create input tensor
        X = torch.FloatTensor(scaled_data).unsqueeze(0)

        # Make prediction
        self.model.eval()
        with torch.no_grad():
            prediction = self.model(X).item()

        # Inverse transform if scaler was used
        if self.scaler:
            # Create dummy array for inverse transform
            dummy = np.zeros((1, len(self.scaler.feature_names_in_)))
            dummy[0, 0] = prediction  # Assume price is first column
            prediction = self.scaler.inverse_transform(dummy)[0, 0]

        confidence = (
            min(self.performance_metrics.r2_score, 1.0) if self.performance_metrics else 0.5
        )

        return ModelPrediction(
            timestamp=datetime.now(),
            model_name=self.model_name,
            prediction_type="price",
            value=float(prediction),
            confidence=confidence,
            metadata={
                "model_type": "lstm",
                "sequence_length": self.sequence_length,
                "input_features": len(feature_data.columns),
            },
        )

    async def _predict_fallback(self, input_data: pd.DataFrame) -> ModelPrediction:
        """Fallback prediction using linear regression."""
        if not SKLEARN_AVAILABLE:
            raise ValueError("No prediction capability available")

        numeric_columns = input_data.select_dtypes(include=[np.number]).columns
        feature_data = input_data[numeric_columns].fillna(0)

        if len(feature_data) == 0:
            raise ValueError("No numeric features available for prediction")

        # Use the last row for prediction
        latest_features = feature_data.iloc[-1:].values
        prediction = self.model.predict(latest_features)[0]

        confidence = (
            min(self.performance_metrics.r2_score, 1.0) if self.performance_metrics else 0.5
        )

        return ModelPrediction(
            timestamp=datetime.now(),
            model_name=self.model_name,
            prediction_type="price",
            value=float(prediction),
            confidence=confidence,
            metadata={
                "model_type": "linear_regression",
                "input_features": len(feature_data.columns),
            },
        )

    def save_model(self, filepath: str) -> bool:
        """Save the trained model."""
        try:
            model_data = {
                "model_name": self.model_name,
                "model_type": self.model_type,
                "sequence_length": self.sequence_length,
                "hidden_size": self.hidden_size,
                "is_trained": self.is_trained,
                "training_data_size": self.training_data_size,
                "last_training_time": (
                    self.last_training_time.isoformat() if self.last_training_time else None
                ),
            }

            if TORCH_AVAILABLE and hasattr(self.model, "state_dict"):
                torch.save(
                    {
                        "model_state_dict": self.model.state_dict(),
                        "scaler": self.scaler,
                        "metadata": model_data,
                    },
                    filepath,
                )
            elif SKLEARN_AVAILABLE and hasattr(self.model, "predict"):
                joblib.dump({"model": self.model, "metadata": model_data}, filepath)
            else:
                # Save just metadata
                with open(filepath, "w") as f:
                    json.dump(model_data, f)

            self.logger.info(f"Model saved to {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")
            return False

    def load_model(self, filepath: str) -> bool:
        """Load a trained model."""
        try:
            if TORCH_AVAILABLE:
                checkpoint = torch.load(filepath, map_location="cpu")
                metadata = checkpoint.get("metadata", {})

                self.model_name = metadata.get("model_name", self.model_name)
                self.sequence_length = metadata.get("sequence_length", self.sequence_length)
                self.hidden_size = metadata.get("hidden_size", self.hidden_size)

                if "model_state_dict" in checkpoint:
                    self._initialize_model()
                    # Recreate model with proper input size
                    input_size = checkpoint["model_state_dict"]["lstm.weight_ih_l0"].shape[1]
                    self.model = self.model_class(input_size, self.hidden_size)
                    self.model.load_state_dict(checkpoint["model_state_dict"])

                self.scaler = checkpoint.get("scaler")

            elif SKLEARN_AVAILABLE:
                checkpoint = joblib.load(filepath)
                self.model = checkpoint["model"]
                metadata = checkpoint.get("metadata", {})

            self.is_trained = True
            self.logger.info(f"Model loaded from {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            return False


class VolatilityForecaster(BaseAIModel):
    """Volatility forecasting model using GARCH-like approach."""

    def __init__(self, window_size: int = 30):
        super().__init__("garch_volatility_model", "statistical")
        self.window_size = window_size
        self.model = None

    async def train(self, training_data: pd.DataFrame, target_column: str = "price") -> bool:
        """Train volatility forecasting model."""
        try:
            if target_column not in training_data.columns:
                self.logger.error(f"Target column '{target_column}' not found")
                return False

            prices = training_data[target_column].dropna()

            if len(prices) < self.window_size * 2:
                self.logger.error(
                    f"Insufficient data. Need at least {self.window_size * 2} samples"
                )
                return False

            # Calculate returns
            returns = prices.pct_change().dropna()

            # Calculate rolling volatility (standard deviation of returns)
            rolling_vol = returns.rolling(window=self.window_size).std().dropna()

            if SKLEARN_AVAILABLE:
                # Use historical volatility as features
                X = []
                y = []

                for i in range(self.window_size, len(rolling_vol)):
                    X.append(rolling_vol.iloc[i - self.window_size : i].values)
                    y.append(rolling_vol.iloc[i])

                if len(X) == 0:
                    self.logger.error("No training samples created")
                    return False

                X = np.array(X)
                y = np.array(y)

                # Train random forest for volatility prediction
                self.model = RandomForestRegressor(n_estimators=50, random_state=42)
                self.model.fit(X, y)

            else:
                # Simple moving average fallback
                self.model = {
                    "type": "moving_average",
                    "mean_volatility": rolling_vol.mean(),
                    "std_volatility": rolling_vol.std(),
                }

            self.is_trained = True
            self.training_data_size = len(returns)
            self.last_training_time = datetime.now()

            # Calculate performance metrics
            if SKLEARN_AVAILABLE and hasattr(self.model, "predict"):
                predictions = self.model.predict(X)
                mse = mean_squared_error(y, predictions)
                mae = mean_absolute_error(y, predictions)
                r2 = r2_score(y, predictions)
            else:
                # Fallback metrics
                mse = rolling_vol.var()
                mae = rolling_vol.std()
                r2 = 0.5

            self.performance_metrics = ModelPerformance(
                model_name=self.model_name,
                mse=mse,
                mae=mae,
                r2_score=r2,
                accuracy=max(0, r2),
                total_predictions=len(returns),
                last_updated=datetime.now(),
            )

            self.logger.info(f"Volatility model trained. R² Score: {r2:.4f}")
            return True

        except Exception as e:
            self.logger.error(f"Training failed: {e}")
            return False

    async def predict(self, input_data: pd.DataFrame) -> ModelPrediction:
        """Predict volatility."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")

        try:
            # Assume 'price' column exists
            prices = input_data["price"].dropna()

            if len(prices) < 2:
                raise ValueError("Insufficient price data for volatility calculation")

            # Calculate recent returns
            returns = prices.pct_change().dropna()
            recent_volatility = returns.tail(self.window_size).std()

            if SKLEARN_AVAILABLE and hasattr(self.model, "predict"):
                # Use model prediction
                recent_vol_history = (
                    returns.rolling(window=min(self.window_size, len(returns))).std().dropna()
                )

                if len(recent_vol_history) >= self.window_size:
                    X = recent_vol_history.tail(self.window_size).values.reshape(1, -1)
                    prediction = self.model.predict(X)[0]
                else:
                    prediction = recent_volatility

            else:
                # Fallback to simple prediction
                mean_vol = self.model["mean_volatility"]
                prediction = (recent_volatility + mean_vol) / 2

            confidence = (
                min(self.performance_metrics.r2_score, 1.0) if self.performance_metrics else 0.5
            )

            return ModelPrediction(
                timestamp=datetime.now(),
                model_name=self.model_name,
                prediction_type="volatility",
                value=float(prediction),
                confidence=confidence,
                metadata={"current_volatility": recent_volatility, "window_size": self.window_size},
            )

        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return ModelPrediction(
                timestamp=datetime.now(),
                model_name=self.model_name,
                prediction_type="volatility",
                value=0.0,
                confidence=0.0,
                metadata={"error": str(e)},
            )

    def save_model(self, filepath: str) -> bool:
        """Save volatility model."""
        try:
            if SKLEARN_AVAILABLE and hasattr(self.model, "predict"):
                joblib.dump(
                    {
                        "model": self.model,
                        "window_size": self.window_size,
                        "model_name": self.model_name,
                    },
                    filepath,
                )
            else:
                with open(filepath, "w") as f:
                    json.dump(
                        {
                            "model": self.model,
                            "window_size": self.window_size,
                            "model_name": self.model_name,
                        },
                        f,
                    )

            return True

        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")
            return False

    def load_model(self, filepath: str) -> bool:
        """Load volatility model."""
        try:
            if SKLEARN_AVAILABLE:
                data = joblib.load(filepath)
            else:
                with open(filepath, "r") as f:
                    data = json.load(f)

            self.model = data["model"]
            self.window_size = data["window_size"]
            self.model_name = data["model_name"]
            self.is_trained = True

            return True

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            return False


class TradingAIModels:
    """Manager for all AI trading models."""

    def __init__(self):
        self.models: Dict[str, BaseAIModel] = {}
        self.logger = logging.getLogger(__name__)

        # Initialize default models
        self._initialize_models()

    def _initialize_models(self):
        """Initialize default AI models."""
        self.models = {
            "price_predictor": LSTMPricePredictor(sequence_length=50),
            "volatility_forecaster": VolatilityForecaster(window_size=30),
            # Additional models can be added here
        }

        self.logger.info(f"Initialized {len(self.models)} AI models")

    async def train_all_models(self, training_data: pd.DataFrame) -> Dict[str, bool]:
        """Train all models with the provided data."""
        results = {}

        for model_name, model in self.models.items():
            try:
                self.logger.info(f"Training {model_name}...")
                success = await model.train(training_data)
                results[model_name] = success

                if success:
                    self.logger.info(f"✅ {model_name} trained successfully")
                else:
                    self.logger.error(f"❌ {model_name} training failed")

            except Exception as e:
                self.logger.error(f"Error training {model_name}: {e}")
                results[model_name] = False

        return results

    async def predict_all(self, input_data: pd.DataFrame) -> Dict[str, ModelPrediction]:
        """Get predictions from all trained models."""
        predictions = {}

        for model_name, model in self.models.items():
            if model.is_trained:
                try:
                    prediction = await model.predict(input_data)
                    predictions[model_name] = prediction
                except Exception as e:
                    self.logger.error(f"Prediction failed for {model_name}: {e}")

        return predictions

    def get_model_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all models."""
        return {name: model.get_model_info() for name, model in self.models.items()}

    def add_model(self, model: BaseAIModel) -> bool:
        """Add a new model to the manager."""
        try:
            self.models[model.model_name] = model
            self.logger.info(f"Added model: {model.model_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add model: {e}")
            return False

    def remove_model(self, model_name: str) -> bool:
        """Remove a model from the manager."""
        if model_name in self.models:
            del self.models[model_name]
            self.logger.info(f"Removed model: {model_name}")
            return True
        return False

    async def save_all_models(self, base_directory: str) -> Dict[str, bool]:
        """Save all trained models."""
        results = {}

        for model_name, model in self.models.items():
            if model.is_trained:
                filepath = f"{base_directory}/{model_name}.pkl"
                results[model_name] = model.save_model(filepath)

        return results

    async def load_all_models(self, base_directory: str) -> Dict[str, bool]:
        """Load all models from directory."""
        results = {}

        for model_name, model in self.models.items():
            filepath = f"{base_directory}/{model_name}.pkl"
            results[model_name] = model.load_model(filepath)

        return results


# Example usage
async def main():
    """Example usage of AI trading models."""
    logging.basicConfig(level=logging.INFO)

    # Create sample data
    dates = pd.date_range(start="2023-01-01", end="2024-01-01", freq="H")
    np.random.seed(42)

    # Generate synthetic price data with trend and noise
    trend = np.linspace(100, 150, len(dates))
    noise = np.random.normal(0, 5, len(dates))
    prices = trend + noise + 10 * np.sin(np.arange(len(dates)) * 0.01)

    # Create DataFrame
    sample_data = pd.DataFrame(
        {
            "timestamp": dates,
            "price": prices,
            "volume": np.random.uniform(1000, 10000, len(dates)),
            "spread": np.random.uniform(0.01, 0.1, len(dates)),
        }
    )

    print(f"📊 Generated {len(sample_data)} sample data points")

    # Initialize models
    models = TradingAIModels()

    print("\n🧠 Training AI models...")
    training_results = await models.train_all_models(sample_data)

    print("\n📈 Training Results:")
    for model_name, success in training_results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {model_name}: {status}")

    # Make predictions with recent data
    recent_data = sample_data.tail(100)
    print(f"\n🔮 Making predictions with {len(recent_data)} recent data points...")

    predictions = await models.predict_all(recent_data)

    print("\n📊 Predictions:")
    for model_name, prediction in predictions.items():
        print(f"  {model_name}:")
        print(f"    Value: {prediction.value:.4f}")
        print(f"    Confidence: {prediction.confidence:.4f}")
        print(f"    Type: {prediction.prediction_type}")

    # Show model status
    print("\n📋 Model Status:")
    status = models.get_model_status()
    for model_name, info in status.items():
        print(f"  {model_name}:")
        print(f"    Trained: {info['is_trained']}")
        print(f"    Data size: {info['training_data_size']}")
        if info["performance"]:
            print(f"    R² Score: {info['performance']['r2_score']:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
