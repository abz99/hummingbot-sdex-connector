# CI Troubleshooting Guide

## Overview
This guide provides comprehensive troubleshooting steps for the Stellar Hummingbot Connector v3.0 CI pipeline.

## Automated CI Health Monitoring System

### Core Components
1. **CI Health Monitor** (`.github/ci-monitor.py`) - Comprehensive pipeline analysis
2. **Post-Push Monitor** (`.github/post-push-ci-monitor.py`) - Automated verification after push
3. **CI Push Wrapper** (`scripts/ci-push-wrapper.sh`) - Integrated push with health checks
4. **Health Dashboard** (`.github/workflows/ci-health-dashboard.yml`) - Continuous monitoring

### Quick Diagnostics

#### Check CI Health
```bash
# Run comprehensive health analysis
python .github/ci-monitor.py

# Monitor specific workflow
python .github/ci-monitor.py --workflow ci.yml

# Generate detailed report
python .github/ci-monitor.py --output health-report.md
```

#### Test Post-Push Monitoring
```bash
# Monitor current commit
python .github/post-push-ci-monitor.py --save-results

# Monitor specific commit
python .github/post-push-ci-monitor.py --commit abc1234 --save-results
```

#### Use Automated Push with Verification
```bash
# Push with automatic CI health verification
./scripts/ci-push-wrapper.sh main "Feature implementation"
```

## Common Issues and Solutions

### 1. Missing Dependencies (Most Common)

**Symptoms:**
- Workflows fail during dependency installation
- `ModuleNotFoundError` in CI logs
- Missing security tools (bandit, safety, semgrep)

**Solution:**
```bash
# Check if requirements-dev.txt exists
ls requirements-dev.txt

# If missing, create it:
cat > requirements-dev.txt << 'EOF'
# Security Tools
safety==3.2.7
bandit==1.7.9
semgrep==1.87.0

# Performance Testing
pytest-benchmark==4.0.0
locust==2.32.2

# Development Tools
pre-commit==3.8.0
black==24.8.0
isort==5.13.2
flake8==7.1.1
mypy==1.11.2

# Testing Enhancement
pytest-xdist==3.6.0
pytest-mock==3.14.0
pytest-timeout==2.3.1

# Coverage Tools
coverage[toml]==7.6.1
pytest-cov==5.0.0
EOF
```

### 2. GitHub Secrets Configuration

**Required Secrets:**
- `GITHUB_TOKEN` - For CI monitoring API access
- `DOCKER_REGISTRY_TOKEN` - For container deployment
- `STELLAR_TESTNET_KEY` - For testnet integration tests

**Check Configuration:**
```bash
# Verify token access
gh auth status

# List repository secrets
gh secret list
```

### 3. Test Failures

**Common Test Issues:**
- Stellar SDK version compatibility
- Network connectivity in CI environment
- Missing test fixtures or data

**Debug Steps:**
```bash
# Run tests locally with verbose output
pytest tests/ -v --tb=long

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v -k "not testnet"

# Check test coverage
pytest tests/ --cov=hummingbot/connector/exchange/stellar/
```

### 4. Container Build Issues

**Symptoms:**
- Docker build failures
- Missing base images
- Registry authentication errors

**Solution:**
```bash
# Test local build
docker build -f deployment/docker/Dockerfile.production .

# Check registry access
docker login ghcr.io

# Verify Dockerfile syntax
docker build --dry-run -f deployment/docker/Dockerfile.production .
```

### 5. Workflow Timeout Issues

**Configuration:**
- Default timeout: 30 minutes
- Long-running tests may need adjustment
- Network-dependent tests require longer timeouts

**Fix in workflow files:**
```yaml
jobs:
  test:
    timeout-minutes: 45  # Increase as needed
```

## Advanced Diagnostics

### Workflow Run Analysis

#### Get Recent Workflow Status
```bash
# List recent workflow runs
gh run list --limit 10

# View specific run details
gh run view RUN_ID

# Download run logs
gh run download RUN_ID
```

#### Monitor Workflow in Real-time
```bash
# Watch running workflow
gh run watch

# Follow specific workflow
gh workflow run ci.yml --ref main
gh run watch
```

### Local Environment Validation

#### Check Python Environment
```bash
# Verify Python version (3.9+ required)
python --version

# Check installed packages
pip list | grep -E "(stellar|pytest|flake8|black|mypy)"

# Validate test environment
python -m pytest --collect-only tests/
```

#### Check Stellar SDK Compatibility
```bash
# Run SDK compatibility check
python scripts/check_sdk_compatibility.py

# Test Stellar network connectivity
python scripts/test_network_connectivity.py
```

## Automated Recovery

### Emergency Recovery Script
```bash
# Run emergency recovery
./.claude_emergency_recovery.sh

# Reset CI environment
./scripts/reset_ci_environment.sh
```

### Reset and Rebuild
```bash
# Clean and rebuild environment
rm -rf __pycache__ .pytest_cache
pip install -r requirements-dev.txt
python -m pytest tests/ --collect-only
```

## Monitoring and Alerts

### Continuous Monitoring
The CI Health Dashboard runs every 4 hours and:
- Monitors all workflow success rates
- Detects degraded pipeline health
- Automatically creates issues for critical failures
- Generates comprehensive health reports

### Health Status Indicators
- **🟢 Healthy**: All workflows passing, success rate > 80%
- **🟡 Degraded**: Some failures, success rate 60-80%
- **🔴 Failing**: Critical issues, success rate < 60%

### Notification Channels
1. **GitHub Issues**: Automatically created for critical failures
2. **Workflow Artifacts**: Detailed reports saved for 30 days
3. **PR Comments**: Health status on pull requests

## Best Practices

### Before Pushing
1. Run local tests: `pytest tests/ -v`
2. Check code quality: `flake8 . && black --check . && mypy .`
3. Verify dependencies: `pip check`
4. Use the push wrapper: `./scripts/ci-push-wrapper.sh`

### Monitoring Workflow Health
1. Review weekly CI health reports
2. Address degraded workflows promptly
3. Keep dependencies updated
4. Monitor resource usage and timeouts

### Emergency Procedures
1. **Critical Failure**: Run emergency recovery script
2. **Persistent Issues**: Check GitHub status page
3. **Security Alerts**: Review and update dependencies
4. **Performance Issues**: Optimize tests and workflows

## Contact and Support

### Documentation
- [CI Health Dashboard](../.github/workflows/ci-health-dashboard.yml)
- [Monitoring Scripts](../.github/)
- [Project Status](../PROJECT_STATUS.md)

### Quick Reference
```bash
# Essential CI commands
python .github/ci-monitor.py                    # Health check
./scripts/ci-push-wrapper.sh                   # Safe push
pytest tests/ -v                               # Local tests
gh run list                                    # Recent runs
gh workflow view ci.yml                        # Workflow status
```

Remember: The automated monitoring system will detect and report most issues automatically. Check the latest CI health report in GitHub Actions artifacts for detailed analysis.