#!/bin/bash

# Stellar Hummingbot Connector v3.0 - Automated Installation Script
# This script provides one-click installation for the Stellar Hummingbot Connector

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/stellar/hummingbot-connector-v3.git"
PYTHON_MIN_VERSION="3.11"
INSTALL_DIR="$HOME/stellar-hummingbot-connector-v3"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare version numbers
version_compare() {
    if [[ $1 == $2 ]]; then
        return 0
    fi
    local IFS=.
    local i ver1=($1) ver2=($2)
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++)); do
        ver1[i]=0
    done
    for ((i=0; i<${#ver1[@]}; i++)); do
        if [[ -z ${ver2[i]} ]]; then
            ver2[i]=0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]})); then
            return 1
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]})); then
            return 2
        fi
    done
    return 0
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt; then
            echo "ubuntu"
        elif command_exists yum; then
            echo "centos"
        elif command_exists dnf; then
            echo "fedora"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to install Python on different systems
install_python() {
    local os=$(detect_os)

    print_status "Installing Python $PYTHON_MIN_VERSION..."

    case $os in
        "ubuntu")
            sudo apt update
            sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
            ;;
        "centos")
            sudo yum install -y python311 python311-pip python311-devel
            ;;
        "fedora")
            sudo dnf install -y python3.11 python3-pip python3-devel
            ;;
        "macos")
            if command_exists brew; then
                brew install python@3.11
            else
                print_error "Homebrew not found. Please install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;
        *)
            print_error "Automatic Python installation not supported for your OS. Please install Python $PYTHON_MIN_VERSION manually."
            exit 1
            ;;
    esac
}

# Function to check Python version
check_python() {
    print_status "Checking Python installation..."

    # Try different Python commands
    for python_cmd in python3.11 python3 python; do
        if command_exists $python_cmd; then
            local python_version=$($python_cmd --version 2>&1 | cut -d' ' -f2)
            version_compare $python_version $PYTHON_MIN_VERSION
            local result=$?

            if [[ $result -eq 1 ]] || [[ $result -eq 0 ]]; then
                export PYTHON_CMD=$python_cmd
                print_success "Found Python $python_version at $(which $python_cmd)"
                return 0
            fi
        fi
    done

    print_warning "Python $PYTHON_MIN_VERSION or higher not found."
    read -p "Would you like to install Python $PYTHON_MIN_VERSION? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_python
        check_python  # Recursive call to re-check after installation
    else
        print_error "Python $PYTHON_MIN_VERSION or higher is required. Installation aborted."
        exit 1
    fi
}

# Function to install Git if not present
install_git() {
    local os=$(detect_os)

    print_status "Installing Git..."

    case $os in
        "ubuntu")
            sudo apt update && sudo apt install -y git
            ;;
        "centos")
            sudo yum install -y git
            ;;
        "fedora")
            sudo dnf install -y git
            ;;
        "macos")
            if command_exists brew; then
                brew install git
            else
                print_error "Please install Git manually from https://git-scm.com/"
                exit 1
            fi
            ;;
        *)
            print_error "Please install Git manually for your operating system."
            exit 1
            ;;
    esac
}

# Function to check Git
check_git() {
    print_status "Checking Git installation..."

    if command_exists git; then
        print_success "Git found at $(which git)"
    else
        print_warning "Git not found."
        read -p "Would you like to install Git? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_git
        else
            print_error "Git is required. Installation aborted."
            exit 1
        fi
    fi
}

# Function to check available disk space
check_disk_space() {
    print_status "Checking available disk space..."

    local available_space
    if command_exists df; then
        available_space=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
        if [[ $available_space -lt 10 ]]; then
            print_warning "Only ${available_space}GB available. At least 10GB recommended."
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        else
            print_success "Sufficient disk space available (${available_space}GB)"
        fi
    else
        print_warning "Could not check disk space. Proceeding..."
    fi
}

# Function to clone repository
clone_repository() {
    print_status "Cloning repository..."

    if [[ -d "$INSTALL_DIR" ]]; then
        print_warning "Directory $INSTALL_DIR already exists."
        read -p "Remove existing directory and reinstall? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            print_error "Installation aborted."
            exit 1
        fi
    fi

    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    print_success "Repository cloned to $INSTALL_DIR"
}

# Function to create virtual environment
create_venv() {
    print_status "Creating virtual environment..."

    $PYTHON_CMD -m venv venv

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    print_success "Virtual environment created and activated"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."

    # Ensure we're in the virtual environment
    source venv/bin/activate

    # Install core dependencies
    pip install -r requirements.txt

    # Install development dependencies if available
    if [[ -f requirements-dev.txt ]]; then
        pip install -r requirements-dev.txt
    fi

    # Install AI/ML dependencies for Phase 6
    pip install pandas numpy scikit-learn

    print_success "Dependencies installed successfully"
}

# Function to run basic tests
run_basic_tests() {
    print_status "Running basic functionality tests..."

    # Ensure we're in the virtual environment
    source venv/bin/activate

    # Test Python imports
    python -c "
import sys
try:
    from hummingbot.connector.exchange.stellar import StellarExchange
    print('✅ Core imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

    # Run a simple test if pytest is available
    if command_exists pytest && [[ -d tests/ ]]; then
        print_status "Running unit tests..."
        pytest tests/unit/test_stellar_exchange_contract.py::TestStellarExchangeInitialization::test_exchange_initialization_success -v || true
    fi

    print_success "Basic tests completed"
}

# Function to create basic configuration
create_config() {
    print_status "Creating basic configuration..."

    # Create config directory if it doesn't exist
    mkdir -p config

    # Create basic environment file
    cat > .env << EOF
# Stellar Hummingbot Connector v3.0 Configuration
# Generated by automated installer on $(date)

# Network Configuration (testnet by default for safety)
STELLAR_NETWORK_PASSPHRASE="Test SDF Network ; September 2015"
SOROBAN_RPC_URL="https://soroban-testnet.stellar.org"
HORIZON_URL="https://horizon-testnet.stellar.org"

# Security Configuration
STELLAR_SECRET_KEY=""  # Leave empty for test accounts
STELLAR_PUBLIC_KEY=""  # Leave empty for test accounts

# AI Trading Configuration
AI_TRADING_ENABLED=true
AI_MODEL_PATH="./ai_models/"
AI_DATA_PIPELINE_ENABLED=true

# Logging Configuration
LOG_LEVEL="INFO"
LOG_FILE="./logs/stellar-connector.log"

# Performance Configuration
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
CONNECTION_POOL_SIZE=20
EOF

    # Create logs directory
    mkdir -p logs

    print_success "Basic configuration created"
}

# Function to test network connectivity
test_connectivity() {
    print_status "Testing network connectivity..."

    # Test Stellar Testnet
    if curl -s --max-time 10 "https://horizon-testnet.stellar.org/" > /dev/null; then
        print_success "Stellar Testnet connectivity: OK"
    else
        print_warning "Stellar Testnet connectivity: FAILED"
    fi

    # Test Soroban RPC
    if curl -s --max-time 10 "https://soroban-testnet.stellar.org/health" > /dev/null; then
        print_success "Soroban RPC connectivity: OK"
    else
        print_warning "Soroban RPC connectivity: FAILED"
    fi
}

# Function to create quick start script
create_quick_start() {
    print_status "Creating quick start script..."

    cat > quick_start.py << 'EOF'
#!/usr/bin/env python3
"""
Stellar Hummingbot Connector v3.0 - Quick Start Example
This script demonstrates basic functionality of the connector.
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def quick_start_demo():
    """Demonstrate basic connector functionality."""
    print("🚀 Stellar Hummingbot Connector v3.0 - Quick Start")
    print("=" * 50)

    try:
        # Import the connector
        from hummingbot.connector.exchange.stellar import StellarExchange

        print("✅ Successfully imported StellarExchange")

        # Initialize the connector (testnet by default)
        print("🔧 Initializing connector...")
        exchange = StellarExchange(
            trading_pairs=["XLM-USDC"],
            network="testnet"
        )

        print("✅ Connector initialized successfully")
        print(f"📊 Trading pairs: {exchange.trading_pairs}")
        print(f"🌐 Network: testnet")

        # Test AI system if available
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

            from ai_trading.data_pipeline import TradingDataPipeline

            print("🧠 AI Trading System Available")
            pipeline = TradingDataPipeline()
            print(f"📈 Data sources: {pipeline.get_pipeline_status()['active_sources']}")

        except ImportError:
            print("ℹ️  AI Trading System not fully configured (optional)")

        print("\n🎉 Quick start completed successfully!")
        print("\nNext steps:")
        print("1. Review the configuration in .env file")
        print("2. Explore examples/ directory for more advanced usage")
        print("3. Read OPERATIONS_MANUAL.md for production deployment")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please check your installation and ensure all dependencies are installed.")
        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(quick_start_demo())
    exit(0 if success else 1)
EOF

    chmod +x quick_start.py
    print_success "Quick start script created"
}

# Function to display completion message
display_completion() {
    print_success "Installation completed successfully! 🎉"
    echo
    echo "🔧 Installation Summary:"
    echo "  📁 Installation directory: $INSTALL_DIR"
    echo "  🐍 Python version: $($PYTHON_CMD --version)"
    echo "  📦 Virtual environment: $INSTALL_DIR/venv"
    echo "  ⚙️  Configuration file: $INSTALL_DIR/.env"
    echo
    echo "🚀 Next steps:"
    echo "  1. cd $INSTALL_DIR"
    echo "  2. source venv/bin/activate"
    echo "  3. python quick_start.py"
    echo
    echo "📚 Documentation:"
    echo "  📖 User Guide: README.md"
    echo "  🔧 Configuration: CONFIGURATION.md"
    echo "  🏭 Operations: OPERATIONS_MANUAL.md"
    echo "  🆘 Troubleshooting: Check INSTALL.md for common issues"
    echo
    echo "💬 Support:"
    echo "  🌐 GitHub: https://github.com/stellar/hummingbot-connector-v3"
    echo "  💬 Discord: https://discord.gg/stellar"
    echo "  📧 Email: support@stellar.org"
    echo
    print_success "Happy trading with Stellar! 🌟"
}

# Main installation function
main() {
    echo "🌟 Stellar Hummingbot Connector v3.0 Installer"
    echo "=============================================="
    echo

    # Check prerequisites
    check_python
    check_git
    check_disk_space

    # Clone repository
    clone_repository

    # Set up environment
    create_venv
    install_dependencies

    # Configuration and testing
    create_config
    test_connectivity
    run_basic_tests
    create_quick_start

    # Completion
    display_completion
}

# Handle script interruption
trap 'print_error "Installation interrupted. Cleaning up..."; exit 1' INT TERM

# Run main installation
main "$@"