# Development Rules for Stellar Hummingbot Connector v3

## 🚨 **CRITICAL RULE: NEVER SKIP FAILING TESTS**

### **Absolute Prohibition**
- **NEVER use `pytest.mark.skip` or `pytest.mark.xfail` to bypass failing tests**
- **NEVER commit code with failing tests**
- **NEVER use `--ignore` flags to exclude failing test files**
- **NEVER bypass pre-commit hooks to avoid test failures**

### **Why This Rule Exists**
Failing tests reveal:
1. **Real bugs and design flaws** in the codebase
2. **Missing functionality** that needs implementation
3. **API design issues** that require architectural improvements
4. **Integration problems** between components
5. **Regression issues** from recent changes

### **What to Do When Tests Fail**
1. **INVESTIGATE** the root cause of the failure
2. **FIX** the underlying issue (code bug, missing feature, or test logic)
3. **IMPROVE** the API/architecture if the test reveals design flaws
4. **ENHANCE** test coverage if gaps are discovered
5. **COMMIT** only when ALL tests pass

### **Example: Lesson Learned**
In commit `b0ef38d`, we discovered that `test_end_to_end_key_management` was failing because:
- The `StellarSecurityManager` was missing a `store_keypair()` method
- Only `generate_keypair()` existed, which always created random keys
- The test revealed this API gap and forced us to implement the missing functionality

**Result**: Instead of skipping the test, we added `store_keypair()` and achieved 100% test coverage.

### **Enforcement**
- All commits MUST pass the complete test suite
- Pre-commit hooks will block commits with failing tests
- Code reviews will reject PRs with skipped or ignored tests
- CI/CD pipelines will fail if any tests are skipped without justification

### **The Only Exception**
Tests may only be temporarily marked as skipped if:
1. **External dependency unavailable** (e.g., hardware wallet not connected)
2. **Network service temporarily down** (e.g., testnet maintenance)
3. **Accompanied by a GitHub issue** tracking the temporary skip
4. **Time-boxed resolution plan** (max 1 week)

### **Remember**
> **"A failing test is not a problem to ignore - it's a problem to solve."**
> 
> Failing tests are your codebase telling you something is wrong. Listen to them.

---

## Other Development Rules

### Code Quality
- All code must pass `flake8`, `mypy`, and `black` formatting
- Minimum 90% test coverage for all new code
- Comprehensive error handling and logging
- Type hints required for all functions and methods

### Security
- Never commit secrets, keys, or credentials
- All sensitive operations must use the security infrastructure
- Regular security audits and dependency updates
- Follow principle of least privilege

### Testing
- Write tests FIRST (TDD approach)
- Test both happy path and error scenarios  
- Integration tests for cross-component functionality
- Performance tests for critical paths

### Documentation
- Clear docstrings for all public APIs
- README updates for new features
- Architecture decision records (ADRs) for major changes
- Code comments for complex logic only

### Git Workflow  
- Descriptive commit messages with context
- Small, focused commits that tell a story
- Squash related commits before merging
- Always include co-authorship for AI assistance
- **MANDATORY: Sync with remote on every commit** (`git push origin main` after each successful commit)

---

**This file serves as the authoritative source for development standards.**
**All contributors must follow these rules without exception.**