#!/bin/bash

# Simple prerequisites test script
echo "🧪 Testing Prerequisites Checker Components"
echo "==========================================="

# Test Python check
echo "Testing Python detection..."
for python_cmd in python3.11 python3 python; do
    if command -v $python_cmd >/dev/null 2>&1; then
        echo "✅ Found $python_cmd: $($python_cmd --version)"
        break
    fi
done

# Test Git check
echo "Testing Git detection..."
if command -v git >/dev/null 2>&1; then
    echo "✅ Found Git: $(git --version)"
else
    echo "❌ Git not found"
fi

# Test disk space
echo "Testing disk space check..."
if command -v df >/dev/null 2>&1; then
    available=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    echo "✅ Available disk space: ${available}GB"
else
    echo "⚠️  Could not check disk space"
fi

# Test network connectivity
echo "Testing network connectivity..."
if curl -s --max-time 5 "https://www.google.com" >/dev/null 2>&1; then
    echo "✅ Internet connectivity OK"
else
    echo "❌ No internet connectivity"
fi

echo "Prerequisites test complete"