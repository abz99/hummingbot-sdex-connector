#!/bin/bash
# Script to detect and report failing/skipped tests
# This enforces the "NEVER SKIP FAILING TESTS" rule

set -e

echo "🔍 Checking for failing or skipped tests..."

# Run tests in check mode
echo "Running complete test suite..."
python -m pytest --tb=line --maxfail=1 -v 2>&1 | tee /tmp/test-output.log

# Check for failures
FAILURES=$(grep -c "FAILED" /tmp/test-output.log || true)
SKIPPED=$(grep -c "SKIPPED" /tmp/test-output.log || true) 
XFAIL=$(grep -c "XFAIL" /tmp/test-output.log || true)

echo ""
echo "📊 Test Summary:"
echo "   Failures: $FAILURES"
echo "   Skipped: $SKIPPED" 
echo "   Expected Failures (xfail): $XFAIL"

# Enforce the rule
if [ "$FAILURES" -gt 0 ]; then
    echo ""
    echo "🚨 RULE VIOLATION: FAILING TESTS DETECTED"
    echo ""
    echo "NEVER SKIP FAILING TESTS - FIX THEM!"
    echo ""
    echo "What to do:"
    echo "1. Investigate root cause of failures"
    echo "2. Fix underlying bugs or design issues"
    echo "3. Improve APIs if tests reveal gaps"
    echo "4. Only commit when ALL tests pass"
    echo ""
    echo "See DEVELOPMENT_RULES.md for complete guidelines."
    exit 1
fi

if [ "$XFAIL" -gt 0 ]; then
    echo ""
    echo "⚠️  WARNING: Expected failures (xfail) detected"
    echo "   These should be temporary and have GitHub issues tracking them"
    echo "   Review each xfail to ensure it's justified"
fi

if [ "$SKIPPED" -gt 1 ]; then  # Allow 1 expected skip
    echo ""
    echo "⚠️  WARNING: Multiple skipped tests detected"  
    echo "   Skipped tests should be rare and justified"
    echo "   Each skip should have a GitHub issue and resolution plan"
    echo ""
    echo "Skipped tests found:"
    grep "SKIPPED" /tmp/test-output.log || true
fi

echo ""
echo "✅ Test enforcement check complete!"

# Clean up
rm -f /tmp/test-output.log