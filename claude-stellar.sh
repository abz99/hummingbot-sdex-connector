#!/bin/bash
# corrected-claude-stellar.sh - Fixed Claude Code wrapper for Stellar SDEX development

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Ensure virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✓ Activated virtual environment"
    else
        echo "⚠️  Virtual environment not found. Please run: python -m venv venv && source venv/bin/activate"
        exit 1
    fi
fi

# Check if Claude Code is available
if ! command -v claude-code &> /dev/null; then
    echo "❌ Claude Code not found. Please install it first:"
    echo "   npm install -g @anthropic-ai/claude-code"
    echo "   claude-code auth"
    exit 1
fi

# Check Claude Code authentication
if ! claude-code whoami &>/dev/null; then
    echo "❌ Claude Code not authenticated. Please run:"
    echo "   claude-code auth"
    exit 1
fi

# Function to run Claude Code with enhanced context
run_claude_with_context() {
    local command="$1"
    shift
    
    # Set environment context for Claude
    export CLAUDE_CONTEXT="Stellar SDEX Connector Development - Python 3.11+, Hummingbot integration, asyncio patterns"
    export CLAUDE_PROJECT="stellar-blockchain-connector"
    export CLAUDE_FRAMEWORK="hummingbot-stellar-sdk"
    
    # Add project context to commands
    case "$command" in
        "ask")
            local question="$1"
            # Add context to questions
            claude-code ask "Context: I'm developing a Stellar SDEX connector for Hummingbot using Python 3.11+ and Stellar SDK v8.x. Question: $question"
            ;;
        *)
            claude-code "$command" "$@"
            ;;
    esac
}

# Enhanced commands for Stellar development
case "$1" in
    "stellar-init")
        echo "🚀 Initializing Stellar SDEX project with Claude Code..."
        
        # Create project structure first
        echo "📁 Creating project structure..."
        mkdir -p src/stellar_connector/{core,exchange,utils}
        mkdir -p test/{unit,integration,performance}
        mkdir -p config docs
        
        # Initialize with Claude (using correct command)
        echo "🤖 Getting Claude's help with project initialization..."
        run_claude_with_context ask "I'm starting the PROJECT_INIT_001 task for implementing a Stellar SDEX connector for Hummingbot. Help me create the initial ModernStellarChainInterface class with Python 3.11+ and Stellar SDK v8.x. What should be the first implementation steps?"
        ;;
        
    "stellar-ask")
        shift
        question="$*"
        if [ -z "$question" ]; then
            read -p "Ask Claude about Stellar development: " question
        fi
        run_claude_with_context ask "$question"
        ;;
        
    "stellar-review")
        file="${2:-$(find . -name '*.py' -type f | head -1)}"
        if [ -f "$file" ]; then
            echo "🔍 Getting Claude's review of $file..."
            run_claude_with_context ask "Please review this Stellar SDEX connector code for best practices, asyncio patterns, Stellar SDK v8.x usage, and Hummingbot integration compliance. File: $file

$(cat "$file")"
        else
            echo "❌ File not found: $file"
            exit 1
        fi
        ;;
        
    "stellar-edit")
        file="${2:-$(find . -name '*.py' -type f | head -1)}"
        instruction="${3:-}"
        
        if [ ! -f "$file" ]; then
            echo "❌ File not found: $file"
            exit 1
        fi
        
        if [ -z "$instruction" ]; then
            read -p "Edit instruction for $file: " instruction
        fi
        
        echo "✏️  Getting Claude's help editing $file..."
        run_claude_with_context ask "Please help me edit this Stellar SDEX connector file according to this instruction: '$instruction'

Current code in $file:
$(cat "$file")

Please provide the improved code following Stellar SDK v8.x best practices and modern Python asyncio patterns."
        ;;
        
    "stellar-test")
        echo "🧪 Getting Claude's help with testing..."
        run_claude_with_context ask "Help me implement comprehensive tests for the Stellar SDEX connector. Current project structure:

$(find . -name '*.py' -type f | head -10)

Please suggest test implementation for pytest with asyncio support, focusing on Stellar SDK operations and Hummingbot integration patterns."
        ;;
        
    "stellar-optimize")
        file="${2:-$(find . -name '*.py' -type f | head -1)}"
        if [ -f "$file" ]; then
            echo "⚡ Getting optimization suggestions for $file..."
            run_claude_with_context ask "Please optimize this Stellar SDEX connector code for performance, focusing on asyncio patterns, connection pooling, and Stellar SDK v8.x best practices:

$(cat "$file")"
        else
            echo "❌ File not found: $file"
        fi
        ;;
        
    "stellar-debug")
        file="${2:-$(find . -name '*.py' -type f | head -1)}"
        if [ -f "$file" ]; then
            echo "🐛 Getting debugging help for $file..."
            run_claude_with_context ask "Help me debug this Stellar SDEX connector code. Look for potential issues with async patterns, Stellar SDK usage, error handling, and Hummingbot integration:

$(cat "$file")"
        else
            echo "❌ File not found: $file"
        fi
        ;;
        
    "stellar-implement")
        task="${2:-}"
        if [ -z "$task" ]; then
            echo "Available tasks:"
            echo "  STELLAR_CHAIN_001 - Modern Stellar Chain Interface"
            echo "  SECURITY_001 - Enterprise Security Framework"
            echo "  ORDER_MANAGER_001 - Advanced Order Management"
            echo "  ASSET_MANAGER_001 - Modern Asset Management"
            echo "  SOROBAN_001 - Smart Contract Manager"
            read -p "Which task would you like help implementing? " task
        fi
        
        echo "🚀 Getting implementation help for $task..."
        run_claude_with_context ask "Help me implement the $task from the Stellar SDEX connector implementation checklist. Provide detailed Python code using Stellar SDK v8.x, modern asyncio patterns, and Hummingbot integration best practices. Current project structure:

$(find . -maxdepth 3 -type f -name '*.py' 2>/dev/null | head -10)"
        ;;
        
    "stellar-status")
        echo "📊 Getting project status analysis..."
        echo ""
        echo "📁 Current project structure:"
        find . -name '*.py' -type f | head -10
        echo ""
        echo "📦 Python environment:"
        python -c "
import sys
print(f'Python: {sys.version}')
try:
    import stellar_sdk
    print(f'Stellar SDK: {stellar_sdk.__version__}')
except ImportError:
    print('Stellar SDK: Not installed')
"
        echo ""
        run_claude_with_context ask "Analyze the current state of my Stellar SDEX connector project and suggest next implementation steps. Here's the current structure:

Project Files:
$(find . -name '*.py' -type f | head -10)

Please suggest what to implement next and any potential issues."
        ;;
        
    *)
        echo "🌟 Stellar SDEX Development Helper"
        echo "=================================="
        echo ""
        echo "Usage: $0 {command} [arguments]"
        echo ""
        echo "Available commands:"
        echo "  stellar-init         - Initialize project with Claude's help"
        echo "  stellar-ask [quest]  - Ask Claude development questions"
        echo "  stellar-review [file] - Get Claude's code review"
        echo "  stellar-edit [file] [instruction] - Edit code with Claude"
        echo "  stellar-test         - Get testing implementation help"
        echo "  stellar-optimize [file] - Get performance optimization help"
        echo "  stellar-debug [file] - Get debugging assistance"
        echo "  stellar-implement [task] - Get task implementation help"
        echo "  stellar-status       - Analyze project status"
        echo ""
        echo "Examples:"
        echo "  $0 stellar-ask 'How do I handle Stellar sequence numbers?'"
        echo "  $0 stellar-review src/stellar_connector/chain_interface.py"
        echo "  $0 stellar-implement STELLAR_CHAIN_001"
        echo "  $0 stellar-status"
        echo ""
        echo "💡 Tip: Run commands from your project root directory"
        exit 1
        ;;
esac
