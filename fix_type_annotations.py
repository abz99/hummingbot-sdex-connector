#!/usr/bin/env python3
"""
Automated script to fix common MyPy type annotation issues.
This script specifically targets functions missing return type annotations.
"""

import os
import re
from pathlib import Path

def fix_missing_return_annotations(file_path: str) -> int:
    """Fix missing return type annotations in a Python file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # Pattern to match function definitions without return type annotations
    # This pattern looks for:
    # - def function_name(...):
    # - async def function_name(...):
    # But excludes functions that already have -> in the signature
    
    patterns_to_fix = [
        # Standard functions without return annotation
        (r'(\n    def __post_init__\(self\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def __init__\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def _init_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def record_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def set_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def log_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def fire_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def register_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def update_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def start[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def stop[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def add_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def setup[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def configure[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def cleanup[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        
        # Multi-line function signatures (common pattern)
        (r'(\n    def [^(]+\(\s*[^)]*\n[^)]*\))(:\n)', r'\1 -> None\2'),
    ]
    
    for pattern, replacement in patterns_to_fix:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            content = new_content
            fixes_applied += 1
    
    # Only write if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Fixed {fixes_applied} functions in {file_path}")
        return fixes_applied
    
    return 0

def main():
    """Fix type annotations in all Stellar connector files."""
    stellar_dir = Path("hummingbot/connector/exchange/stellar")
    
    if not stellar_dir.exists():
        print(f"Directory {stellar_dir} does not exist")
        return
    
    total_fixes = 0
    files_processed = 0
    
    # Focus on files with the most issues first
    priority_files = [
        "stellar_observability.py",
        "stellar_metrics.py", 
        "stellar_production_metrics.py",
        "stellar_security_hardening.py",
        "stellar_qa_metrics_optimized.py",
        "stellar_health_monitor.py",
        "stellar_connection_manager.py",
        "stellar_security_metrics.py",
    ]
    
    # Process priority files first
    for filename in priority_files:
        file_path = stellar_dir / filename
        if file_path.exists():
            fixes = fix_missing_return_annotations(str(file_path))
            total_fixes += fixes
            files_processed += 1
    
    # Process remaining Python files
    for file_path in stellar_dir.glob("*.py"):
        if file_path.name not in priority_files:
            fixes = fix_missing_return_annotations(str(file_path))
            total_fixes += fixes  
            files_processed += 1
    
    print(f"\nSummary:")
    print(f"Files processed: {files_processed}")
    print(f"Total fixes applied: {total_fixes}")

if __name__ == "__main__":
    main()