# Test Configuration & Local Development Guide

## Overview
This document provides comprehensive instructions for running tests locally, configuring the development environment, and executing the complete test matrix for the Stellar Hummingbot connector.

## Quick Start

### Prerequisites Installation
```bash
# Python 3.9+ (recommended: 3.11)
python --version

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install testing tools
pip install pytest pytest-cov pytest-asyncio pytest-mock pytest-timeout pytest-benchmark
```

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# Set Python path
export PYTHONPATH=$PWD:$PYTHONPATH

# Install Stellar CLI tools (for integration tests)
curl -L https://github.com/stellar/soroban-cli/releases/download/v21.0.0/soroban-cli-21.0.0-x86_64-unknown-linux-gnu.tar.gz | tar xz
sudo mv soroban /usr/local/bin/
```

## Test Execution Matrix

### 1. Unit Tests (Mock-based, No External Calls)

#### Run All Unit Tests
```bash
# Basic execution
pytest tests/unit/ -v

# With coverage report
pytest tests/unit/ --cov=hummingbot.connector.exchange.stellar --cov-report=html --cov-report=term

# Specific test modules
pytest tests/unit/test_stellar_exchange_contract.py -v
pytest tests/unit/test_order_lifecycle.py -v
pytest tests/unit/test_stellar_chain_contract.py -v
pytest tests/unit/test_stellar_security_contract.py -v
pytest tests/unit/test_stellar_soroban_contract.py -v
pytest tests/unit/test_stellar_path_engine_contract.py -v
```

#### Coverage Thresholds
```bash
# Enforce coverage thresholds
pytest tests/unit/ --cov=hummingbot.connector.exchange.stellar --cov-fail-under=80

# Critical modules (90%+ coverage required)
pytest tests/unit/test_stellar_security_contract.py --cov=hummingbot.connector.exchange.stellar.stellar_security --cov-fail-under=90
pytest tests/unit/test_stellar_chain_contract.py --cov=hummingbot.connector.exchange.stellar.stellar_chain_interface --cov-fail-under=90
```

### 2. Security & Compliance Tests

#### Secret Scanning
```bash
# Run comprehensive secret scanning
pytest tests/security/test_stellar_security_compliance.py::TestSecurityCompliance::test_no_hardcoded_secrets_in_repository -v

# Git history scanning
pytest tests/security/test_stellar_security_compliance.py::TestSecurityCompliance::test_git_history_secret_scan -v

# Configuration file security
pytest tests/security/test_stellar_security_compliance.py::TestSecurityCompliance::test_configuration_file_security -v
```

#### Dependency Security
```bash
# Install security tools
pip install safety bandit semgrep

# Run dependency vulnerability scan
safety check --json --output safety-report.json

# Static security analysis
bandit -r hummingbot/connector/exchange/stellar/ -f json -o bandit-report.json

# Run security compliance tests
pytest tests/security/ -v
```

### 3. Integration Tests (Local Stellar Network)

#### Setup Local Stellar Network
```bash
# Option 1: Docker Quickstart (Recommended)
docker run --rm -it -p 8000:8000 \
  --name stellar \
  stellar/quickstart:soroban-dev@sha256:a6b22dd4ba8e68b6067a7d6e1d1d1d9ee30c52f5a9a64e5e4b3b9c6f3b5b1c6d \
  --standalone \
  --enable-soroban-rpc \
  --enable-soroban-diagnostic-events

# Option 2: Local binary installation
git clone https://github.com/stellar/stellar-core.git
cd stellar-core
make -j$(nproc)
./src/stellar-core --conf quickstart.cfg
```

#### Verify Network Health
```bash
# Test Horizon endpoint
curl http://localhost:8000/

# Test Soroban RPC endpoint
curl http://localhost:8000/soroban/rpc \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}'

# Expected response: {"jsonrpc":"2.0","id":1,"result":{"status":"healthy"}}
```

#### Generate Test Accounts
```bash
# Generate and fund test accounts
soroban keys generate --global test-account-1 --network standalone
soroban keys generate --global test-account-2 --network standalone

# Fund accounts with native XLM
soroban keys fund test-account-1 --network standalone
soroban keys fund test-account-2 --network standalone

# Verify funding
soroban keys address test-account-1 | xargs curl -s "http://localhost:8000/accounts/{}"
```

#### Deploy Test Contracts (if available)
```bash
# Navigate to contracts directory (if exists)
cd contracts/

# Build contracts
soroban contract build

# Deploy AMM test contract
CONTRACT_ID=$(soroban contract deploy \
  --wasm target/wasm32-unknown-unknown/release/amm_pool.wasm \
  --source test-account-1 \
  --network standalone)

echo "Contract deployed: $CONTRACT_ID"
```

#### Run Integration Tests
```bash
# Run all integration tests
pytest tests/integration/ \
  --network=local \
  --soroban-rpc=http://localhost:8000/soroban/rpc \
  --horizon-url=http://localhost:8000 \
  -v -s

# Run specific integration test flows
pytest tests/integration/test_soroban_deployment.py -v
pytest tests/integration/test_soroban_amm_flow.py -v
pytest tests/integration/test_soroban_path_payments.py -v
```

### 4. Testnet Integration Tests

#### Configure Testnet Access
```bash
# Set testnet environment variables
export STELLAR_NETWORK_PASSPHRASE="Test SDF Network ; September 2015"
export SOROBAN_RPC_URL="https://soroban-testnet.stellar.org"
export HORIZON_URL="https://horizon-testnet.stellar.org"

# Generate testnet account
soroban keys generate --global testnet-account --network testnet

# Fund account (requires Friendbot)
soroban keys fund testnet-account --network testnet

# Verify account creation
TESTNET_ADDRESS=$(soroban keys address testnet-account)
curl -s "https://horizon-testnet.stellar.org/accounts/$TESTNET_ADDRESS" | jq .
```

#### Run Testnet Validation
```bash
# Run testnet validation tests (slower, real network)
pytest tests/testnet/ \
  --network=testnet \
  --timeout=600 \
  -v -s --tb=short

# Monitor testnet transaction
soroban events --start-ledger $(soroban ledgers --network testnet | jq -r .sequence) --network testnet
```

### 5. Performance & Load Testing

#### Benchmark Tests
```bash
# Install performance testing tools
pip install pytest-benchmark locust

# Run performance benchmarks
pytest tests/performance/ \
  --benchmark-min-rounds=10 \
  --benchmark-warmup=on \
  --benchmark-json=performance-results.json \
  -v

# View benchmark results
cat performance-results.json | jq '.benchmarks[] | {name: .name, mean: .stats.mean}'
```

#### Load Testing
```bash
# Run load tests with Locust
locust -f tests/performance/load_test_stellar_connector.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=1m --headless
```

## SDK Version Compatibility Matrix

### Supported Configurations
```bash
# Python 3.9 + Stellar SDK 7.17.0, 8.0.0, 8.1.0
# Python 3.10 + Stellar SDK 7.17.0, 8.0.0, 8.1.0, 8.2.0
# Python 3.11 + Stellar SDK 7.17.0, 8.0.0, 8.1.0, 8.2.0
# Python 3.12 + Stellar SDK 8.0.0, 8.1.0, 8.2.0
```

### Test Multiple SDK Versions
```bash
# Install specific SDK version
pip install stellar-sdk==8.1.0

# Run compatibility check
python scripts/check_sdk_compatibility.py --sdk-version=8.1.0

# Run unit tests with specific SDK
pytest tests/unit/ -v --tb=short
```

### Automated SDK Matrix Testing
```bash
# Test script for multiple SDK versions
#!/bin/bash
SDK_VERSIONS=("7.17.0" "8.0.0" "8.1.0" "8.2.0")

for version in "${SDK_VERSIONS[@]}"; do
    echo "Testing SDK version: $version"
    
    # Install SDK version
    pip install stellar-sdk==$version
    
    # Run compatibility check
    python scripts/check_sdk_compatibility.py --sdk-version=$version
    
    # Run tests
    pytest tests/unit/ --tb=short --quiet
    
    if [ $? -eq 0 ]; then
        echo "✅ SDK $version: PASS"
    else
        echo "❌ SDK $version: FAIL"
    fi
done
```

## Code Quality & Style Enforcement

### Automated Formatting
```bash
# Install formatting tools
pip install black isort flake8 mypy

# Format code automatically
black --line-length=100 --target-version=py311 hummingbot/connector/exchange/stellar/
isort --profile=black hummingbot/connector/exchange/stellar/
```

### Quality Checks
```bash
# Run all quality checks
./scripts/check_quality.sh

# Manual quality check commands
flake8 hummingbot/connector/exchange/stellar/ --max-line-length=100 --extend-ignore=E203,W503 --max-complexity=12
mypy hummingbot/connector/exchange/stellar/ --strict --ignore-missing-imports --no-implicit-optional

# Type checking with specific modules
mypy hummingbot/connector/exchange/stellar/stellar_security.py --strict
```

## Configuration Files & Environment Variables

### Required Environment Variables
```bash
# .env file (for local development)
STELLAR_SECRET_KEY=""  # Leave empty for test accounts
STELLAR_PUBLIC_KEY=""  # Leave empty for test accounts
SOROBAN_RPC_URL="http://localhost:8000/soroban/rpc"
HORIZON_URL="http://localhost:8000"
STELLAR_NETWORK_PASSPHRASE="Standalone Network ; February 2017"

# Testing configuration
PYTEST_TIMEOUT=300
COVERAGE_THRESHOLD=80
CRITICAL_COVERAGE_THRESHOLD=90
```

### Configuration Validation
```bash
# Validate configuration
python -c "
import os
from pathlib import Path

required_vars = ['SOROBAN_RPC_URL', 'HORIZON_URL', 'STELLAR_NETWORK_PASSPHRASE']
for var in required_vars:
    if not os.getenv(var):
        print(f'⚠️  Missing: {var}')
    else:
        print(f'✅ {var}: {os.getenv(var)}')
"
```

## Troubleshooting Guide

### Common Issues

#### 1. Network Connection Issues
```bash
# Check network connectivity
curl -I http://localhost:8000
curl -I https://horizon-testnet.stellar.org

# Restart local Stellar network
docker restart stellar
```

#### 2. Account Funding Issues
```bash
# Check account balance
ACCOUNT=$(soroban keys address test-account-1)
curl -s "http://localhost:8000/accounts/$ACCOUNT" | jq '.balances'

# Re-fund account
soroban keys fund test-account-1 --network standalone
```

#### 3. Contract Deployment Failures
```bash
# Check contract WASM file
ls -la contracts/*.wasm

# Verify account has sufficient balance for deployment
soroban keys address test-account-1 | xargs curl -s "http://localhost:8000/accounts/{}" | jq '.balances[0].balance'

# Deploy with increased fees
soroban contract deploy --wasm contract.wasm --source test-account-1 --network standalone --fee 10000000
```

#### 4. Test Failures
```bash
# Run tests with detailed output
pytest tests/unit/test_stellar_exchange_contract.py -vvv -s --tb=long

# Run single test method
pytest tests/unit/test_stellar_exchange_contract.py::TestStellarExchangeContract::test_exchange_initialization_success -vvv

# Skip slow tests
pytest tests/unit/ -m "not slow" -v
```

#### 5. Import/Dependency Issues
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify package installation
pip list | grep stellar-sdk
pip list | grep hummingbot

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Debug Commands

#### Network Debugging
```bash
# Check Soroban RPC health
curl http://localhost:8000/soroban/rpc -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getNetwork"}'

# Check latest ledger
curl http://localhost:8000/ledgers?order=desc&limit=1

# Monitor transaction stream
curl -N http://localhost:8000/transactions?cursor=now&include_failed=true
```

#### Contract Debugging
```bash
# Get contract info
soroban contract id wasm --wasm contract.wasm --network standalone

# Invoke contract method
soroban contract invoke \
  --id $CONTRACT_ID \
  --source test-account-1 \
  --network standalone \
  -- get_reserves

# Monitor contract events
soroban events --start-ledger $START_LEDGER --contract $CONTRACT_ID --network standalone
```

### Performance Optimization

#### Test Execution Optimization
```bash
# Parallel test execution
pytest tests/unit/ -n auto --dist worksteal

# Skip slow integration tests during development
pytest tests/unit/ -m "not integration" --tb=short

# Use pytest-xdist for faster execution
pip install pytest-xdist
pytest tests/unit/ -n 4  # Use 4 processes
```

#### Memory Usage Optimization
```bash
# Monitor memory usage during tests
pip install memory-profiler
pytest tests/unit/ --profile

# Run garbage collection between tests
pytest tests/unit/ --forked
```

## Continuous Integration Local Simulation

### Simulate CI Pipeline Locally
```bash
#!/bin/bash
# ci_simulation.sh

set -e

echo "🔍 Running Security Scan..."
python -m pytest tests/security/ -v

echo "📝 Running Code Quality Checks..."
black --check --line-length=100 hummingbot/connector/exchange/stellar/
flake8 hummingbot/connector/exchange/stellar/ --max-line-length=100
mypy hummingbot/connector/exchange/stellar/ --strict --ignore-missing-imports

echo "🧪 Running Unit Tests..."
pytest tests/unit/ --cov=hummingbot.connector.exchange.stellar --cov-fail-under=80

echo "🌐 Starting Integration Tests..."
# Start Stellar network in background
docker run -d --name stellar-test -p 8001:8000 stellar/quickstart:soroban-dev --standalone --enable-soroban-rpc

# Wait for network
sleep 30

# Run integration tests
pytest tests/integration/ --network=local --soroban-rpc=http://localhost:8001/soroban/rpc

# Cleanup
docker stop stellar-test
docker rm stellar-test

echo "✅ All tests passed!"
```

### Make Script Executable
```bash
chmod +x ci_simulation.sh
./ci_simulation.sh
```

## IDE Configuration

### VS Code Settings
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/unit"],
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=100"],
    "python.sortImports.args": ["--profile=black"]
}
```

### PyCharm Configuration
1. Set Project Interpreter: Settings → Project → Python Interpreter → Add → Existing Environment
2. Configure Test Runner: Settings → Tools → Python Integrated Tools → Testing → pytest
3. Set Code Style: Settings → Editor → Code Style → Python → Line Length: 100
4. Enable Type Checking: Settings → Editor → Inspections → Python → Type Checker: mypy

## Summary

This configuration guide provides comprehensive instructions for:

✅ **Local Development Setup** - Python environment, dependencies, and tools  
✅ **Test Execution Matrix** - Unit, integration, security, and performance tests  
✅ **SDK Compatibility Testing** - Multiple Python and Stellar SDK versions  
✅ **Quality Assurance** - Code formatting, linting, and type checking  
✅ **Network Configuration** - Local Stellar network and testnet access  
✅ **Troubleshooting** - Common issues and debugging techniques  
✅ **CI Simulation** - Local pipeline execution and IDE configuration  

For questions or issues, refer to the troubleshooting section or create an issue in the project repository.