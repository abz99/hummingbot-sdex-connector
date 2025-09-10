#!/usr/bin/env python3
"""
Fix all duplicate return type annotations
Pattern: -> Type1 -> Type2: becomes -> Type1:
"""

import re
import os
import glob

def fix_duplicate_annotations(content):
    """Fix duplicate return type annotations."""
    
    # Pattern to match duplicate annotations
    # Match: -> Type1 -> Type2: and replace with -> Type1:
    pattern = r'(\) -> [^:]+) -> [^:]+:'
    replacement = r'\1:'
    
    content = re.sub(pattern, replacement, content)
    
    return content

def main():
    """Process all Python files in the stellar connector directory."""
    pattern = "hummingbot/connector/exchange/stellar/*.py"
    files = glob.glob(pattern)
    
    fixed_count = 0
    total_fixes = 0
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            fixed_content = fix_duplicate_annotations(original_content)
            
            if fixed_content != original_content:
                # Count the number of fixes
                fixes_in_file = len(re.findall(r'\) -> [^:]+) -> [^:]+:', original_content))
                total_fixes += fixes_in_file
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"Fixed {fixes_in_file} duplicate annotations in: {file_path}")
                fixed_count += 1
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed duplicate annotations in {fixed_count} files ({total_fixes} total fixes)")

if __name__ == "__main__":
    main()