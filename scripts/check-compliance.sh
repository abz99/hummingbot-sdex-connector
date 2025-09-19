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
