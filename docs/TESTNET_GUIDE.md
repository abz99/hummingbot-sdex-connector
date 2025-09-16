# Testnet Trading Guide
**Stellar Hummingbot Connector v3.0**

**Last Updated:** 2025-09-16 06:46 UTC

## 🧪 Safe Testing Environment Setup

### 🎯 Why Use Testnet?

Testnet provides a **risk-free environment** to:
- Learn the connector functionality
- Test trading strategies
- Validate configurations
- Practice operational procedures

**No real money at risk** - Perfect for experimentation!

### 🚀 Quick Testnet Setup

#### **1. Configure Testnet Environment**
```bash
# Set testnet configuration
export STELLAR_NETWORK=testnet
export STELLAR_HORIZON_URL=https://horizon-testnet.stellar.org
export STELLAR_PASSPHRASE="Test SDF Network ; September 2015"

# Start connector in testnet mode
hummingbot create --network testnet
```

#### **2. Get Test Accounts and Funding**
```bash
# Create test account
stellar-sdk-utils create-account --testnet

# Fund account with test XLM (friendbot)
curl "https://friendbot.stellar.org?addr=YOUR_TEST_ACCOUNT_ADDRESS"

# Verify funding
stellar-sdk-utils account-info --account YOUR_TEST_ACCOUNT_ADDRESS --testnet
```

#### **3. Configure Test Trading Pair**
```yaml
# testnet_config.yml
trading_pair: "XLM-USDC"
base_asset: "XLM"
quote_asset: "USDC"

# Test-specific settings
order_amount: 10.0        # Small test amounts
bid_spread: 1.0          # Wide spreads for testing
ask_spread: 1.0
refresh_interval: 30     # Frequent updates for testing
```

### 📊 Testnet Features

#### **Available Test Assets**
- **XLM** (Native Stellar lumens)
- **USDC** (Test USDC tokens)
- **BTC** (Test Bitcoin anchor tokens)
- **ETH** (Test Ethereum anchor tokens)

#### **Test Scenarios**
1. **Basic Market Making**: Simple bid/ask orders
2. **Arbitrage Testing**: Cross-DEX price differences
3. **Volume Testing**: High-frequency order placement
4. **Error Handling**: Network disconnection simulation
5. **Strategy Optimization**: Parameter tuning

### 🔧 Testnet-Specific Configuration

#### **Network Settings**
```yaml
testnet:
  horizon_url: "https://horizon-testnet.stellar.org"
  soroban_rpc: "https://soroban-testnet.stellar.org"
  network_passphrase: "Test SDF Network ; September 2015"

  # Testnet-friendly timeouts
  request_timeout: 30
  retry_attempts: 5

  # Enhanced logging for debugging
  log_level: "DEBUG"
```

#### **Trading Parameters**
```yaml
testnet_trading:
  # Conservative for testing
  min_order_size: 1.0
  max_order_size: 100.0

  # Wide spreads to ensure fills
  default_spread: 2.0

  # Frequent updates for testing
  refresh_interval: 10

  # Enable all monitoring
  enable_detailed_logging: true
  enable_performance_metrics: true
```

### 📈 Testing Checklist

#### **Before Mainnet Deployment**
- [ ] **Account Management**: Create, fund, and manage test accounts
- [ ] **Order Placement**: Successfully place and cancel orders
- [ ] **Strategy Execution**: Run complete trading strategy cycles
- [ ] **Error Handling**: Test network disconnection recovery
- [ ] **Monitoring**: Verify all metrics and alerts work
- [ ] **Performance**: Measure latency and throughput
- [ ] **Security**: Test key management and authentication

#### **Strategy Validation**
- [ ] **Profitability**: Strategy shows positive returns in testing
- [ ] **Risk Controls**: All risk limits properly enforced
- [ ] **Market Conditions**: Tested under various market scenarios
- [ ] **Operational Stability**: 24+ hours of continuous operation

### 🎯 Common Testnet Scenarios

#### **Scenario 1: Basic Market Making**
```bash
# Start simple market making strategy
hummingbot create \
  --strategy pure_market_making \
  --exchange stellar \
  --trading-pair XLM-USDC \
  --testnet
```

#### **Scenario 2: Cross-DEX Arbitrage**
```bash
# Test arbitrage between DEXs
hummingbot create \
  --strategy arbitrage \
  --primary-exchange stellar \
  --secondary-exchange stellar-testnet-2 \
  --trading-pair XLM-USDC
```

#### **Scenario 3: Strategy Parameter Optimization**
```bash
# Test different spread configurations
for spread in 0.5 1.0 2.0; do
  hummingbot backtest \
    --strategy pure_market_making \
    --spread $spread \
    --testnet-data
done
```

### 🔗 Testnet Resources

#### **Stellar Testnet Services**
- **Horizon API**: https://horizon-testnet.stellar.org
- **Laboratory**: https://laboratory.stellar.org (set to testnet)
- **Friendbot**: https://friendbot.stellar.org (free test XLM)
- **Explorer**: https://testnet.steexp.com

#### **Monitoring and Debugging**
- **Local Dashboard**: http://localhost:8080
- **Logs**: `tail -f logs/testnet_trading.log`
- **Metrics**: http://localhost:8000/metrics

### ⚠️ Important Notes

1. **No Real Value**: Testnet tokens have no monetary value
2. **Network Resets**: Testnet may be reset periodically
3. **Performance Differences**: Testnet may behave differently than mainnet
4. **Limited Liquidity**: Order books may be sparse
5. **Test Data**: Use representative but not sensitive data

### 🎓 Learning Path

1. **Start Here**: Basic testnet setup and funding
2. **Practice**: Simple market making strategies
3. **Experiment**: Complex strategies and parameters
4. **Validate**: Comprehensive testing scenarios
5. **Graduate**: Deploy to mainnet with confidence

---
*Testnet is your safe space to learn. Take advantage of it before risking real funds on mainnet!*