#!/bin/bash
"""
Setup Knowledge Base Pipeline for Stellar Hummingbot Connector

This script sets up the automated knowledge base indexing pipeline
including dependencies, configuration, and automation.
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"
KNOWLEDGE_DIR="$PROJECT_ROOT/knowledge"

log_info "Setting up Knowledge Base Pipeline"
log_info "Project root: $PROJECT_ROOT"

# Check Python version
check_python() {
    log_info "Checking Python version..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
    if [[ "$PYTHON_VERSION" < "3.11" ]]; then
        log_error "Python 3.11+ is required, found $PYTHON_VERSION"
        exit 1
    fi
    
    log_success "Python version: $(python3 --version)"
}

# Install required packages
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Check if pip is available
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is required but not installed"
        exit 1
    fi
    
    # Install required packages
    local packages=(
        "pyyaml>=6.0"
        "watchdog>=3.0"
    )
    
    for package in "${packages[@]}"; do
        log_info "Installing $package..."
        pip3 install "$package" || {
            log_error "Failed to install $package"
            exit 1
        }
    done
    
    log_success "Dependencies installed successfully"
}

# Create directory structure
setup_directories() {
    log_info "Setting up directory structure..."
    
    # Create knowledge directory structure
    mkdir -p "$KNOWLEDGE_DIR/index"
    mkdir -p "$KNOWLEDGE_DIR/cache"
    
    # Create logs directory
    mkdir -p "$PROJECT_ROOT/logs"
    
    log_success "Directory structure created"
}

# Make scripts executable
setup_scripts() {
    log_info "Setting up scripts..."
    
    local scripts=(
        "knowledge_base_indexer.py"
        "knowledge_base_watcher.py"
    )
    
    for script in "${scripts[@]}"; do
        if [[ -f "$SCRIPTS_DIR/$script" ]]; then
            chmod +x "$SCRIPTS_DIR/$script"
            log_info "Made $script executable"
        else
            log_warning "Script not found: $script"
        fi
    done
    
    log_success "Scripts setup completed"
}

# Create systemd service (Linux only)
create_systemd_service() {
    if [[ ! -d "/etc/systemd/system" ]]; then
        log_info "Systemd not available, skipping service creation"
        return
    fi
    
    log_info "Creating systemd service..."
    
    local service_content="[Unit]
Description=Stellar Hummingbot Knowledge Base Watcher
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_ROOT
ExecStart=$SCRIPTS_DIR/knowledge_base_watcher.py --project-root $PROJECT_ROOT
Restart=always
RestartSec=5
StandardOutput=append:$PROJECT_ROOT/logs/knowledge-base-watcher.log
StandardError=append:$PROJECT_ROOT/logs/knowledge-base-watcher-error.log

[Install]
WantedBy=multi-user.target"

    local service_file="/tmp/stellar-knowledge-base-watcher.service"
    echo "$service_content" > "$service_file"
    
    log_info "Systemd service file created at: $service_file"
    log_info "To install the service, run:"
    log_info "  sudo cp $service_file /etc/systemd/system/"
    log_info "  sudo systemctl daemon-reload"
    log_info "  sudo systemctl enable stellar-knowledge-base-watcher"
    log_info "  sudo systemctl start stellar-knowledge-base-watcher"
}

# Create cron job
setup_cron_job() {
    log_info "Setting up cron job for periodic indexing..."
    
    # Create cron script
    local cron_script="$SCRIPTS_DIR/knowledge_base_cron.sh"
    
    cat > "$cron_script" << 'EOF'
#!/bin/bash
# Cron script for knowledge base indexing

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/knowledge-base-cron.log"

echo "$(date): Starting scheduled knowledge base indexing" >> "$LOG_FILE"

cd "$PROJECT_ROOT"
python3 scripts/knowledge_base_indexer.py --project-root "$PROJECT_ROOT" >> "$LOG_FILE" 2>&1

echo "$(date): Completed scheduled knowledge base indexing" >> "$LOG_FILE"
EOF
    
    chmod +x "$cron_script"
    
    log_info "Cron script created at: $cron_script"
    log_info "To add to crontab (run every 15 minutes), execute:"
    log_info "  crontab -e"
    log_info "And add this line:"
    log_info "  */15 * * * * $cron_script"
}

# Create configuration validation script
create_validation_script() {
    log_info "Creating configuration validation script..."
    
    local validation_script="$SCRIPTS_DIR/validate_knowledge_base_config.py"
    
    cat > "$validation_script" << 'EOF'
#!/usr/bin/env python3
"""Validate knowledge base configuration."""

import sys
import yaml
from pathlib import Path

def validate_config(config_file):
    """Validate team_startup.yaml configuration."""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}")
        return False
    
    # Check knowledge_base section
    if 'knowledge_base' not in config:
        print("ERROR: No knowledge_base section found in config")
        return False
    
    knowledge_bases = config['knowledge_base']
    if not isinstance(knowledge_bases, list):
        print("ERROR: knowledge_base must be a list")
        return False
    
    valid = True
    for i, kb in enumerate(knowledge_bases):
        if not isinstance(kb, dict):
            print(f"ERROR: knowledge_base[{i}] must be a dictionary")
            valid = False
            continue
        
        # Check required fields
        required_fields = ['id', 'type', 'description']
        for field in required_fields:
            if field not in kb:
                print(f"ERROR: knowledge_base[{i}] missing required field: {field}")
                valid = False
        
        # Type-specific validation
        kb_type = kb.get('type')
        if kb_type in ['file', 'directory']:
            if 'path' not in kb:
                print(f"ERROR: knowledge_base[{i}] type '{kb_type}' requires 'path' field")
                valid = False
        elif kb_type == 'multi_file':
            if 'files' not in kb:
                print(f"ERROR: knowledge_base[{i}] type 'multi_file' requires 'files' field")
                valid = False
        elif kb_type == 'web':
            if 'url' not in kb:
                print(f"ERROR: knowledge_base[{i}] type 'web' requires 'url' field")
                valid = False
    
    if valid:
        print(f"SUCCESS: Configuration is valid ({len(knowledge_bases)} knowledge bases)")
    
    return valid

if __name__ == '__main__':
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'team_startup.yaml'
    valid = validate_config(config_file)
    sys.exit(0 if valid else 1)
EOF
    
    chmod +x "$validation_script"
    log_success "Validation script created: $validation_script"
}

# Create Git hooks
setup_git_hooks() {
    log_info "Setting up Git hooks..."
    
    local hooks_dir="$PROJECT_ROOT/.git/hooks"
    if [[ ! -d "$hooks_dir" ]]; then
        log_warning "Not a git repository, skipping Git hooks"
        return
    fi
    
    # Pre-commit hook
    local pre_commit_hook="$hooks_dir/pre-commit"
    
    cat > "$pre_commit_hook" << 'EOF'
#!/bin/bash
# Pre-commit hook for knowledge base validation

PROJECT_ROOT="$(git rev-parse --show-toplevel)"

echo "Validating knowledge base configuration..."
if ! python3 "$PROJECT_ROOT/scripts/validate_knowledge_base_config.py" "$PROJECT_ROOT/team_startup.yaml"; then
    echo "ERROR: Knowledge base configuration validation failed"
    exit 1
fi

echo "Re-indexing knowledge bases..."
cd "$PROJECT_ROOT"
python3 scripts/knowledge_base_indexer.py --project-root "$PROJECT_ROOT" --force

# Add updated index files to commit
git add knowledge/index/

echo "Knowledge base validation and indexing completed"
EOF
    
    chmod +x "$pre_commit_hook"
    log_success "Git pre-commit hook created"
    
    # Post-commit hook
    local post_commit_hook="$hooks_dir/post-commit"
    
    cat > "$post_commit_hook" << 'EOF'
#!/bin/bash
# Post-commit hook for knowledge base indexing

PROJECT_ROOT="$(git rev-parse --show-toplevel)"

echo "Post-commit knowledge base indexing..."
cd "$PROJECT_ROOT"
python3 scripts/knowledge_base_indexer.py --project-root "$PROJECT_ROOT" >/dev/null 2>&1 &

echo "Knowledge base indexing started in background"
EOF
    
    chmod +x "$post_commit_hook"
    log_success "Git post-commit hook created"
}

# Create wrapper scripts
create_wrapper_scripts() {
    log_info "Creating wrapper scripts..."
    
    # Index script
    local index_script="$SCRIPTS_DIR/kb-index"
    cat > "$index_script" << 'EOF'
#!/bin/bash
# Knowledge Base Indexer wrapper script

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$PROJECT_ROOT/scripts/knowledge_base_indexer.py" --project-root "$PROJECT_ROOT" "$@"
EOF
    chmod +x "$index_script"
    
    # Watch script
    local watch_script="$SCRIPTS_DIR/kb-watch"
    cat > "$watch_script" << 'EOF'
#!/bin/bash
# Knowledge Base Watcher wrapper script

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$PROJECT_ROOT/scripts/knowledge_base_watcher.py" --project-root "$PROJECT_ROOT" "$@"
EOF
    chmod +x "$watch_script"
    
    log_success "Wrapper scripts created: kb-index, kb-watch"
}

# Test the installation
test_installation() {
    log_info "Testing installation..."
    
    # Test configuration validation
    log_info "Testing configuration validation..."
    if python3 "$SCRIPTS_DIR/validate_knowledge_base_config.py" "$PROJECT_ROOT/team_startup.yaml"; then
        log_success "Configuration validation: PASSED"
    else
        log_error "Configuration validation: FAILED"
        return 1
    fi
    
    # Test indexer
    log_info "Testing knowledge base indexer..."
    if python3 "$SCRIPTS_DIR/knowledge_base_indexer.py" --project-root "$PROJECT_ROOT" --check-only; then
        log_success "Knowledge base indexer: WORKING"
    else
        log_info "Knowledge base indexer: NEEDS UPDATE (this is normal for first run)"
    fi
    
    # Test initial indexing
    log_info "Running initial indexing..."
    if python3 "$SCRIPTS_DIR/knowledge_base_indexer.py" --project-root "$PROJECT_ROOT"; then
        log_success "Initial indexing: COMPLETED"
    else
        log_error "Initial indexing: FAILED"
        return 1
    fi
    
    log_success "Installation test completed successfully"
}

# Display usage information
show_usage() {
    log_info "Knowledge Base Pipeline Setup Complete!"
    echo
    echo "Available commands:"
    echo "  $SCRIPTS_DIR/kb-index          - Run knowledge base indexer"
    echo "  $SCRIPTS_DIR/kb-watch          - Start file watcher (interactive)"
    echo "  $SCRIPTS_DIR/knowledge_base_indexer.py --help  - Show indexer options"
    echo "  $SCRIPTS_DIR/knowledge_base_watcher.py --help   - Show watcher options"
    echo
    echo "Configuration file: $PROJECT_ROOT/team_startup.yaml"
    echo "Index directory: $KNOWLEDGE_DIR/index"
    echo "Log directory: $PROJECT_ROOT/logs"
    echo
    echo "To start monitoring immediately:"
    echo "  $SCRIPTS_DIR/kb-watch"
    echo
    echo "For automated setup (choose one):"
    echo "  1. Systemd service (Linux): See instructions above"
    echo "  2. Cron job: See crontab instructions above"
}

# Main execution
main() {
    log_info "Starting Knowledge Base Pipeline Setup"
    
    check_python
    install_dependencies
    setup_directories
    setup_scripts
    create_validation_script
    create_systemd_service
    setup_cron_job
    setup_git_hooks
    create_wrapper_scripts
    test_installation
    
    log_success "Knowledge Base Pipeline setup completed successfully!"
    echo
    show_usage
}

# Run main function
main "$@"