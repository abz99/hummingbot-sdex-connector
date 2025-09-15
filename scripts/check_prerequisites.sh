#!/bin/bash

# Stellar Hummingbot Connector v3.0 - Prerequisites Checker
# This script checks system prerequisites before installation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Requirements
PYTHON_MIN_VERSION="3.11"
PYTHON_RECOMMENDED_VERSION="3.11"
MIN_DISK_SPACE_GB=10
RECOMMENDED_DISK_SPACE_GB=20
MIN_MEMORY_GB=4
RECOMMENDED_MEMORY_GB=8

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to print colored output
print_check() {
    local status=$1
    local message=$2
    case $status in
        "PASS")
            echo "✅ PASS - $message"
            ((PASSED++))
            ;;
        "FAIL")
            echo "❌ FAIL - $message"
            ((FAILED++))
            ;;
        "WARN")
            echo "⚠️  WARN - $message"
            ((WARNINGS++))
            ;;
        "INFO")
            echo "ℹ️  INFO - $message"
            ;;
    esac
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

# Function to get human readable size
human_readable_size() {
    local bytes=$1
    local sizes=("B" "KB" "MB" "GB" "TB")
    local i=0
    while (( bytes > 1024 && i < ${#sizes[@]}-1 )); do
        bytes=$((bytes / 1024))
        ((i++))
    done
    echo "${bytes}${sizes[i]}"
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists lsb_release; then
            echo "$(lsb_release -si) $(lsb_release -sr)"
        elif [[ -f /etc/os-release ]]; then
            echo "$(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)"
        else
            echo "Linux (unknown distribution)"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macOS $(sw_vers -productVersion)"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]]; then
        echo "Windows (Cygwin/MSYS)"
    else
        echo "Unknown OS: $OSTYPE"
    fi
}

# Check operating system
check_operating_system() {
    echo "🖥️  Operating System Check"
    echo "=========================="

    local os_info=$(detect_os)
    print_check "INFO" "Operating System: $os_info"

    # Check if OS is supported
    if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
        print_check "PASS" "Operating system is supported"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]]; then
        print_check "WARN" "Windows detected - installation may require additional steps"
    else
        print_check "FAIL" "Unsupported operating system"
    fi

    echo
}

# Check Python installation
check_python() {
    echo "🐍 Python Check"
    echo "==============="

    local python_found=false
    local python_cmd=""
    local python_version=""

    # Try different Python commands
    for cmd in python3.11 python3 python; do
        if command_exists $cmd; then
            python_version=$($cmd --version 2>&1 | cut -d' ' -f2)
            version_compare $python_version $PYTHON_MIN_VERSION
            local result=$?

            if [[ $result -eq 1 ]] || [[ $result -eq 0 ]]; then
                python_found=true
                python_cmd=$cmd
                break
            fi
        fi
    done

    if $python_found; then
        print_check "PASS" "Python $python_version found at $(which $python_cmd)"

        version_compare $python_version $PYTHON_RECOMMENDED_VERSION
        local result=$?
        if [[ $result -eq 1 ]] || [[ $result -eq 0 ]]; then
            print_check "PASS" "Python version meets recommended requirements"
        else
            print_check "WARN" "Python $PYTHON_RECOMMENDED_VERSION or higher recommended"
        fi

        # Check if python-venv is available
        if $python_cmd -m venv --help >/dev/null 2>&1; then
            print_check "PASS" "Python venv module available"
        else
            print_check "FAIL" "Python venv module not available - install python3-venv package"
        fi

        # Check if pip is available
        if $python_cmd -m pip --version >/dev/null 2>&1; then
            local pip_version=$($python_cmd -m pip --version | cut -d' ' -f2)
            print_check "PASS" "pip $pip_version available"
        else
            print_check "FAIL" "pip not available"
        fi

    else
        print_check "FAIL" "Python $PYTHON_MIN_VERSION or higher not found"
        echo "       Install Python from: https://www.python.org/downloads/"
    fi

    echo
}

# Check Git installation
check_git() {
    echo "📁 Git Check"
    echo "============"

    if command_exists git; then
        local git_version=$(git --version | cut -d' ' -f3)
        print_check "PASS" "Git $git_version found at $(which git)"

        # Check git configuration
        if git config user.name >/dev/null 2>&1 && git config user.email >/dev/null 2>&1; then
            print_check "PASS" "Git user configuration present"
        else
            print_check "WARN" "Git user not configured - run 'git config --global user.name' and 'git config --global user.email'"
        fi
    else
        print_check "FAIL" "Git not found - install from https://git-scm.com/"
    fi

    echo
}

# Check system resources
check_system_resources() {
    echo "💻 System Resources Check"
    echo "========================="

    # Check available memory
    if command_exists free; then
        local total_memory_kb=$(free -k | awk '/^Mem:/ {print $2}')
        local total_memory_gb=$((total_memory_kb / 1024 / 1024))

        if [[ $total_memory_gb -ge $RECOMMENDED_MEMORY_GB ]]; then
            print_check "PASS" "System memory: ${total_memory_gb}GB (recommended: ${RECOMMENDED_MEMORY_GB}GB+)"
        elif [[ $total_memory_gb -ge $MIN_MEMORY_GB ]]; then
            print_check "WARN" "System memory: ${total_memory_gb}GB (minimum: ${MIN_MEMORY_GB}GB, recommended: ${RECOMMENDED_MEMORY_GB}GB)"
        else
            print_check "FAIL" "System memory: ${total_memory_gb}GB (minimum ${MIN_MEMORY_GB}GB required)"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        local total_memory_bytes=$(sysctl -n hw.memsize)
        local total_memory_gb=$((total_memory_bytes / 1024 / 1024 / 1024))

        if [[ $total_memory_gb -ge $RECOMMENDED_MEMORY_GB ]]; then
            print_check "PASS" "System memory: ${total_memory_gb}GB (recommended: ${RECOMMENDED_MEMORY_GB}GB+)"
        elif [[ $total_memory_gb -ge $MIN_MEMORY_GB ]]; then
            print_check "WARN" "System memory: ${total_memory_gb}GB (minimum: ${MIN_MEMORY_GB}GB, recommended: ${RECOMMENDED_MEMORY_GB}GB)"
        else
            print_check "FAIL" "System memory: ${total_memory_gb}GB (minimum ${MIN_MEMORY_GB}GB required)"
        fi
    else
        print_check "INFO" "Could not check system memory"
    fi

    # Check available disk space
    if command_exists df; then
        local available_space_gb=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')

        if [[ $available_space_gb -ge $RECOMMENDED_DISK_SPACE_GB ]]; then
            print_check "PASS" "Available disk space: ${available_space_gb}GB (recommended: ${RECOMMENDED_DISK_SPACE_GB}GB+)"
        elif [[ $available_space_gb -ge $MIN_DISK_SPACE_GB ]]; then
            print_check "WARN" "Available disk space: ${available_space_gb}GB (minimum: ${MIN_DISK_SPACE_GB}GB, recommended: ${RECOMMENDED_DISK_SPACE_GB}GB)"
        else
            print_check "FAIL" "Available disk space: ${available_space_gb}GB (minimum ${MIN_DISK_SPACE_GB}GB required)"
        fi
    else
        print_check "INFO" "Could not check available disk space"
    fi

    # Check CPU information
    if command_exists nproc; then
        local cpu_cores=$(nproc)
        if [[ $cpu_cores -ge 4 ]]; then
            print_check "PASS" "CPU cores: $cpu_cores (recommended: 4+)"
        elif [[ $cpu_cores -ge 2 ]]; then
            print_check "WARN" "CPU cores: $cpu_cores (minimum: 2, recommended: 4+)"
        else
            print_check "FAIL" "CPU cores: $cpu_cores (minimum 2 required)"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        local cpu_cores=$(sysctl -n hw.ncpu)
        if [[ $cpu_cores -ge 4 ]]; then
            print_check "PASS" "CPU cores: $cpu_cores (recommended: 4+)"
        elif [[ $cpu_cores -ge 2 ]]; then
            print_check "WARN" "CPU cores: $cpu_cores (minimum: 2, recommended: 4+)"
        else
            print_check "FAIL" "CPU cores: $cpu_cores (minimum 2 required)"
        fi
    else
        print_check "INFO" "Could not check CPU information"
    fi

    echo
}

# Check network connectivity
check_network() {
    echo "🌐 Network Connectivity Check"
    echo "=============================="

    # Check internet connectivity
    if curl -s --max-time 10 "https://www.google.com" >/dev/null 2>&1; then
        print_check "PASS" "Internet connectivity available"
    else
        print_check "FAIL" "No internet connectivity"
        echo
        return
    fi

    # Check Stellar network endpoints
    if curl -s --max-time 10 "https://horizon-testnet.stellar.org/" >/dev/null 2>&1; then
        print_check "PASS" "Stellar Testnet Horizon reachable"
    else
        print_check "WARN" "Stellar Testnet Horizon unreachable (may be temporary)"
    fi

    if curl -s --max-time 10 "https://horizon.stellar.org/" >/dev/null 2>&1; then
        print_check "PASS" "Stellar Mainnet Horizon reachable"
    else
        print_check "WARN" "Stellar Mainnet Horizon unreachable (may be temporary)"
    fi

    # Check Soroban RPC endpoints
    if curl -s --max-time 10 "https://soroban-testnet.stellar.org/health" >/dev/null 2>&1; then
        print_check "PASS" "Soroban Testnet RPC reachable"
    else
        print_check "WARN" "Soroban Testnet RPC unreachable (may be temporary)"
    fi

    # Check GitHub connectivity (for cloning repository)
    if curl -s --max-time 10 "https://github.com/" >/dev/null 2>&1; then
        print_check "PASS" "GitHub reachable (for repository cloning)"
    else
        print_check "WARN" "GitHub unreachable - repository cloning may fail"
    fi

    # Check PyPI connectivity (for installing Python packages)
    if curl -s --max-time 10 "https://pypi.org/" >/dev/null 2>&1; then
        print_check "PASS" "PyPI reachable (for Python package installation)"
    else
        print_check "WARN" "PyPI unreachable - package installation may fail"
    fi

    echo
}

# Check optional tools
check_optional_tools() {
    echo "🔧 Optional Tools Check"
    echo "======================="

    # Check Docker
    if command_exists docker; then
        if docker --version >/dev/null 2>&1; then
            local docker_version=$(docker --version | cut -d' ' -f3 | sed 's/,//')
            print_check "PASS" "Docker $docker_version available (optional for advanced deployment)"
        else
            print_check "WARN" "Docker installed but not running"
        fi
    else
        print_check "INFO" "Docker not installed (optional for containerized deployment)"
    fi

    # Check kubectl
    if command_exists kubectl; then
        local kubectl_version=$(kubectl version --client --short 2>/dev/null | cut -d' ' -f3)
        print_check "PASS" "kubectl $kubectl_version available (optional for Kubernetes deployment)"
    else
        print_check "INFO" "kubectl not installed (optional for Kubernetes deployment)"
    fi

    # Check make
    if command_exists make; then
        local make_version=$(make --version | head -1 | cut -d' ' -f3)
        print_check "PASS" "make $make_version available (optional for build automation)"
    else
        print_check "INFO" "make not installed (optional for build automation)"
    fi

    # Check curl
    if command_exists curl; then
        local curl_version=$(curl --version | head -1 | cut -d' ' -f2)
        print_check "PASS" "curl $curl_version available"
    else
        print_check "WARN" "curl not available - some network tests may fail"
    fi

    echo
}

# Check development tools
check_development_tools() {
    echo "👨‍💻 Development Tools Check (Optional)"
    echo "======================================"

    # Check code editors
    local editors_found=0
    for editor in code vim nano emacs; do
        if command_exists $editor; then
            print_check "PASS" "$editor editor available"
            ((editors_found++))
        fi
    done

    if [[ $editors_found -eq 0 ]]; then
        print_check "INFO" "No common code editors found (install vim, nano, or VS Code)"
    fi

    # Check shell
    if [[ -n "${BASH_VERSION:-}" ]]; then
        print_check "PASS" "bash $BASH_VERSION shell"
    elif [[ -n "${ZSH_VERSION:-}" ]]; then
        print_check "PASS" "zsh $ZSH_VERSION shell"
    else
        print_check "INFO" "Shell: $SHELL"
    fi

    echo
}

# Generate installation commands
generate_installation_commands() {
    echo "📋 Installation Commands"
    echo "========================"

    local os_type=""
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt; then
            os_type="ubuntu"
        elif command_exists yum; then
            os_type="centos"
        elif command_exists dnf; then
            os_type="fedora"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        os_type="macos"
    fi

    case $os_type in
        "ubuntu")
            echo "For Ubuntu/Debian systems:"
            echo "  sudo apt update"
            echo "  sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip git curl"
            ;;
        "centos")
            echo "For CentOS systems:"
            echo "  sudo yum install -y python311 python311-pip python311-devel git curl"
            ;;
        "fedora")
            echo "For Fedora systems:"
            echo "  sudo dnf install -y python3.11 python3-pip python3-devel git curl"
            ;;
        "macos")
            echo "For macOS systems:"
            echo "  # Install Homebrew if not already installed:"
            echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            echo "  # Install requirements:"
            echo "  brew install python@3.11 git"
            ;;
        *)
            echo "Please install the following manually:"
            echo "  - Python 3.11 or higher"
            echo "  - Git"
            echo "  - curl"
            ;;
    esac

    echo
    echo "After installing prerequisites, run the automated installer:"
    echo "  curl -fsSL https://raw.githubusercontent.com/stellar/hummingbot-connector-v3/main/scripts/install.sh | bash"
    echo
}

# Generate summary report
generate_summary() {
    echo "📊 Prerequisites Check Summary"
    echo "=============================="

    echo "Results:"
    echo "  ✅ Passed: $PASSED"
    echo "  ⚠️  Warnings: $WARNINGS"
    echo "  ❌ Failed: $FAILED"
    echo

    if [[ $FAILED -eq 0 ]]; then
        if [[ $WARNINGS -eq 0 ]]; then
            echo "🎉 All prerequisites met! You can proceed with installation."
        else
            echo "✅ Prerequisites mostly met. Review warnings above, but installation should work."
        fi
        echo
        echo "Ready to install? Run:"
        echo "  curl -fsSL https://raw.githubusercontent.com/stellar/hummingbot-connector-v3/main/scripts/install.sh | bash"
    else
        echo "❌ Some prerequisites are missing. Please install the required components and run this check again."
        echo
        generate_installation_commands
    fi

    echo
    echo "For detailed installation instructions, visit:"
    echo "  https://github.com/stellar/hummingbot-connector-v3/blob/main/INSTALL.md"
}

# Main function
main() {
    echo "🌟 Stellar Hummingbot Connector v3.0 - Prerequisites Checker"
    echo "============================================================"
    echo

    check_operating_system
    check_python
    check_git
    check_system_resources
    check_network
    check_optional_tools
    check_development_tools
    generate_summary
}

# Run the checks
main "$@"