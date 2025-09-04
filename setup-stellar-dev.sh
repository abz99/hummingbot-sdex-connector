#!/bin/bash
# setup-stellar-dev.sh - Complete development environment setup

set -e

echo "Setting up Stellar SDEX development environment..."

# Check Python version
python_version=$(python3.11 --version 2>/dev/null || echo "Not found")
if [[ $python_version == "Not found" ]]; then
    echo "Python 3.11+ is required. Please install it first."
    exit 1
fi

echo "✓ Python version: $python_version"

# Check Neovim
nvim_version=$(nvim --version 2>/dev/null | head -1 || echo "Not found")
if [[ $nvim_version == "Not found" ]]; then
    echo "Neovim is required. Please install it first."
    exit 1
fi

echo "✓ Neovim version: $nvim_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel

# Core dependencies
pip install stellar-sdk==8.* hummingbot asyncio aiohttp

# Development dependencies
pip install pytest pytest-asyncio pytest-cov
pip install black flake8 mypy isort
pip install python-lsp-server[all]

# Security dependencies
pip install cryptography hvac

# Monitoring dependencies
pip install prometheus-client structlog python-json-logger

echo "✓ Python environment setup complete"

# Setup Neovim configuration
echo "Setting up Neovim configuration..."

# Backup existing config
if [ -d "$HOME/.config/nvim" ]; then
    echo "Backing up existing Neovim configuration..."
    mv "$HOME/.config/nvim" "$HOME/.config/nvim.backup.$(date +%s)"
fi

# Create new config directory
mkdir -p "$HOME/.config/nvim/lua"

echo "✓ Neovim configuration directory created"

# Install Claude Code if not present
if ! command -v claude-code &> /dev/null; then
    echo "Claude Code not found. Please install it following the instructions at:"
    echo "https://docs.anthropic.com/en/docs/claude-code"
    echo "Then run this script again."
    exit 1
fi

echo "✓ Claude Code installation verified"

# Create project-specific files
echo "Creating project-specific configuration files..."

# .nvimrc for project
cat > .nvimrc << 'NVIMRC_EOF'
-- Project-specific Neovim configuration loaded automatically
vim.opt_local.tabstop = 4
vim.opt_local.shiftwidth = 4  
vim.opt_local.expandtab = true
vim.opt_local.textwidth = 100

-- Activate virtual environment
vim.env.VIRTUAL_ENV = vim.fn.getcwd() .. "/venv"
vim.env.PATH = vim.env.VIRTUAL_ENV .. "/bin:" .. vim.env.PATH
NVIMRC_EOF

# pytest.ini
cat > pytest.ini << 'PYTEST_EOF'
[tool:pytest]
testpaths = test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --strict-config
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=90
    --asyncio-mode=auto
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    security: Security tests
asyncio_mode = auto
PYTEST_EOF

# .flake8
cat > .flake8 << 'FLAKE8_EOF'
[flake8]
max-line-length = 100
extend-ignore = E203, W503, E501
exclude = 
    .git,
    __pycache__,
    venv,
    .venv,
    build,
    dist,
    .pytest_cache
per-file-ignores =
    __init__.py:F401
    test_*.py:S101
FLAKE8_EOF

# mypy.ini
cat > mypy.ini << 'MYPY_EOF'
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

[mypy-tests.*]
disallow_untyped_defs = False

[mypy-stellar_sdk.*]
ignore_missing_imports = True

[mypy-hummingbot.*]
ignore_missing_imports = True
MYPY_EOF

# pyproject.toml
cat > pyproject.toml << 'PYPROJECT_EOF'
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?
vim.keymap.set("n", "<leader>ca", "<cmd>lua _CLAUDE_ASK()<CR>", { desc
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 100
known_first_party = ["stellar_connector"]
known_third_party = ["stellar_sdk", "hummingbot"]

[build-system]
requires = ["setuptools>=45", "wheel", "setuptools_scm[toml]>=6.2"]
build-backend = "setuptools.build_meta"
PYPROJECT_EOF

echo "✓ Project configuration files created"

# Test the setup
echo "Testing development environment..."

# Test Python imports
python -c "import sys; print(f'Python {sys.version}')"
python -c "import stellar_sdk; print(f'Stellar SDK version: {stellar_sdk.__version__}')"

# Test tools
black --version
flake8 --version
mypy --version
pytest --version

echo ""
echo "🎉 Stellar SDEX development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Start Neovim: nvim"
echo "2. Let plugins install automatically"
echo "3. Run :checkhealth to verify setup"
echo "4. Begin development with PROJECT_INIT_001 task"
echo ""
echo "Claude Code integration:"
echo "- Use <leader>cc to open Claude Code terminal"
echo "- Use <leader>ca to ask Claude questions"
echo "- Use <leader>ce to edit with Claude"
echo "- Use ./claude-stellar.sh for enhanced commands"