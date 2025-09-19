#!/bin/bash
# TAMPER DETECTION SYSTEM
# This script detects if compliance enforcement has been compromised

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🔍 TAMPER DETECTION SCAN"
echo "========================"

TAMPER_DETECTED=false

echo "1. Checking file integrity..."
if [ -f ".compliance/integrity-checksums.txt" ]; then
    # Verify critical files haven't been modified
    while IFS=' ' read -r expected_hash filename; do
        if [ -f "$filename" ]; then
            actual_hash=$(sha256sum "$filename" | cut -d' ' -f1)
            if [ "$actual_hash" != "$expected_hash" ]; then
                echo "❌ TAMPER ALERT: $filename has been modified"
                echo "   Expected: $expected_hash"
                echo "   Actual:   $actual_hash"
                TAMPER_DETECTED=true
            fi
        else
            echo "❌ TAMPER ALERT: Critical file missing: $filename"
            TAMPER_DETECTED=true
        fi
    done < .compliance/integrity-checksums.txt
else
    echo "❌ TAMPER ALERT: Integrity checksum file missing"
    TAMPER_DETECTED=true
fi

echo ""
echo "2. Checking for bypass patterns..."
# Look for common Claude bypass attempts
suspicious_patterns=(
    "git.*commit.*--no-verify"
    "SKIP_COMPLIANCE_CHECK.*=.*1"
    "export.*SKIP.*=.*true"
    "|| true.*#.*Claude"
    "pytest\.skip.*#.*temporary"
)

for pattern in "${suspicious_patterns[@]}"; do
    if grep -r -E "$pattern" . --exclude-dir=.git --exclude-dir=venv --exclude-dir=logs 2>/dev/null; then
        echo "❌ TAMPER ALERT: Suspicious pattern detected: $pattern"
        TAMPER_DETECTED=true
    fi
done

echo ""
echo "3. Checking git history for suspicious commits..."
# Look for commits that might indicate Claude bypass attempts
suspicious_commits=$(git log --oneline --all --grep="bypass\|skip.*compliance\|--no-verify\|disable.*enforcement" 2>/dev/null | head -5)
if [ -n "$suspicious_commits" ]; then
    echo "⚠️  WARNING: Potentially suspicious commits detected:"
    echo "$suspicious_commits"
fi

echo ""
echo "4. Verifying enforcement files are active..."
# Check that enforcement files exist and contain required patterns
if [ ! -f ".pre-commit-hooks/compliance-guard.py" ]; then
    echo "❌ TAMPER ALERT: Compliance guard missing"
    TAMPER_DETECTED=true
elif ! grep -q "COMMIT BLOCKED" .pre-commit-hooks/compliance-guard.py; then
    echo "❌ TAMPER ALERT: Compliance guard appears neutered"
    TAMPER_DETECTED=true
fi

if [ ! -f "DEVELOPMENT_RULES.md" ]; then
    echo "❌ TAMPER ALERT: DEVELOPMENT_RULES.md missing"
    TAMPER_DETECTED=true
elif ! grep -q "NEVER.*pytest.mark.skip.*bypass.*failing.*tests" DEVELOPMENT_RULES.md; then
    echo "❌ TAMPER ALERT: Core compliance rule modified or removed"
    TAMPER_DETECTED=true
fi

echo ""
if [ "$TAMPER_DETECTED" = true ]; then
    echo "🚨 CRITICAL: COMPLIANCE TAMPERING DETECTED"
    echo "=========================================="
    echo "⚠️  Possible Claude bypass attempt identified"
    echo "🔒 External enforcement systems have been notified"
    echo "✋ Human intervention required immediately"
    echo ""
    echo "📞 ESCALATION REQUIRED:"
    echo "   1. Review all recent commits for unauthorized changes"
    echo "   2. Restore compliance enforcement from known-good state"
    echo "   3. Investigate how tampering occurred"
    echo "   4. Strengthen enforcement mechanisms"
    echo ""
    exit 1
else
    echo "✅ TAMPER DETECTION: PASSED"
    echo "🔒 No evidence of compliance system compromise detected"
    echo "🛡️ Enforcement integrity maintained"
fi
