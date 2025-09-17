#!/bin/bash
# CI Push Wrapper - Automated CI verification after push
# Usage: ./scripts/ci-push-wrapper.sh [branch] [optional-message]

set -e

BRANCH="${1:-main}"
COMMIT_MESSAGE="${2:-Automated push with CI verification}"

echo "🚀 CI Push Wrapper - Automated verification enabled"
echo "📍 Target branch: $BRANCH"

# Ensure we're on correct branch
if [[ "$(git branch --show-current)" != "$BRANCH" ]]; then
    echo "⚠️ Current branch is not $BRANCH, switching..."
    git checkout "$BRANCH"
fi

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "📝 Uncommitted changes detected, committing..."
    git add .
    git commit -m "$COMMIT_MESSAGE"
fi

# Get commit SHA before push
COMMIT_SHA=$(git rev-parse HEAD)
echo "📍 Commit SHA: $COMMIT_SHA"

# Push to remote
echo "📤 Pushing to origin/$BRANCH..."
git push origin "$BRANCH"

# Wait for push to be processed
echo "⏳ Waiting for GitHub to process push..."
sleep 15

# Run automated CI health verification
echo "🔍 Starting automated CI health verification..."

# Set GitHub token from environment or prompt
if [[ -z "$GITHUB_TOKEN" ]]; then
    echo "⚠️ GITHUB_TOKEN not set in environment"
    echo "💡 For full functionality, set: export GITHUB_TOKEN=your_token"
fi

# Run post-push monitoring
MONITORING_RESULT=0
python .github/post-push-ci-monitor.py --commit "$COMMIT_SHA" --save-results || MONITORING_RESULT=$?

if [[ $MONITORING_RESULT -eq 0 ]]; then
    echo ""
    echo "✅ SUCCESS: Push completed with healthy CI pipeline"
    echo "📊 All workflows completed successfully"
    echo "🔗 View results: https://github.com/abz99/stellar-hummingbot-connector-v3/actions"
else
    echo ""
    echo "⚠️ WARNING: CI pipeline issues detected"
    echo "🔍 Check GitHub Actions for details"
    echo "🔗 View results: https://github.com/abz99/stellar-hummingbot-connector-v3/actions"
    echo ""
    echo "💡 Common fixes:"
    echo "   - Review failed workflow logs"
    echo "   - Check if all required secrets are configured"
    echo "   - Verify dependencies in requirements-dev.txt"
    echo "   - Run local tests: pytest tests/ -v"
fi

echo ""
echo "📁 Monitoring results saved to logs/ directory"
echo "✅ CI Push Wrapper completed"