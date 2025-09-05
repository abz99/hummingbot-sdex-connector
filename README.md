# Stellar Hummingbot Connector v3

A production-ready, enterprise-grade connector for integrating Stellar Lumens (XLM) trading with the Hummingbot algorithmic trading platform.

## 🚨 **CRITICAL: Development Rules**

**Before contributing, read [`DEVELOPMENT_RULES.md`](./DEVELOPMENT_RULES.md)**

### **Golden Rule: NEVER SKIP FAILING TESTS**
- All tests must pass before committing
- Fix root causes, don't ignore failures  
- Failing tests reveal bugs and design flaws
- See our [enforcement tools](#test-enforcement)

## Features

### 🔐 **Enterprise Security**
- Multi-tier security levels (Development, Testing, Staging, Production)
- Hardware wallet support (Ledger, Trezor) with BIP-44 derivation
- HashiCorp Vault integration for key management
- Hierarchical Deterministic (HD) wallet implementation
- Hardware Security Module (HSM) integration architecture

### 🏗️ **Modern Architecture**  
- Async/await patterns throughout
- Type-safe implementation with mypy compliance
- Structured logging with correlation IDs
- Comprehensive error classification and handling
- Modular design with clear separation of concerns

### 📊 **Production Features**
- Multi-network support (Testnet, Futurenet, Mainnet)
- Runtime asset verification against stellar.toml
- Prometheus/StatsD metrics collection
- Connection health monitoring with alerting
- HTTP/2 optimized connection management

### ✅ **Quality Assurance**
- 100% test coverage (84/84 tests passing)
- Comprehensive error scenario testing
- Performance benchmarking
- Security validation tests

## Quick Start

### Prerequisites
- Python 3.11+
- Virtual environment recommended

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd stellar-hummingbot-connector-v3

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
pip install -r requirements-dev.txt

# Run tests to verify setup
python -m pytest
```

### Basic Usage

```python
from hummingbot.connector.exchange.stellar import StellarExchange

# Initialize connector
exchange = StellarExchange(
    trading_pairs=["XLM-USD"],
    network="testnet"
)

# Start trading
await exchange.start()
```

## Development

### Test Enforcement

We maintain strict test quality with automated enforcement:

```bash
# Check for failing/skipped tests
./scripts/check-failing-tests.sh

# Run full test suite
python -m pytest

# Run with coverage
python -m pytest --cov=hummingbot --cov-report=html
```

### Code Quality Tools

```bash
# Format code
black .

# Lint code  
flake8 src/ test/

# Type checking
mypy src/

# Run all checks
pre-commit run --all-files
```

### Security Testing

```bash
# Run security-specific tests
python -m pytest -m security

# Test all security components
python -m pytest test/unit/test_stellar_security_comprehensive.py
```

## Architecture

### Core Components

- **`stellar_exchange.py`**: Main exchange interface
- **`stellar_security_manager.py`**: Enterprise security management  
- **`stellar_network_manager.py`**: Network connection handling
- **`stellar_order_manager.py`**: Order lifecycle management

### Security Infrastructure

- **Key Management**: Multi-backend storage (Memory, FileSystem, HSM, Vault)
- **Hardware Wallets**: Ledger/Trezor integration with BIP-44 paths
- **Key Derivation**: PBKDF2, Scrypt, HKDF, Argon2 algorithms
- **Test Accounts**: Advanced lifecycle management and pooling

### Testing Strategy

- **Unit Tests**: Fast, isolated component testing
- **Integration Tests**: Cross-component functionality
- **Security Tests**: Cryptographic validation and attack scenarios  
- **Performance Tests**: Benchmarking and load testing

## Contributing

### Development Workflow

1. **Read** [`DEVELOPMENT_RULES.md`](./DEVELOPMENT_RULES.md) thoroughly
2. **Create** feature branch from `master`
3. **Write** tests first (TDD approach)
4. **Implement** functionality with proper error handling
5. **Ensure** all tests pass (100% success rate required)
6. **Submit** pull request with descriptive commits

### Commit Standards

- Descriptive commit messages with context
- Include co-authorship for AI assistance  
- Small, focused commits that tell a story
- All tests must pass before committing

### Code Review

- Security-focused review for all changes
- Architecture alignment verification
- Performance impact assessment
- Test coverage validation

## Support

### Documentation
- API documentation: `docs/api/`  
- Architecture decisions: `docs/adr/`
- Security guidelines: `docs/security/`

### Getting Help
- Create GitHub issue for bugs
- Discussion forum for questions
- Security issues: security@example.com

## License

[MIT License](LICENSE) - See LICENSE file for details.

---

**Built with enterprise-grade security and reliability for production trading environments.**