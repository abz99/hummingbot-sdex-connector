# Pull Request Checklist

## Overview
This checklist ensures all pull requests meet the production quality standards for the Stellar Hummingbot connector. **All items must be completed** before merging to main or develop branches.

**QA Framework Integration**: This checklist maps to QA IDs in `qa/quality_catalogue.yml` for complete traceability.

---

## 🔐 Security Requirements (MANDATORY)

### Secret Scanning & Security Compliance
- [ ] **No hardcoded secrets** - Run: `pytest tests/security/test_stellar_security_compliance.py::TestSecurityCompliance::test_no_hardcoded_secrets_in_repository -v`
  - **QA_ID**: REQ-SEC-001
  - **Acceptance**: assert len(found_secrets) == 0
  
- [ ] **Git history clean** - Run: `pytest tests/security/test_stellar_security_compliance.py::TestSecurityCompliance::test_git_history_secret_scan -v`
  - **QA_ID**: REQ-SEC-002
  - **Acceptance**: assert len(concerning_commits) == 0

- [ ] **Configuration security** - Run: `pytest tests/security/test_stellar_security_compliance.py::TestSecurityCompliance::test_configuration_file_security -v`
  - **QA_ID**: REQ-SEC-003
  - **Acceptance**: assert len(all_issues) == 0

### Dependencies & Static Analysis
- [ ] **Dependency vulnerability scan** - Run: `safety check --json`
  - **QA_ID**: REQ-SEC-004
  - **Acceptance**: No high or critical vulnerabilities

- [ ] **Static security analysis** - Run: `bandit -r hummingbot/connector/exchange/stellar/ -f json`
  - **QA_ID**: REQ-SEC-005
  - **Acceptance**: No high-severity issues

---

## 🧪 Testing Requirements (MANDATORY)

### Unit Test Coverage
- [ ] **Minimum 80% overall coverage** - Run: `pytest tests/unit/ --cov=hummingbot.connector.exchange.stellar --cov-fail-under=80`
  - **QA_ID**: REQ-TEST-001
  - **Acceptance**: assert coverage >= 80%

- [ ] **Critical modules 90%+ coverage** - Run individual coverage checks:
  ```bash
  pytest tests/unit/test_stellar_security_contract.py --cov=hummingbot.connector.exchange.stellar.stellar_security --cov-fail-under=90
  pytest tests/unit/test_stellar_chain_contract.py --cov=hummingbot.connector.exchange.stellar.stellar_chain_interface --cov-fail-under=90
  ```
  - **QA_ID**: REQ-TEST-002, REQ-TEST-003
  - **Acceptance**: assert coverage >= 90% for security and chain modules

### Core Functionality Tests
- [ ] **Exchange connector contract** - Run: `pytest tests/unit/test_stellar_exchange_contract.py -v`
  - **QA_IDs**: REQ-EXC-001 through REQ-EXC-005
  - **Key Assertions**:
    - assert exchange.status == ConnectorStatus.CONNECTED
    - assert len(trading_pairs) > 0
    - assert balance_response.success == True

- [ ] **Order lifecycle validation** - Run: `pytest tests/unit/test_order_lifecycle.py -v`
  - **QA_IDs**: REQ-ORD-001 through REQ-ORD-006
  - **Key Assertions**:
    - assert order.status == OrderStatus.NEW
    - assert order.filled_amount == expected_fill
    - assert correlation_id in order_tracking

- [ ] **Chain interface compliance** - Run: `pytest tests/unit/test_stellar_chain_contract.py -v`
  - **QA_IDs**: REQ-CHAIN-001 through REQ-CHAIN-007
  - **Key Assertions**:
    - assert transaction.sequence == account_sequence + 1
    - assert fee_bump_factor >= 1.1
    - assert len(fallback_servers) > 0

- [ ] **Security contract validation** - Run: `pytest tests/unit/test_stellar_security_contract.py -v`
  - **QA_IDs**: REQ-SEC-006 through REQ-SEC-012
  - **Key Assertions**:
    - assert signature1 == signature2  # Deterministic signing
    - assert key_rotation_success == True
    - assert hsm_failover_time < 5.0

### Smart Contract & Path Engine Tests
- [ ] **Soroban contract integration** - Run: `pytest tests/unit/test_stellar_soroban_contract.py -v`
  - **QA_IDs**: REQ-SOB-001 through REQ-SOB-007
  - **Key Assertions**:
    - assert simulation.success == True
    - assert contract.address is not None
    - assert gas_used < MAX_GAS_LIMIT

- [ ] **Path payment engine** - Run: `pytest tests/unit/test_stellar_path_engine_contract.py -v`
  - **QA_IDs**: REQ-PATH-001 through REQ-PATH-006
  - **Key Assertions**:
    - assert path.total_cost < source_amount * 1.05
    - assert arbitrage_profit > Decimal('0')
    - assert mev_protection_active == True

---

## 📊 Code Quality Requirements (MANDATORY)

### Style & Formatting
- [ ] **Code formatting** - Run: `black --check --line-length=100 --target-version=py311 hummingbot/connector/exchange/stellar/`
  - **QA_ID**: REQ-STYLE-001
  - **Acceptance**: No formatting changes required

- [ ] **Import sorting** - Run: `isort --check-only --profile=black hummingbot/connector/exchange/stellar/`
  - **QA_ID**: REQ-STYLE-002
  - **Acceptance**: Imports properly sorted

- [ ] **Linting compliance** - Run: `flake8 hummingbot/connector/exchange/stellar/ --max-line-length=100 --extend-ignore=E203,W503 --max-complexity=12`
  - **QA_ID**: REQ-STYLE-003
  - **Acceptance**: Zero linting violations

### Type Safety
- [ ] **Type checking** - Run: `mypy hummingbot/connector/exchange/stellar/ --strict --ignore-missing-imports --no-implicit-optional`
  - **QA_ID**: REQ-TYPE-001
  - **Acceptance**: Zero type errors

- [ ] **Critical module type safety** - Run individual mypy checks on core modules
  - **QA_ID**: REQ-TYPE-002
  - **Acceptance**: Strict typing on security, chain, and connector modules

---

## 🌐 Integration & Compatibility (CONDITIONAL)

### SDK Compatibility (Required for SDK changes)
- [ ] **SDK compatibility check** - Run: `python scripts/check_sdk_compatibility.py --sdk-version=$(pip show stellar-sdk | grep Version | cut -d' ' -f2)`
  - **QA_ID**: REQ-COMPAT-001
  - **Acceptance**: assert compatibility_check == True

- [ ] **Multiple SDK version testing** (if SDK version changes):
  ```bash
  pip install stellar-sdk==7.17.0 && pytest tests/unit/ --tb=short
  pip install stellar-sdk==8.1.0 && pytest tests/unit/ --tb=short
  pip install stellar-sdk==8.2.0 && pytest tests/unit/ --tb=short
  ```
  - **QA_ID**: REQ-COMPAT-002
  - **Acceptance**: Tests pass on all supported SDK versions

### Integration Testing (Required for significant changes)
- [ ] **Local network integration** (if network layer changes) - Run: `pytest tests/integration/ --network=local -v`
  - **QA_ID**: REQ-INT-001
  - **Acceptance**: All integration tests pass

- [ ] **Testnet validation** (for major releases) - Run: `pytest tests/testnet/ --network=testnet --timeout=600 -v`
  - **QA_ID**: REQ-INT-002
  - **Acceptance**: Testnet integration successful

---

## 📈 Performance & Reliability (CONDITIONAL)

### Performance Benchmarks (Required for performance-critical changes)
- [ ] **Latency benchmarks** - Run: `pytest tests/performance/ --benchmark-min-rounds=10 -v`
  - **QA_ID**: REQ-PERF-001
  - **Acceptance**: 
    - Order placement latency < 500ms
    - Balance query latency < 200ms
    - Path finding latency < 2s

- [ ] **Memory usage validation** - Run: `pytest tests/unit/ --profile-memory`
  - **QA_ID**: REQ-PERF-002
  - **Acceptance**: No memory leaks detected

### Load Testing (Required for scalability changes)
- [ ] **Concurrent operation testing** - Run: `pytest tests/performance/test_concurrent_operations.py -v`
  - **QA_ID**: REQ-PERF-003
  - **Acceptance**: 
    - Support 50+ concurrent orders
    - 99.9% success rate under load

---

## 📋 Documentation & Traceability (MANDATORY)

### QA Documentation
- [ ] **QA ID mapping verified** - All new test functions include proper QA_ID docstrings
  - **Example**: `"""QA_ID: REQ-EXC-001\nAcceptance Criteria: assert exchange.status == ConnectorStatus.CONNECTED"""`
  - **Verification**: grep -r "QA_ID:" tests/ | wc -l should match catalogue entries

- [ ] **Quality catalogue updated** - If new requirements added, update `qa/quality_catalogue.yml`
  - **Process**: Add new requirement → Generate JSON → Update test files → Verify mapping

### Code Documentation
- [ ] **Docstrings present** - All new public methods have comprehensive docstrings
- [ ] **Type hints complete** - All function parameters and return types annotated
- [ ] **Complex logic commented** - Non-trivial algorithms include explanatory comments

---

## 🔄 Version Control & Git Hygiene

### Commit Quality
- [ ] **Descriptive commit messages** - Follow format: `"type(scope): description\n\nDetails\n\nQA_IDs: REQ-XXX-001"`
- [ ] **Atomic commits** - Each commit represents a single logical change
- [ ] **No merge conflicts** - Branch rebased against target branch

### Branch Requirements
- [ ] **Feature branch naming** - Follow pattern: `feature/QA-ID-description` or `hotfix/issue-description`
- [ ] **Target branch correct** - PR targets `develop` (features) or `main` (hotfixes)

---

## 🚀 Pre-Merge Validation (AUTOMATED)

### CI Pipeline Status
- [ ] **All CI checks pass** - GitHub Actions workflow completed successfully
  - Security scan: ✅
  - Code quality: ✅
  - Unit tests (matrix): ✅
  - Integration tests: ✅
  
- [ ] **No failing tests** - Zero test failures in CI pipeline
- [ ] **Coverage maintained** - Overall coverage did not decrease

### Final Verification
- [ ] **Manual testing completed** (if UI/UX changes)
- [ ] **Breaking changes documented** (if API changes)
- [ ] **Migration guide provided** (if database/config changes)

---

## 📝 Reviewer Checklist (FOR REVIEWERS)

### Code Review
- [ ] **Architecture compliance** - Code follows established patterns and conventions
- [ ] **Security review** - No security vulnerabilities introduced
- [ ] **Performance impact** - No significant performance degradation
- [ ] **Error handling** - Proper exception handling and error messages

### Testing Review
- [ ] **Test coverage adequate** - New code has corresponding tests
- [ ] **Test quality** - Tests are meaningful and catch potential regressions
- [ ] **Mock usage appropriate** - External dependencies properly mocked
- [ ] **Edge cases covered** - Tests include error conditions and boundary cases

### Documentation Review
- [ ] **Code clarity** - Code is self-documenting and well-structured
- [ ] **API documentation** - Public interfaces properly documented
- [ ] **QA traceability** - Requirements mapped to tests correctly

---

## ⚠️ BLOCKING CONDITIONS

**The following conditions BLOCK merging:**

1. **Security Issues**: Any hardcoded secrets, security vulnerabilities, or compliance failures
2. **Test Failures**: Any failing unit tests, integration tests, or coverage below thresholds
3. **Quality Violations**: Linting errors, type errors, or formatting issues
4. **Missing QA Mapping**: New functionality without corresponding QA IDs and tests
5. **CI Pipeline Failures**: Any stage of the CI pipeline failing
6. **Reviewer Approval**: Less than 2 approving reviews for main branch merges

---

## 🎯 Quick Validation Commands

### Complete Pre-Merge Check
```bash
#!/bin/bash
# run_pr_checks.sh

set -e

echo "🔍 Running security scan..."
pytest tests/security/ -v

echo "📝 Checking code quality..."
black --check --line-length=100 hummingbot/connector/exchange/stellar/
flake8 hummingbot/connector/exchange/stellar/ --max-line-length=100
mypy hummingbot/connector/exchange/stellar/ --strict --ignore-missing-imports

echo "🧪 Running unit tests with coverage..."
pytest tests/unit/ --cov=hummingbot.connector.exchange.stellar --cov-fail-under=80 --cov-report=term

echo "✅ All PR checks passed!"
```

### Make Script Executable
```bash
chmod +x run_pr_checks.sh
./run_pr_checks.sh
```

---

## 📞 Support & Escalation

### For Issues or Questions:
1. **Test Failures**: Check `CONFIGURATION.md` troubleshooting section
2. **Quality Tool Issues**: Update tools or configuration in `docs/QUALITY_GUIDELINES.md`
3. **QA Mapping Questions**: Reference `qa/quality_catalogue.yml` for requirement details
4. **CI Pipeline Issues**: Check `.github/workflows/ci.yml` configuration

### Escalation Process:
1. **Blocking Issues**: Tag `@team-leads` in PR comments
2. **Security Concerns**: Create security issue with `security` label
3. **Infrastructure Problems**: Contact DevOps team
4. **Process Questions**: Reference this checklist and quality guidelines

---

**Note**: This checklist evolves with the project. Updates require team approval and must maintain backward compatibility with existing QA framework.