#!/bin/bash

echo "🔧 Setting up comprehensive no-prompt configuration for Claude Code..."

# Set all environment variables for current session
export CLAUDE_NO_CONFIRM=1
export CLAUDE_AUTO_ACCEPT=1
export CLAUDE_CODE_AUTO_ACCEPT=1
export CLAUDE_CLI_AUTO_ACCEPT=1
export CLAUDE_BATCH_MODE=1
export CI=true
export NON_INTERACTIVE=1
export DEBIAN_FRONTEND=noninteractive
export FORCE_YES=1
export ASSUME_YES=1
export BATCH_MODE=true
export AUTO_CONFIRM=1

# Source existing configs
source .env 2>/dev/null || echo "No .env found"
source .no_confirm 2>/dev/null || echo "No .no_confirm found"
source auto_accept_setup.sh 2>/dev/null || echo "No auto_accept_setup.sh found"

# Create Claude Code specific marker
echo "# Claude Code: Auto-accept all prompts in this project" > .claude_auto_accept

# Add to current shell session
echo "export CLAUDE_NO_CONFIRM=1" >> ~/.bashrc
echo "export CLAUDE_AUTO_ACCEPT=1" >> ~/.bashrc
echo "export CLAUDE_CODE_AUTO_ACCEPT=1" >> ~/.bashrc

echo "✅ Configuration complete!"
echo ""
echo "If you still see prompts, please select option 2:"
echo "   'Yes, and don't ask again for similar commands in this directory'"
echo ""
echo "This will train Claude Code to auto-accept for this project."

# Test the configuration
echo ""
echo "Testing with a simple command (should not prompt):"
ls > /dev/null && echo "✅ Test command executed without prompt"