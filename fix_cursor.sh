#!/bin/bash

echo "🔧 Fixing cursor visibility in Claude Code terminal..."

# Enable cursor visibility
printf '\033[?25h'     # Show cursor
tput cnorm 2>/dev/null # Normal cursor visibility
printf '\033[0 q'      # Default cursor style
printf '\033[5 q'      # Blinking bar cursor (alternative)

# Set cursor color to white
printf '\033]12;white\007'

# Alternative cursor colors you can try:
# printf '\033]12;red\007'
# printf '\033]12;green\007'
# printf '\033]12;yellow\007'

# Force terminal to refresh
clear

echo "✅ Cursor visibility commands sent"
echo "If cursor is still not visible, try:"
echo "  1. Restart Claude Code terminal"
echo "  2. Check Claude Code settings for cursor options"
echo "  3. Try different terminal themes"

# Test cursor position
echo -n "Type here to test cursor visibility: "
read -t 1 test_input 2>/dev/null || true
echo ""