# Stellar Hummingbot Connector - DevOps CI/CD Best Practices

## Overview
This document outlines CI/CD best practices, workflow templates, and DevOps standards for the Stellar Hummingbot connector project.

## CI/CD Pipeline Architecture

### Pipeline Stages
1. **Code Quality** - Linting, formatting, type checking
2. **Security Scanning** - Dependency vulnerabilities, secrets detection
3. **Testing** - Unit, integration, security, performance tests
4. **Build & Package** - Docker images, Python packages
5. **Deploy** - Staging, production deployments
6. **Monitor** - Post-deployment verification

### GitHub Actions Workflow Structure
```yaml
name: CI/CD Pipeline
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  quality:
    name: Code Quality Checks
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: |
            ~/.cache/pip
            ~/.cache/pre-commit
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
      
      - name: Code formatting (black)
        run: black --check --diff .
      
      - name: Import sorting (isort)
        run: isort --check-only --diff .
      
      - name: Linting (flake8)
        run: flake8 .
      
      - name: Type checking (mypy)
        run: mypy hummingbot/connector/exchange/stellar/
```

## Code Quality Standards

### Formatting and Linting Configuration
```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311', 'py312']
include = '\.pyi?$'
extend-exclude = '''
/(
    \.git
  | \.mypy_cache
  | \.venv
  | venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true

[tool.mypy]
python_version = "3.11"
strict = true
disallow_untyped_defs = true
disallow_untyped_decorators = true
disallow_incomplete_defs = true
check_untyped_defs = true
strict_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
```

### Coverage Requirements
```toml
[tool.coverage.run]
source = ["hummingbot/connector/exchange/stellar"]
omit = [
    "*/tests/*",
    "*/venv/*",
    "*/__pycache__/*"
]

[tool.coverage.report]
fail_under = 85
show_missing = true
skip_covered = false
```

## Security Integration

### Dependency Scanning
```yaml
  security:
    name: Security Scanning
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run safety check
        run: |
          pip install safety
          safety check -r requirements.txt
      
      - name: Run bandit security linter
        run: |
          pip install bandit
          bandit -r hummingbot/connector/exchange/stellar/
      
      - name: Scan for secrets
        uses: trufflesecurity/trufflehog@v3.63.2-beta
        with:
          path: ./
          base: main
          head: HEAD
```

### Secret Management
```yaml
  - name: Setup secrets
    env:
      STELLAR_NETWORK_PASSPHRASE: ${{ secrets.STELLAR_NETWORK_PASSPHRASE }}
      STELLAR_HORIZON_URL: ${{ secrets.STELLAR_HORIZON_URL }}
    run: |
      echo "Configuring secure environment..."
      # Never log secret values
```

## Testing Strategy

### Test Categories and Execution
```yaml
  test:
    name: Test Suite
    runs-on: ubuntu-latest
    needs: [quality, security]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Unit Tests
        run: |
          pytest tests/unit/ -v --cov=hummingbot/connector/exchange/stellar \
            --cov-report=xml --cov-report=term-missing --cov-fail-under=85
      
      - name: Integration Tests
        run: |
          pytest tests/integration/ -v --tb=short
        env:
          STELLAR_TEST_NETWORK: true
      
      - name: Security Tests
        run: |
          pytest -m security -v --tb=short
      
      - name: Performance Tests
        run: |
          pytest -m performance -v --tb=short
```

### Test Environment Configuration
```python
# conftest.py
import pytest
import asyncio
from stellar_sdk import Server
from unittest.mock import AsyncMock

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mock_stellar_server():
    """Provide a mocked Stellar server for testing."""
    server = AsyncMock(spec=Server)
    return server
```

## Build and Packaging

### Docker Configuration
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install connector
RUN pip install -e .

# Run tests during build
RUN python -m pytest tests/unit/ --tb=short

EXPOSE 8080
CMD ["python", "-m", "hummingbot.connector.exchange.stellar"]
```

### Multi-stage Build for Production
```dockerfile
# Multi-stage Dockerfile for production
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim as production

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

CMD ["python", "-m", "hummingbot.connector.exchange.stellar"]
```

## Deployment Strategies

### Staging Environment
```yaml
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [test]
    if: github.ref == 'refs/heads/develop'
    
    environment: staging
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            stellar-hummingbot:staging-${{ github.sha }}
            stellar-hummingbot:staging-latest
      
      - name: Deploy to staging
        run: |
          # Kubernetes deployment commands
          kubectl set image deployment/stellar-connector \
            stellar-connector=stellar-hummingbot:staging-${{ github.sha }}
```

### Production Deployment
```yaml
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [test]
    if: github.ref == 'refs/heads/main'
    
    environment: production
    
    steps:
      - name: Deploy with blue-green strategy
        run: |
          # Implement blue-green deployment
          ./scripts/deploy_blue_green.sh
```

## Monitoring and Observability

### Health Check Integration
```python
# health_check.py
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
import asyncio

app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer."""
    try:
        # Check critical dependencies
        await check_stellar_network()
        await check_database()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "healthy", "timestamp": time.time()}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(e)}
        )
```

### Metrics Collection
```yaml
  - name: Collect metrics
    run: |
      # Export performance metrics
      python scripts/export_metrics.py > metrics.json
      
      # Upload to monitoring system
      curl -X POST "$METRICS_ENDPOINT" \
        -H "Authorization: Bearer $METRICS_TOKEN" \
        -d @metrics.json
```

## Release Management

### Semantic Versioning
```yaml
name: Release
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false
```

### Automated Changelog
```yaml
  - name: Generate Changelog
    uses: conventional-changelog/conventional-changelog-action@v3
    with:
      github-token: ${{ secrets.GITHUB_TOKEN }}
      output-file: "CHANGELOG.md"
      release-count: 0
```

## Environment Management

### Configuration Management
```python
# config.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Network configuration
    stellar_network_passphrase: str = "Test SDF Network ; September 2015"
    stellar_horizon_url: str = "https://horizon-testnet.stellar.org"
    
    # Security configuration
    enable_hsm: bool = False
    hsm_config_path: Optional[str] = None
    
    # Performance tuning
    max_concurrent_requests: int = 100
    request_timeout_seconds: int = 30
    
    class Config:
        env_prefix = "STELLAR_"
        case_sensitive = True
```

### Infrastructure as Code
```yaml
# docker-compose.yml
version: '3.8'
services:
  stellar-connector:
    build: .
    ports:
      - "8080:8080"
    environment:
      - STELLAR_NETWORK_PASSPHRASE=${STELLAR_NETWORK_PASSPHRASE}
      - STELLAR_HORIZON_URL=${STELLAR_HORIZON_URL}
    volumes:
      - ./config:/app/config:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

## Performance Optimization

### Build Optimization
```yaml
  - name: Optimize build
    run: |
      # Use build cache
      docker buildx build \
        --cache-from type=gha \
        --cache-to type=gha,mode=max \
        --tag stellar-connector:latest .
```

### Dependency Optimization
```toml
# pyproject.toml optimizations
[build-system]
requires = ["setuptools>=65", "wheel", "setuptools_scm[toml]>=7"]
build-backend = "setuptools.build_meta"

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "black>=23.0",
    "isort>=5.12",
    "flake8>=6.0",
    "mypy>=1.0"
]
```

## Disaster Recovery

### Backup Strategies
```yaml
  backup:
    name: Backup Configuration
    runs-on: ubuntu-latest
    steps:
      - name: Backup to S3
        run: |
          aws s3 sync ./config s3://stellar-connector-backups/config/
          aws s3 sync ./data s3://stellar-connector-backups/data/
```

### Recovery Procedures
```bash
#!/bin/bash
# recovery.sh - Disaster recovery script

set -e

echo "Starting disaster recovery..."

# Restore configuration
aws s3 sync s3://stellar-connector-backups/config/ ./config/

# Restore data
aws s3 sync s3://stellar-connector-backups/data/ ./data/

# Verify integrity
python scripts/verify_integrity.py

echo "Recovery completed successfully"
```

## Compliance and Auditing

### Audit Trail
```yaml
  audit:
    name: Audit Trail
    runs-on: ubuntu-latest
    steps:
      - name: Generate audit report
        run: |
          python scripts/generate_audit_report.py \
            --output audit-report-$(date +%Y%m%d).json
      
      - name: Store audit logs
        run: |
          # Store in secure audit system
          curl -X POST "$AUDIT_ENDPOINT" \
            -H "Authorization: Bearer $AUDIT_TOKEN" \
            -d @audit-report-*.json
```

### Compliance Checks
```python
# compliance_check.py
def check_security_compliance():
    """Verify security compliance requirements."""
    checks = [
        verify_no_hardcoded_secrets(),
        verify_tls_configuration(),
        verify_dependency_versions(),
        verify_access_controls()
    ]
    return all(checks)
```

## DevOps Best Practices Checklist

### CI/CD Pipeline
- [ ] Fast feedback loops (<10 minutes)
- [ ] Automated quality gates
- [ ] Security scanning integration
- [ ] Deployment automation
- [ ] Rollback capabilities

### Monitoring and Alerting
- [ ] Application metrics collection
- [ ] Infrastructure monitoring
- [ ] Log aggregation and analysis
- [ ] Alert escalation procedures
- [ ] SLA monitoring

### Security Integration
- [ ] Secret management
- [ ] Vulnerability scanning
- [ ] Access control enforcement
- [ ] Audit logging
- [ ] Compliance verification

### Operational Excellence
- [ ] Documentation maintenance
- [ ] Runbook procedures
- [ ] Disaster recovery testing
- [ ] Performance optimization
- [ ] Cost optimization

## References
- GitHub Actions Best Practices
- Docker Security Guidelines
- Kubernetes Deployment Patterns
- Python Packaging Standards
- DevOps Security Integration