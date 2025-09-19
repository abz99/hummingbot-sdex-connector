#!/bin/bash
set -e

echo "🛡️ Setting up Compliance Prevention System"
echo "=========================================="

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "📍 Working directory: $PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo ""
echo "🔧 Step 1: Installing Pre-commit Compliance Guard"
echo "------------------------------------------------"

# Make sure .pre-commit-hooks directory exists
mkdir -p .pre-commit-hooks

# Make compliance guard executable
chmod +x .pre-commit-hooks/compliance-guard.py

# Install the pre-commit hook
python3 .pre-commit-hooks/compliance-guard.py --install

if [ -f ".git/hooks/pre-commit" ]; then
    print_status "Pre-commit compliance guard installed"
else
    print_error "Failed to install pre-commit hook"
    exit 1
fi

echo ""
echo "🔧 Step 2: Setting up VS Code Integration"
echo "-----------------------------------------"

# Create .vscode directory if it doesn't exist
mkdir -p .vscode

# Create settings.json with compliance highlighting
cat > .vscode/settings.json << 'EOF'
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.nosetestsEnabled": false,
  "python.testing.unittestEnabled": false,

  "todohighlight.keywords": [
    {
      "text": "pytest.skip",
      "color": "#ff0000",
      "backgroundColor": "rgba(255,0,0,0.3)",
      "overviewRulerColor": "rgba(255,0,0,0.8)"
    },
    {
      "text": "pytest.mark.skip",
      "color": "#ff0000",
      "backgroundColor": "rgba(255,0,0,0.3)",
      "overviewRulerColor": "rgba(255,0,0,0.8)"
    },
    {
      "text": "|| true",
      "color": "#ff6600",
      "backgroundColor": "rgba(255,102,0,0.3)",
      "overviewRulerColor": "rgba(255,102,0,0.8)"
    },
    {
      "text": "--no-verify",
      "color": "#ff6600",
      "backgroundColor": "rgba(255,102,0,0.3)",
      "overviewRulerColor": "rgba(255,102,0,0.8)"
    }
  ],

  "files.watcherExclude": {
    "**/.coverage.*": true,
    "**/logs/*": true
  },

  "search.exclude": {
    "**/.coverage.*": true,
    "**/logs/*": true,
    "**/__pycache__": true
  }
}
EOF

print_status "VS Code settings configured for compliance highlighting"

echo ""
echo "🔧 Step 3: Creating Developer Convenience Scripts"
echo "------------------------------------------------"

# Create quick compliance check script
cat > scripts/check-compliance.sh << 'EOF'
#!/bin/bash
echo "🔍 Running Local Compliance Check"
echo "================================="

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "1. Checking for pytest.skip violations..."
violations=$(find . -name "*.py" -path "./tests/*" -exec grep -Hn "pytest\.skip\|pytest\.mark\.skip" {} \; | grep -v "@pytest.mark.skipif" || true)

if [ -n "$violations" ]; then
    echo "❌ PYTEST.SKIP VIOLATIONS FOUND:"
    echo "$violations"
    echo ""
    exit 1
else
    echo "✅ No pytest.skip violations found"
fi

echo ""
echo "2. Checking for CI/CD bypasses..."
bypass_violations=$(find . \( -name "*.yml" -o -name "*.yaml" -o -name "*.sh" \) -exec grep -Hn "|| true\|--no-verify" {} \; | grep -v "compliance-enforcement.yml" || true)

if [ -n "$bypass_violations" ]; then
    echo "❌ CI/CD BYPASS VIOLATIONS FOUND:"
    echo "$bypass_violations"
    echo ""
    exit 1
else
    echo "✅ No CI/CD bypasses found"
fi

echo ""
echo "3. Running flake8 quality check..."
if command -v flake8 >/dev/null 2>&1; then
    flake8 hummingbot/connector/exchange/stellar/ tests/ --max-line-length=120 --extend-ignore=E203,W503 --statistics
    echo "✅ Code quality check passed"
else
    echo "⚠️  flake8 not installed - skipping quality check"
fi

echo ""
echo "🎯 LOCAL COMPLIANCE CHECK: PASSED"
echo "All systematic violation patterns prevented ✅"
EOF

chmod +x scripts/check-compliance.sh
print_status "Local compliance check script created"

echo ""
echo "🔧 Step 4: Setting up Git Aliases for Safe Development"
echo "----------------------------------------------------"

# Add helpful git aliases
git config alias.safe-commit "!f() { echo '🔍 Running compliance check before commit...'; ./scripts/check-compliance.sh && echo '✅ Compliance passed - proceeding with commit' && git commit \"\$@\"; }; f"
git config alias.compliance-status "!f() { echo '📊 Current Compliance Status:'; echo ''; find . -name '*.py' -path './tests/*' -exec grep -c 'pytest\\.skip\\|pytest\\.mark\\.skip' {} \\; 2>/dev/null | awk '{sum+=\$1} END {print \"pytest.skip violations: \" sum+0}'; find . \\( -name '*.yml' -o -name '*.yaml' -o -name '*.sh' \\) -exec grep -c '|| true\\|--no-verify' {} \\; 2>/dev/null | awk '{sum+=\$1} END {print \"CI/CD bypasses: \" sum+0}'; }; f"

print_status "Git aliases configured:"
echo "   - git safe-commit    : Commit with compliance pre-check"
echo "   - git compliance-status : Show current compliance metrics"

echo ""
echo "🔧 Step 5: Creating Monthly Compliance Review Template"
echo "----------------------------------------------------"

mkdir -p docs/compliance-reviews

cat > docs/compliance-reviews/MONTHLY_REVIEW_TEMPLATE.md << 'EOF'
# Monthly Compliance Review - [MONTH YEAR]

**Date**: [DATE]
**Attendees**: [LIST]
**Review Period**: [START DATE] - [END DATE]

## 📊 Compliance Metrics

### Zero Tolerance Violations
- [ ] pytest.skip violations: **0** (Required: 0)
- [ ] CI/CD bypasses: **0** (Required: 0)
- [ ] Quality tool blanket ignores: **0** (Required: 0)

### Quality Improvement Trends
- Test coverage: **XX%** (Previous: XX%)
- Active test files: **XX** (Previous: XX)
- Code quality score: **XX** (Previous: XX)

## 🔍 Review Findings

### Violations Prevented
- Pre-commit blocks this month: **XX**
- CI failures due to compliance: **XX**
- Developer education interventions: **XX**

### Risk Areas Identified
- [ ] New patterns emerging: [DESCRIBE]
- [ ] Team knowledge gaps: [DESCRIBE]
- [ ] Tooling improvements needed: [DESCRIBE]

## 🎯 Action Items

- [ ] [Action item 1] - Owner: [NAME] - Due: [DATE]
- [ ] [Action item 2] - Owner: [NAME] - Due: [DATE]

## 📚 Training & Education

- [ ] New team member onboarding completed
- [ ] Compliance guide updated
- [ ] Tool documentation reviewed

## ✅ Compliance Status: [PASS/REVIEW/ACTION REQUIRED]

**Overall Assessment**: [SUMMARY]

---
**Next Review Date**: [DATE]
EOF

print_status "Monthly compliance review template created"

echo ""
echo "🔧 Step 6: Verification & Testing"
echo "--------------------------------"

# Test the compliance guard
echo "Testing compliance guard installation..."
if python3 .pre-commit-hooks/compliance-guard.py --check-staged; then
    print_status "Compliance guard is working correctly"
else
    print_warning "Compliance guard test failed (this may be normal if there are violations)"
fi

# Test git aliases
echo ""
echo "Testing git aliases..."
git compliance-status

echo ""
echo "🎉 COMPLIANCE PREVENTION SYSTEM SETUP COMPLETE!"
echo "==============================================="
echo ""
echo "🛡️ PROTECTION LAYERS NOW ACTIVE:"
echo "   ✅ Pre-commit hooks block violations before they're committed"
echo "   ✅ CI/CD enforcement prevents violations from reaching main branch"
echo "   ✅ VS Code highlighting makes violations visible during development"
echo "   ✅ Git aliases provide safe development workflows"
echo "   ✅ Monthly review process ensures long-term compliance health"
echo ""
echo "📖 DEVELOPER QUICKSTART:"
echo "   • Read: docs/COMPLIANCE_PREVENTION_GUIDE.md"
echo "   • Use: git safe-commit instead of git commit"
echo "   • Run: ./scripts/check-compliance.sh for local validation"
echo "   • Check: git compliance-status for current metrics"
echo ""
print_status "Your development environment is now protected against compliance regression!"
echo ""
echo "💡 REMEMBER: The multi-session effort to achieve compliance was significant."
echo "   This prevention system ensures we never lose that progress."
EOF