#!/usr/bin/env python3
"""
Simple fix for duplicate return type annotations
"""

import re
import os
import glob

def fix_duplicate_annotations(content):
    """Fix duplicate return type annotations with a simpler approach."""
    
    # Simple pattern to find and fix the specific issue
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Look for patterns like: ") -> Type1 -> Type2:"
        if ' -> ' in line and line.count(' -> ') > 1 and line.strip().endswith(':'):
            # Find the last occurrence of " -> " before the colon
            parts = line.split(' -> ')
            if len(parts) >= 3:
                # Keep everything up to the second-to-last " -> "
                fixed_line = ' -> '.join(parts[:-1]) + ':'
                fixed_lines.append(fixed_line)
                continue
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def main():
    """Process all Python files in the stellar connector directory."""
    pattern = "hummingbot/connector/exchange/stellar/*.py"
    files = glob.glob(pattern)
    
    fixed_count = 0
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            fixed_content = fix_duplicate_annotations(original_content)
            
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"Fixed duplicate annotations in: {file_path}")
                fixed_count += 1
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed duplicate annotations in {fixed_count} files")

if __name__ == "__main__":
    main()