#!/usr/bin/env python3
"""
Fix collections generic type annotations that require Python 3.9+
Converts deque[Any] -> deque, defaultdict[...] -> defaultdict, etc.
"""

import re
import os
import glob

def fix_collections_generics(content):
    """Fix collections generic type annotations."""
    # Fix imports first
    patterns = [
        (r'from collections import ([^,\n]*), deque\[Any\]', r'from collections import \1, deque'),
        (r'from collections import deque\[Any\]', r'from collections import deque'),
        (r'from collections import defaultdict\[([^\]]+)\]', r'from collections import defaultdict'),
    ]
    
    for old_pattern, new_pattern in patterns:
        content = re.sub(old_pattern, new_pattern, content)
    
    # Fix usage in code
    usage_patterns = [
        (r'\bdeque\[Any\]', r'deque'),
        (r'\bdeque\[[^\]]+\]', r'deque'),
        (r'\bdefaultdict\[[^\]]+\]', r'defaultdict'),
    ]
    
    for old_pattern, new_pattern in usage_patterns:
        content = re.sub(old_pattern, new_pattern, content)
    
    return content

def main():
    """Process all Python files in the stellar connector directory."""
    pattern = "hummingbot/connector/exchange/stellar/*.py"
    files = glob.glob(pattern)
    
    fixed_count = 0
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            fixed_content = fix_collections_generics(original_content)
            
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"Fixed collections generics in: {file_path}")
                fixed_count += 1
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed collections generics in {fixed_count} files")

if __name__ == "__main__":
    main()