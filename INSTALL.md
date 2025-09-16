# Stellar Hummingbot Connector v3.0 - Installation Guide

## 🚀 Quick Installation (5 Minutes)

**Get the Stellar Hummingbot Connector running in under 5 minutes with automated setup.**

---

## 📋 Prerequisites Check

Before starting, ensure you have:

✅ **Python 3.11+** (Required)
✅ **Git** (Required)
✅ **Docker** (Optional - for advanced features)
✅ **10GB free disk space** (Recommended)

### Quick Prerequisites Check
```bash
# Run this command to verify your system:
curl -fsSL https://raw.githubusercontent.com/stellar/hummingbot-connector-v3/main/scripts/check_prerequisites.sh | bash
```

---

## 🏃‍♂️ One-Click Installation

### Option 1: Automated Setup (Recommended)
```bash
# Download and run the automated installer
curl -fsSL https://raw.githubusercontent.com/stellar/hummingbot-connector-v3/main/scripts/install.sh | bash

# Follow the prompts - installation takes 2-3 minutes
```

### Option 2: Manual Installation
```bash
# 1. Clone the repository
git clone https://github.com/abz99/hummingbot-sdex-connector.git
cd hummingbot-connector-v3

# 2. Run the setup script
./scripts/setup.sh

# 3. Activate the environment
source venv/bin/activate

# 4. Verify installation
python -c "from hummingbot.connector.exchange.stellar import StellarExchange; print('✅ Installation successful!')"
```

---

## 🔧 Platform-Specific Instructions

### 🪟 Windows
```powershell
# Install Python 3.11+ from python.org
# Install Git from git-scm.com

# Open PowerShell as Administrator and run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then run the installation:
git clone https://github.com/abz99/hummingbot-sdex-connector.git
cd hummingbot-connector-v3
.\scripts\setup.ps1
```

### 🍎 macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install prerequisites
brew install python@3.11 git

# Run installation
curl -fsSL https://raw.githubusercontent.com/stellar/hummingbot-connector-v3/main/scripts/install.sh | bash
```

### 🐧 Ubuntu/Debian Linux
```bash
# Update package list
sudo apt update

# Install prerequisites
sudo apt install -y python3.11 python3.11-venv python3-pip git curl

# Run installation
curl -fsSL https://raw.githubusercontent.com/stellar/hummingbot-connector-v3/main/scripts/install.sh | bash
```

### 🔴 Red Hat/CentOS/Fedora
```bash
# Install prerequisites
sudo dnf install -y python3.11 python3-pip git curl

# Run installation
curl -fsSL https://raw.githubusercontent.com/stellar/hummingbot-connector-v3/main/scripts/install.sh | bash
```

---

## ✅ Verification Steps

### 1. Basic Functionality Test
```bash
# Activate the environment
source venv/bin/activate

# Run the quick test
python -m pytest tests/unit/test_stellar_exchange_contract.py::TestStellarExchangeInitialization::test_exchange_initialization_success -v

# Expected output: PASSED
```

### 2. Network Connectivity Test
```bash
# Test Stellar network connectivity
python scripts/test_connectivity.py

# Expected output:
# ✅ Stellar Testnet: Connected
# ✅ Soroban RPC: Available
# ✅ All systems operational
```

### 3. Trading Interface Test
```bash
# Test the trading interface
python examples/basic_trading_test.py

# Expected output:
# ✅ Exchange initialized
# ✅ Market data received
# ✅ Ready for trading
```

---

## 🎯 Quick Start Trading

### Basic Trading Setup
```python
# Create a simple trading bot (examples/quick_start.py)
from hummingbot.connector.exchange.stellar import StellarExchange
import asyncio

async def main():
    # Initialize the connector
    exchange = StellarExchange(
        trading_pairs=["XLM-USDC"],
        network="testnet"  # Use testnet for initial testing
    )

    # Start the exchange
    await exchange.start()

    # Get market data
    ticker = await exchange.get_ticker("XLM-USDC")
    print(f"XLM-USDC Price: {ticker.last_price}")

    # Stop the exchange
    await exchange.stop()

# Run the example
asyncio.run(main())
```

### Run the Quick Start
```bash
# Run the basic trading example
python examples/quick_start.py
```

---

## 🏗️ Advanced Installation Options

### Docker Installation
```bash
# Pull the pre-built image
docker pull stellar/hummingbot-connector-v3:latest

# Run with Docker
docker run -it --rm \
  -v $(pwd)/config:/app/config \
  stellar/hummingbot-connector-v3:latest
```

### Development Installation
```bash
# Clone with development dependencies
git clone https://github.com/abz99/hummingbot-sdex-connector.git
cd hummingbot-connector-v3

# Install in development mode
pip install -e .
pip install -r requirements-dev.txt

# Run development tests
pytest tests/unit/ -v
```

### Production Installation
```bash
# Production deployment
./scripts/production_install.sh

# This includes:
# - Optimized dependencies
# - Security hardening
# - Monitoring setup
# - Performance tuning
```

---

## 🚨 Troubleshooting

### Common Issues and Solutions

#### ❌ "Python 3.11 not found"
```bash
# Ubuntu/Debian
sudo apt install python3.11 python3.11-venv

# macOS
brew install python@3.11

# Windows
# Download from python.org and install
```

#### ❌ "Permission denied" on scripts
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Or run with bash directly
bash scripts/setup.sh
```

#### ❌ "Virtual environment activation failed"
```bash
# Recreate the virtual environment
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### ❌ "Network connection failed"
```bash
# Check internet connectivity
curl -I https://horizon-testnet.stellar.org

# Check firewall settings
# Ensure ports 443 and 80 are open for outbound connections
```

#### ❌ "Import errors"
```bash
# Check Python path
export PYTHONPATH=$PWD:$PYTHONPATH

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Get Help
- **Quick Help**: Run `python scripts/diagnostics.py` for automated troubleshooting
- **Documentation**: See [CONFIGURATION.md](./CONFIGURATION.md) for detailed setup
- **GitHub Issues**: [Create an issue](https://github.com/abz99/hummingbot-sdex-connector/issues) for bugs
- **Community Discord**: Join our [Discord server](https://discord.gg/stellar) for support

---

## 🔄 Upgrade Instructions

### Upgrade to Latest Version
```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Run upgrade script
./scripts/upgrade.sh

# Verify upgrade
python -c "from hummingbot.connector.exchange.stellar import __version__; print(f'Version: {__version__}')"
```

### Migration Between Versions
```bash
# Backup current configuration
cp -r config config.backup

# Run migration script
python scripts/migrate_config.py --from-version=2.0 --to-version=3.0

# Test migration
python scripts/test_config.py
```

---

## 📊 Post-Installation Checklist

### ✅ **Installation Verification**
- [ ] Python 3.11+ installed and accessible
- [ ] Virtual environment created and activated
- [ ] All dependencies installed without errors
- [ ] Basic connectivity test passes
- [ ] Trading interface test successful

### ✅ **Configuration Setup**
- [ ] Network configuration reviewed (testnet vs mainnet)
- [ ] Security settings configured
- [ ] Trading pairs selected
- [ ] Risk management parameters set

### ✅ **Testing & Validation**
- [ ] Unit tests passing
- [ ] Basic trading example works
- [ ] Network connectivity verified
- [ ] Market data streaming functional

### ✅ **Security Review**
- [ ] API keys properly configured (if using)
- [ ] Wallet security measures in place
- [ ] Network security validated
- [ ] Backup procedures established

---

## 🎓 Next Steps

### 1. **Learn the Basics**
- Review [README.md](./README.md) for feature overview
- Read [USER_ONBOARDING_GUIDE.md](./docs/USER_ONBOARDING_GUIDE.md) for comprehensive setup
- Explore [examples/](./examples/) directory for sample trading strategies

### 2. **Configure for Trading**
- Set up your [trading configuration](./config/README.md)
- Configure [security settings](./docs/PRODUCTION_SECURITY_GUIDE.md)
- Review [risk management options](./docs/RISK_MANAGEMENT.md)

### 3. **Start Trading**
- Begin with [testnet trading](./docs/TESTNET_GUIDE.md)
- Monitor with [observability tools](./observability/README.md)
- Scale with [production deployment](./docs/KUBERNETES_DEPLOYMENT_GUIDE.md)

### 4. **Join the Community**
- [GitHub Discussions](https://github.com/abz99/hummingbot-sdex-connector/discussions)
- [Discord Community](https://discord.gg/stellar)
- [Documentation Wiki](https://github.com/abz99/hummingbot-sdex-connector/wiki)

---

## 📞 Support

### **Installation Support**
- **Email**: support@stellar.org
- **Discord**: [#hummingbot-connector](https://discord.gg/stellar)
- **GitHub**: [Issues & Discussions](https://github.com/abz99/hummingbot-sdex-connector)

### **Emergency Support**
- **Security Issues**: security@stellar.org
- **Critical Bugs**: Create a [high-priority issue](https://github.com/abz99/hummingbot-sdex-connector/issues/new?template=bug-critical.md)

---

**🎉 Congratulations! You've successfully installed the Stellar Hummingbot Connector v3.0**

*Ready to start your algorithmic trading journey on the Stellar network!*