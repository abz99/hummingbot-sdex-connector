#!/usr/bin/env python3
"""
Fix malformed type annotations created by the previous script
"""

import re
import os
import glob

def fix_malformed_annotations(content):
    """Fix malformed return type annotations."""
    
    # Fix patterns like: -> None: Type to just -> None
    patterns = [
        (r'(\s+def [^:]+) -> None: \w+:', r'\1 -> None:'),
        (r'(\s+def [^:]+) -> Any: \w+:', r'\1 -> Any:'),
        (r'(\s+def [^:]+) -> Union\[float, Decimal\]: \w+:', r'\1 -> Union[float, Decimal]:'),
        (r'(\s+def [^:]+) -> bool: \w+:', r'\1 -> bool:'),
        
        # Fix function parameters with malformed annotations
        (r'(\w+) -> \w+:', r'\1:'),
        
        # Fix specific malformed patterns found in the logs
        (r'def ([^(]+)\(([^)]*)\) -> None: ([^:]+):', r'def \1(\2) -> None:'),
        (r'def ([^(]+)\(([^)]*)\) -> Any: ([^:]+):', r'def \1(\2) -> Any:'),
        (r'def ([^(]+)\(([^)]*)\) -> Union\[float, Decimal\]: ([^:]+):', r'def \1(\2) -> Union[float, Decimal]:'),
        (r'def ([^(]+)\(([^)]*)\) -> bool: ([^:]+):', r'def \1(\2) -> bool:'),
        
        # Fix parameter annotations that got corrupted
        (r', (\w+) -> \w+:', r', \1:'),
        (r'\((\w+) -> \w+:', r'(\1:'),
    ]
    
    for old_pattern, new_pattern in patterns:
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
            
            fixed_content = fix_malformed_annotations(original_content)
            
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"Fixed malformed annotations in: {file_path}")
                fixed_count += 1
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed malformed annotations in {fixed_count} files")

if __name__ == "__main__":
    main()