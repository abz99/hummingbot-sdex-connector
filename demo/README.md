# QA Monitoring Demo Environment

This demo environment showcases the comprehensive Quality Assurance monitoring capabilities of the Stellar Hummingbot Connector v3.

## 🚀 Quick Start

### Prerequisites

1. **Ensure QA monitoring components are running:**
   ```bash
   # Start Prometheus and Grafana (if not already running)
   docker-compose -f observability/docker-compose.yml up -d
   
   # Verify services
   curl http://localhost:9090/api/v1/query?query=up
   curl http://localhost:3000/api/health
   ```

2. **Install demo dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Demo

#### Full Demo (Recommended)
```bash
python demo/qa_monitoring_demo.py --scenario full
```

#### Specific Scenarios
```bash
# Test coverage monitoring
python demo/qa_monitoring_demo.py --scenario coverage

# Test execution monitoring
python demo/qa_monitoring_demo.py --scenario testing

# Code quality assessment
python demo/qa_monitoring_demo.py --scenario quality

# Compliance tracking
python demo/qa_monitoring_demo.py --scenario compliance

# Alert triggering scenarios
python demo/qa_monitoring_demo.py --scenario alerts
```

#### Verbose Output
```bash
python demo/qa_monitoring_demo.py --scenario full --verbose
```

## 📊 Demo Features

### 1. Coverage Monitoring
- **Simulates**: Test coverage for critical and standard modules
- **Demonstrates**: 
  - Overall coverage calculation (target: ≥80%)
  - Critical module coverage validation (target: ≥90%) 
  - Security module coverage enforcement (target: ≥95%)
  - Compliance rate calculation

### 2. Test Execution Monitoring
- **Simulates**: Various test suite executions
- **Demonstrates**:
  - Test success rate tracking (target: ≥95%)
  - Execution time monitoring (alert: >5 minutes)
  - Test type classification (unit, integration, e2e, security)

### 3. Code Quality Assessment
- **Simulates**: Code quality scoring across components
- **Demonstrates**:
  - Quality score calculation (scale: 0-10, target: ≥7.0)
  - Component-level quality tracking
  - Quality trend analysis

### 4. Compliance Tracking
- **Simulates**: Requirements compliance by category
- **Demonstrates**:
  - Multi-priority compliance tracking
  - Category-based compliance status
  - Compliance percentage calculations

### 5. Defect Monitoring
- **Simulates**: Defect discovery across components
- **Demonstrates**:
  - Severity-based defect classification
  - Component-level defect tracking
  - Defect rate monitoring

### 6. Integration Health
- **Simulates**: QA component operational status
- **Demonstrates**:
  - Component health monitoring
  - Integration status tracking
  - Overall system health calculation

### 7. Alert Scenarios
- **Simulates**: Conditions that trigger monitoring alerts
- **Demonstrates**:
  - Threshold-based alerting
  - Multi-level alert severity
  - Alert condition examples

## 📈 Viewing Results

### Grafana Dashboards
1. **Navigate to**: http://localhost:3000/dashboards
2. **Open**: "Stellar Hummingbot Connector - Production Dashboard"  
3. **Look for QA panels**:
   - QA - Overall Test Coverage
   - QA - Critical Module Coverage  
   - QA - Test Success Rate
   - QA - Code Quality Score
   - QA - Compliance Status
   - QA - Test Execution Time Trend
   - QA - Requirements Coverage Matrix
   - QA - Defect Density Trend
   - QA - Coverage Trend (7 days)

### Prometheus Metrics
1. **Navigate to**: http://localhost:9090
2. **Query examples**:
   ```promql
   # Overall test coverage
   stellar_qa_test_coverage_percentage{coverage_type="overall"}
   
   # Critical module coverage
   stellar_qa_test_coverage_percentage{coverage_type="critical"}
   
   # Test success rates
   stellar_qa_test_success_rate
   
   # Code quality scores
   stellar_qa_code_quality_score
   
   # Compliance status
   stellar_qa_compliance_status
   ```

### Alerts
1. **Navigate to**: http://localhost:9090/alerts
2. **Look for triggered alerts** during demo scenarios:
   - LowOverallTestCoverage
   - CriticalModuleCoverageFailed
   - SecurityModuleCoverageFailed
   - LowTestSuccessRate
   - LowCodeQualityScore

## 🎯 Demo Scenarios Explained

### Coverage Demo
```bash
🎯 Starting Coverage Monitoring Demo
🟢 stellar_security_manager: 96.5% coverage (critical)
🟢 stellar_security: 94.8% coverage (critical)  
🟢 stellar_chain_interface: 91.2% coverage (critical)
🟡 stellar_network_manager: 89.7% coverage (critical)
🟡 stellar_order_manager: 88.3% coverage (critical)
📊 Overall Coverage: 87.4%
🎯 Critical Module Compliance: 60%
```

### Alert Demo
```bash  
🚨 Starting Alerting Demo
🎭 Simulating: Low Security Coverage
⚠️ Would trigger alert: Security module below 95% coverage threshold
🎭 Simulating: Test Failures
⚠️ Would trigger alert: Test success rate below 95% threshold
```

## 🔧 Configuration

### Customizing Thresholds
Edit thresholds in the demo script:
```python
# In qa_monitoring_demo.py
COVERAGE_THRESHOLDS = {
    "overall": 80.0,
    "critical": 90.0, 
    "security": 95.0
}

TEST_SUCCESS_THRESHOLD = 0.95
QUALITY_SCORE_THRESHOLD = 7.0
```

### Adding Custom Scenarios
```python
async def demo_custom_scenario(self):
    """Add your custom demo scenario."""
    # Your demo logic here
    pass
```

## 🛠️ Troubleshooting

### Demo Not Starting
1. **Check dependencies**: `pip list | grep -E "(prometheus|grafana)"`
2. **Verify services**: `docker-compose ps`
3. **Check logs**: `python demo/qa_monitoring_demo.py --verbose`

### Metrics Not Appearing
1. **Verify Prometheus targets**: http://localhost:9090/targets
2. **Check metric names**: http://localhost:9090/api/v1/label/__name__/values
3. **Validate time range** in Grafana (last 5 minutes)

### Grafana Panels Empty
1. **Check data source** configuration
2. **Verify metric queries** in panel settings
3. **Confirm time range** includes demo execution time

## 📚 Next Steps

After running the demo:

1. **Explore Grafana dashboards** to understand metric visualization
2. **Review Prometheus alerts** to understand alerting logic  
3. **Examine demo code** to understand integration patterns
4. **Customize scenarios** for your specific use cases
5. **Integration with CI/CD** using provided automation scripts

## 🎉 Demo Success Criteria

A successful demo shows:

- ✅ **All demo scenarios complete** without errors
- ✅ **Metrics visible** in Prometheus at http://localhost:9090
- ✅ **Dashboards populated** in Grafana at http://localhost:3000
- ✅ **Alerts triggered** during appropriate scenarios
- ✅ **Integration components** showing operational status

This confirms your QA monitoring system is fully functional! 🚀