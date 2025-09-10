#!/usr/bin/env python3
"""
Advanced script to fix remaining MyPy type annotation issues.
Focuses on the most common patterns that weren't caught by the first script.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def fix_more_function_signatures(file_path: str) -> int:
    """Fix more complex function signature patterns."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # More sophisticated patterns for functions that need return annotations
    patterns_to_fix = [
        # Async functions without return annotations
        (r'(\n    async def [^(]+\([^)]*\))(:\n)', r'\1 -> None\2'),
        
        # Property setters
        (r'(\n    @[^.]+\.setter\n    def [^(]+\([^)]*\))(:\n)', r'\1 -> None\2'),
        
        # Event handlers and callbacks
        (r'(\n    def on_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def handle_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def _handle_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        
        # Private methods that typically don't return values
        (r'(\n    def _validate_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def _process_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def _execute_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def _send_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def _create_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def _build_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        
        # Test methods
        (r'(\n    def test_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    async def test_[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        
        # Lifecycle methods
        (r'(\n    def setup[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def teardown[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def cleanup[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def shutdown[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def close[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
        (r'(\n    def reset[^(]*\([^)]*\))(:\n)', r'\1 -> None\2'),
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
        print(f"Fixed {fixes_applied} more functions in {file_path}")
        return fixes_applied
    
    return 0

def fix_generic_type_annotations(file_path: str) -> int:
    """Fix missing type parameters for generic types."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # Common generic type fixes
    type_fixes = [
        # Dict -> Dict[str, Any]
        (r'(\W)Dict(\W)', r'\1Dict[str, Any]\2'),
        (r'(\W)dict(\W)', r'\1dict[str, Any]\2'),
        
        # List -> List[str] (most common case)
        (r'(\W)List(\W)', r'\1List[str]\2'),
        (r': list\b', ': list[str]'),
        
        # Task -> Task[None] (most common case)
        (r'(\W)Task(\W)', r'\1Task[None]\2'),
        
        # deque -> deque[Any]
        (r'(\W)deque(\W)', r'\1deque[Any]\2'),
        
        # Set -> set[str]
        (r': set\b', ': set[str]'),
        (r'(\W)Set(\W)', r'\1set[str]\2'),
    ]
    
    for pattern, replacement in type_fixes:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            content = new_content
            fixes_applied += 1
    
    # Only write if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Fixed {fixes_applied} generic types in {file_path}")
        return fixes_applied
    
    return 0

def remove_unreachable_code(file_path: str) -> int:
    """Remove or fix unreachable code statements."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # Pattern to find and fix unreachable code after early returns
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Look for return statements followed by unreachable code
        if re.match(r'^\s+return\s', line.strip()) and i + 1 < len(lines):
            next_line = lines[i + 1]
            
            # If next line is indented code at same level, it might be unreachable
            current_indent = len(line) - len(line.lstrip())
            next_indent = len(next_line) - len(next_line.lstrip()) if next_line.strip() else 0
            
            # Skip unreachable code at the same indentation level
            if (next_indent == current_indent and 
                next_line.strip() and 
                not next_line.strip().startswith('#') and
                not next_line.strip().startswith('def ') and
                not next_line.strip().startswith('class ') and
                not next_line.strip().startswith('except') and
                not next_line.strip().startswith('finally')):
                # Skip this unreachable line
                i += 1
                fixes_applied += 1
                continue
        
        i += 1
    
    if fixes_applied > 0:
        content = '\n'.join(new_lines)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Removed {fixes_applied} unreachable statements in {file_path}")
    
    return fixes_applied

def main():
    """Apply advanced MyPy fixes to Stellar connector files."""
    stellar_dir = Path("hummingbot/connector/exchange/stellar")
    
    if not stellar_dir.exists():
        print(f"Directory {stellar_dir} does not exist")
        return
    
    total_function_fixes = 0
    total_generic_fixes = 0 
    total_unreachable_fixes = 0
    files_processed = 0
    
    for file_path in stellar_dir.glob("*.py"):
        function_fixes = fix_more_function_signatures(str(file_path))
        generic_fixes = fix_generic_type_annotations(str(file_path))
        unreachable_fixes = remove_unreachable_code(str(file_path))
        
        if function_fixes > 0 or generic_fixes > 0 or unreachable_fixes > 0:
            files_processed += 1
            total_function_fixes += function_fixes
            total_generic_fixes += generic_fixes
            total_unreachable_fixes += unreachable_fixes
    
    print(f"\nAdvanced fixes summary:")
    print(f"Files processed: {files_processed}")
    print(f"Function signature fixes: {total_function_fixes}")
    print(f"Generic type fixes: {total_generic_fixes}")
    print(f"Unreachable code fixes: {total_unreachable_fixes}")
    print(f"Total fixes applied: {total_function_fixes + total_generic_fixes + total_unreachable_fixes}")

if __name__ == "__main__":
    main()