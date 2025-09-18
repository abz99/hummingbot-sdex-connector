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

### ✅ **Quality Assurance Framework**
- **Comprehensive QA System**: Machine-readable quality catalogue with 35+ requirements
- **Test Coverage**: 80%+ baseline, 90%+ for critical modules (security, chain, orders)
- **Multi-layer Testing**: Unit, integration, security compliance, and performance tests
- **Automated Validation**: CI pipeline with matrix testing across Python/SDK versions
- **Traceability**: QA ID mapping from requirements to test implementations

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

# Run with coverage (enforce thresholds)
python -m pytest --cov=hummingbot --cov-report=html --cov-fail-under=80

# Check critical module coverage (90%+ required)
python scripts/check_critical_coverage.py --coverage-file=coverage.xml

# Validate SDK compatibility
python scripts/check_sdk_compatibility.py --sdk-version=$(pip show stellar-sdk | grep Version | cut -d' ' -f2)
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
# Run security compliance tests
python -m pytest tests/security/test_stellar_security_compliance.py -v

# Comprehensive secret scanning
python -m pytest tests/security/test_stellar_security_compliance.py::TestSecurityCompliance::test_no_hardcoded_secrets_in_repository -v

# Git history security scan
python -m pytest tests/security/test_stellar_security_compliance.py::TestSecurityCompliance::test_git_history_secret_scan -v
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

### QA Framework & Quality Assurance

Our comprehensive QA framework ensures production-ready code quality:

#### **Quality Catalogue** 📋
- **Location**: `qa/quality_catalogue.yml` (machine-readable) and `qa/quality_catalogue.json`
- **Requirements**: 35+ traced requirements with QA IDs (REQ-EXC-001, REQ-ORD-001, etc.)
- **Mapping**: Each requirement maps to specific test functions with acceptance criteria

#### **Test Structure** 🧪
```
tests/
├── unit/                          # Unit tests (mock-based, no external calls)
│   ├── test_stellar_exchange_contract.py      # QA_IDs: REQ-EXC-001 to REQ-EXC-005
│   ├── test_order_lifecycle.py                # QA_IDs: REQ-ORD-001 to REQ-ORD-006
│   ├── test_stellar_chain_contract.py         # QA_IDs: REQ-CHAIN-001 to REQ-CHAIN-007
│   ├── test_stellar_security_contract.py      # QA_IDs: REQ-SEC-006 to REQ-SEC-012
│   ├── test_stellar_soroban_contract.py       # QA_IDs: REQ-SOB-001 to REQ-SOB-007
│   └── test_stellar_path_engine_contract.py   # QA_IDs: REQ-PATH-001 to REQ-PATH-006
├── integration/                   # Integration tests with local/testnet networks
│   └── integration_test_soroban_flow.md       # Comprehensive Soroban test guide
└── security/                      # Security compliance tests
    └── test_stellar_security_compliance.py    # QA_IDs: REQ-SEC-001 to REQ-SEC-005
```

#### **Coverage Requirements** 📊
- **Baseline**: 80% coverage for all modules
- **Critical Modules**: 90%+ coverage required
  - `stellar_security*` modules: 95%+
  - `stellar_chain_interface`: 90%+
  - `stellar_order_manager`: 90%+

#### **Quality Tools** ⚙️
```bash
# Run comprehensive pre-commit checks
./run_pr_checks.sh

# QA catalogue maintenance
python -c "import yaml, json; json.dump(yaml.safe_load(open('qa/quality_catalogue.yml')), open('qa/quality_catalogue.json', 'w'), indent=2)"
```

### Development Workflow

1. **Read** [`DEVELOPMENT_RULES.md`](./DEVELOPMENT_RULES.md) thoroughly
2. **Review** [`PR_CHECKLIST.md`](./PR_CHECKLIST.md) for requirements  
3. **Create** feature branch from `develop`
4. **Write** tests first with proper QA ID mapping:
   ```python
   def test_new_feature(self):
       """New feature test.
       
       QA_ID: REQ-NEW-001
       Acceptance Criteria: assert new_feature.result == expected_result
       """
   ```
5. **Implement** functionality with comprehensive error handling
6. **Ensure** all PR checklist items pass (security, coverage, quality)
7. **Submit** pull request following the checklist

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
- **Quality Guidelines**: [`docs/QUALITY_GUIDELINES.md`](./docs/QUALITY_GUIDELINES.md) - Comprehensive quality standards
- **QA Framework**: [`qa/quality_catalogue.yml`](./qa/quality_catalogue.yml) - Machine-readable requirements
- **Testing Guide**: [`CONFIGURATION.md`](./CONFIGURATION.md) - Local testing and setup instructions
- **PR Process**: [`PR_CHECKLIST.md`](./PR_CHECKLIST.md) - Complete pull request checklist
- **Integration Tests**: [`tests/integration/integration_test_soroban_flow.md`](./tests/integration/integration_test_soroban_flow.md)

### Getting Help
- Create GitHub issue for bugs
- Discussion forum for questions
- Security issues: security@example.com

## License

[MIT License](LICENSE) - See LICENSE file for details.

---

**Built with enterprise-grade security and reliability for production trading environments.**# Force workflow cache refresh
