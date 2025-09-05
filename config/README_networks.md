# Stellar Multi-Network Configuration

## Overview

This directory contains comprehensive Stellar network configurations for testnet, futurenet, and mainnet environments. The configuration system supports multi-environment deployments with automatic failover and health monitoring.

## Configuration Files

### Core Network Configuration
- `networks.yml` - Primary network configuration with all three Stellar networks
- `stellar_networks_env.yml` - Environment-specific overrides and feature flags
- `development.yml` - Development environment settings
- `production.yml` - Production environment settings  
- `security.yml` - Security-related configurations

### Key Features

✅ **Multi-Network Support**
- Stellar Testnet (development)
- Stellar Futurenet (latest features)
- Stellar Mainnet (production)

✅ **High Availability**
- Primary + fallback endpoints for each network
- Automatic failover and health monitoring
- Load balancing across multiple providers

✅ **Production-Ready**
- Rate limiting and circuit breakers
- Comprehensive error handling
- Performance optimization settings

✅ **Security-First**
- TLS/SSL configuration
- Request signing capabilities
- Environment-specific security policies

## Quick Start

### 1. Validate Network Configuration
```bash
# Test all configured networks
python scripts/stellar_network_setup.py --validate

# Test specific network
python scripts/stellar_network_setup.py --validate --network testnet
```

### 2. Create Test Accounts
```bash
# Create test accounts for development
python scripts/stellar_network_setup.py --create-accounts --account-count 5

# Create accounts for specific network
python scripts/stellar_network_setup.py --create-accounts --network testnet
```

### 3. Test Trading Functionality
```bash
# Test basic trading features
python scripts/stellar_network_setup.py --test-trading --network testnet
```

## Network Details

### Testnet Configuration
- **Purpose**: Development and testing
- **Friendbot**: ✅ Available for funding test accounts
- **Horizon**: https://horizon-testnet.stellar.org
- **Soroban RPC**: https://soroban-testnet.stellar.org
- **Network Passphrase**: "Test SDF Network ; September 2015"

### Futurenet Configuration  
- **Purpose**: Testing latest Stellar features
- **Friendbot**: ✅ Available for funding test accounts
- **Horizon**: https://horizon-futurenet.stellar.org
- **Soroban RPC**: https://rpc-futurenet.stellar.org
- **Network Passphrase**: "Test SDF Future Network ; October 2022"

### Mainnet Configuration
- **Purpose**: Production trading
- **Friendbot**: ❌ Not available (real XLM required)
- **Horizon**: https://horizon.stellar.org + fallbacks
- **Soroban RPC**: https://soroban-rpc.stellar.org + fallbacks  
- **Network Passphrase**: "Public Global Stellar Network ; September 2015"

## Environment Configuration

### Development Environment
```yaml
stellar:
  default_network: "testnet"
  features:
    enable_debug_logging: true
    detailed_error_messages: true
```

### Staging Environment
```yaml
stellar:
  default_network: "futurenet"
  monitoring:
    enhanced_monitoring: true
    alert_on_failures: true
```

### Production Environment
```yaml
stellar:
  default_network: "mainnet"
  security:
    strict_validation: true
    enhanced_security: true
```

## Well-Known Assets

### Mainnet Assets
- **USDC**: GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN (centre.io)
- **USDT**: GCQTGZQQ5G4PTM2GL7CDIFKUBIPEC52BROAQIAPW53XBRJVN6ZJVTG6V (tether.to)
- **BTC**: GAUTUYY2THLF7SGITDFMXJVYH3LHDSMGEAKSBU267M2K7A3W543CKUEF (apay.io)
- **ETH**: GBDEVU63Y6NTHJQQZIKVTC23NWLQVP3WJ2RI2OTSJTNYOIGICST6DUXR (apay.io)

### Testnet Assets
- **USDC**: GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5
- **TEST**: GDJVFDG5OCW5PYWHB64MGTHGFF57DRRJEDUEFDEL2SLNIOONHYJWHA3Z

## Popular Trading Pairs

### Mainnet
- XLM-USDC, XLM-USDT, XLM-BTC, XLM-ETH
- USDC-USDT, BTC-USDC, ETH-USDC

### Testnet  
- XLM-USDC, XLM-TEST

## Rate Limiting

### Network-Specific Limits
- **Testnet**: 100 req/sec, 500 burst
- **Futurenet**: 50 req/sec, 200 burst  
- **Mainnet**: 200 req/sec, 1000 burst

### Protection Features
- Automatic backoff on 429 errors
- Jitter to prevent thundering herd
- Circuit breaker on repeated failures

## Health Monitoring

### Automatic Health Checks
- ✅ Horizon API endpoints
- ✅ Soroban RPC endpoints  
- ✅ Core node connectivity
- ✅ Response time monitoring
- ✅ Error rate tracking

### Alert Thresholds
- Network down: 3 consecutive failures
- High latency: >5000ms response time
- High error rate: >10% failed requests

## Advanced Features

### Circuit Breaker
- Failure threshold: 5 consecutive errors
- Recovery timeout: 60 seconds
- Half-open testing: 3 requests max

### Connection Pooling
- Pool size: 20 connections per network
- Max concurrent: 50 requests
- Timeout: 30 seconds with retry

### Caching Strategy
- Account info: 30 seconds TTL
- Order books: 5 seconds TTL
- Asset info: 5 minutes TTL

## Using the Network Manager

```python
from hummingbot.connector.exchange.stellar.stellar_network_manager import (
    StellarNetworkManager, StellarNetwork
)

# Initialize network manager
manager = StellarNetworkManager("config/networks.yml")
await manager.initialize()

# Switch networks
await manager.switch_network(StellarNetwork.TESTNET)

# Get server instance
server = manager.get_server()

# Check network health
health = await manager.check_network_health()
print(f"Network status: {health.status}")

# Get account balance
balance = await manager.get_account_balance("GXXXXXX...")

# Fund test account (testnet/futurenet only)
success = await manager.fund_test_account("GXXXXXX...")
```

## Environment Variables

Override configuration via environment variables:

```bash
export STELLAR_NETWORK=mainnet
export STELLAR_HORIZON_URL=https://custom-horizon.example.com
export STELLAR_SOROBAN_URL=https://custom-soroban.example.com
export STELLAR_RATE_LIMIT=500
```

## Troubleshooting

### Common Issues

1. **Network Connection Failed**
   ```bash
   # Check network health
   python scripts/stellar_network_setup.py --validate --network testnet
   ```

2. **Rate Limiting Errors**
   - Configured automatic backoff will handle this
   - Check rate limit settings in configuration

3. **Friendbot Funding Failed** 
   ```bash
   # Manually fund test account
   curl "https://friendbot.stellar.org/?addr=YOUR_PUBLIC_KEY"
   ```

4. **Invalid Network Configuration**
   - Validate YAML syntax
   - Check network passphrase matches Stellar SDK

### Debug Logging

Enable debug logging in development:
```yaml
logging:
  level: "DEBUG"
  loggers:
    stellar_network_manager: "DEBUG"
```

## Security Considerations

- ⚠️ Never commit real private keys to version control
- ⚠️ Use environment variables for sensitive configuration  
- ⚠️ Validate TLS certificates in production
- ⚠️ Enable request signing for authenticated endpoints
- ⚠️ Use HSM or hardware wallets for production keys

## Support

For issues or questions:
- Check network status: https://status.stellar.org
- Stellar developer docs: https://developers.stellar.org
- Community Discord: https://discord.gg/stellar-dev