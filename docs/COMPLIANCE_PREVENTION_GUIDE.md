# 🛡️ Compliance Prevention Guide

**Purpose**: Prevent regression of the systematic compliance violations that were resolved across all 5 categories.

## 🚨 **CRITICAL: The Rules We Must Never Break Again**

### ❌ **NEVER DO THESE THINGS**

1. **❌ pytest.skip / pytest.mark.skip**
   ```python
   # WRONG - This will be blocked by pre-commit hooks
   @pytest.mark.skip(reason="Test is failing")
   pytest.skip("This doesn't work")
   ```

2. **❌ CI/CD Bypasses**
   ```yaml
   # WRONG - This will fail compliance checks
   - run: flake8 . || true
   - run: mypy . || true
   ```
   ```bash
   # WRONG - This bypasses quality controls
   git commit --no-verify
   ```

3. **❌ Quality Tool Ignores Without Specifics**
   ```python
   # WRONG - Blanket ignores are not allowed
   import something  # noqa
   result = func()  # type: ignore
   ```

### ✅ **INSTEAD, DO THIS**

1. **✅ Conditional Testing (When Appropriate)**
   ```python
   # CORRECT - Conditional skipping for external dependencies
   @pytest.mark.skipif(not TESTNET_ENABLED, reason="Requires STELLAR_TESTNET_ENABLED=true")
   @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
   ```

2. **✅ Fix Underlying Issues**
   ```python
   # CORRECT - Fix the test instead of skipping
   def test_api_call(self, mock_client):
       # Use proper mocking and async handling
       with patch("module.api_call") as mock_call:
           mock_call.return_value = {"status": "success"}
           result = await service.api_call()
           assert result is not None
   ```

3. **✅ Specific Quality Ignores (When Justified)**
   ```python
   # CORRECT - Specific codes with justification
   import legacy_module  # noqa: F401  # Used in dynamic import
   result = cast(str, value)  # type: ignore[arg-type]  # Legacy compatibility
   ```

## 🛠️ **Developer Tooling**

### **1. Pre-commit Hook Installation**
```bash
# Install the compliance guard (run once per developer)
python .pre-commit-hooks/compliance-guard.py --install

# Verify installation
ls -la .git/hooks/pre-commit
```

### **2. Local Compliance Check**
```bash
# Check current working directory for violations
python .pre-commit-hooks/compliance-guard.py --check-staged

# Full project scan
find . -name "*.py" -path "./tests/*" -exec grep -Hn "pytest\.skip" {} \;
```

### **3. IDE Integration**

#### **VS Code Settings** (.vscode/settings.json)
```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "files.associations": {
    "*.py": "python"
  },
  "python.testing.pytestEnabled": true,
  "python.testing.nosetestsEnabled": false,
  "python.testing.unittestEnabled": false,

  // Highlight compliance violations
  "search.exclude": {},
  "todohighlight.keywords": [
    {
      "text": "pytest.skip",
      "color": "red",
      "backgroundColor": "rgba(255,0,0,0.3)"
    },
    {
      "text": "|| true",
      "color": "red",
      "backgroundColor": "rgba(255,0,0,0.3)"
    }
  ]
}
```

## 🧪 **Testing Best Practices**

### **When Tests Fail - The Right Approach**

#### ❌ **Wrong Response**
```python
@pytest.mark.skip(reason="This test is failing")
def test_complex_feature():
    # Complex test that's broken
    pass
```

#### ✅ **Right Response**
```python
@pytest.mark.asyncio
async def test_complex_feature(mock_dependencies):
    """Test complex feature with proper infrastructure.

    QA_ID: REQ-XXX-001
    Acceptance Criteria: Feature works correctly with mocked dependencies
    """
    # 1. Analyze WHY the test was failing
    # 2. Create proper test doubles/mocks
    # 3. Fix the underlying API usage
    # 4. Ensure proper async/sync handling

    with patch("module.external_service") as mock_service:
        mock_service.return_value = expected_response

        result = await service.complex_feature()

        assert result is not None
        assert result.status == "success"
        mock_service.assert_called_once()
```

### **Common Test Fixing Patterns**

1. **API Signature Mismatches**
   ```python
   # Common issue: Wrong parameters
   # FIX: Check actual implementation for correct signature
   result = await health_monitor.check_health(endpoint, session)  # Correct
   # Not: result = await health_monitor.check_health()  # Wrong
   ```

2. **Missing Imports**
   ```python
   # FIX: Add proper imports at test method level or file level
   from hummingbot.connector.exchange.stellar.stellar_metrics import MetricDefinition, MetricType
   ```

3. **Async/Sync Mismatches**
   ```python
   # FIX: Make test function async if calling async methods
   @pytest.mark.asyncio
   async def test_async_operation(self, service):
       result = await service.async_method()  # Correct
   ```

## 📊 **Monitoring & Alerts**

### **Daily Compliance Dashboard**
- **GitHub Actions**: Automated daily compliance audit at 2 AM UTC
- **Metrics Collection**: Tracks violation counts over time
- **Trend Analysis**: Identifies if violations are creeping back in

### **Violation Alerts**
- **Pre-commit Blocks**: Immediate feedback when violations are attempted
- **PR Comments**: Compliance status reported on all pull requests
- **CI Failures**: Pipeline fails fast when violations are detected

### **Monthly Compliance Review**
Create monthly compliance review meetings:
1. Review compliance metrics trends
2. Assess if new violation patterns are emerging
3. Update prevention tools if needed
4. Training for new team members

## 🎯 **Success Metrics**

### **Zero Tolerance Metrics**
- **pytest.skip violations**: Must remain at 0
- **CI/CD bypasses**: Must remain at 0
- **Quality tool blanket ignores**: Must remain at 0

### **Quality Improvement Metrics**
- **Test coverage**: Should trend upward
- **Code quality scores**: Should maintain or improve
- **Security scan results**: Should remain clean

## 🆘 **When You Need Help**

### **Multi-Agent Team Support**
If you encounter a situation where you're tempted to bypass compliance:

1. **Engage ProjectManager**: For workflow coordination and systematic approaches
2. **Engage QAEngineer**: For test strategy and infrastructure improvements
3. **Engage SecurityEngineer**: For security-related test challenges
4. **Engage Implementer**: For complex API integration issues

### **Escalation Process**
1. **Never bypass first** - Try to fix the underlying issue
2. **Document the problem** - Explain what's blocking you
3. **Request help** - Use the multi-agent team for systematic solutions
4. **Create temporary issues** - If external dependencies are truly unavailable
5. **Set time-boxed resolution** - Max 1 week for legitimate external issues

## 📖 **Reference Documentation**

- **DEVELOPMENT_RULES.md**: The authoritative source for all rules
- **COMPLIANCE_VIOLATIONS_REPORT.md**: Historical context and lessons learned
- **PROJECT_STATUS.md**: Current project compliance state

---

**Remember**: Every violation we prevented from regressing represents production bugs avoided, security vulnerabilities blocked, and development velocity maintained. The multi-session effort to achieve compliance was significant - let's never lose that progress!