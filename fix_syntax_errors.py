#!/usr/bin/env python3
"""
Fix syntax errors from generic type annotations that require Python 3.9+
Reverts Dict[str, Any] -> Dict, List[str] -> List, etc.
"""

import re
import os
import glob

def fix_typing_imports(content):
    """Fix generic type annotations in imports."""
    # Pattern to match typing imports with generic parameters
    patterns = [
        (r'Dict\[str, Any\]', 'Dict'),
        (r'List\[str\]', 'List'),
        (r'List\[Any\]', 'List'),
        (r'set\[str\]', 'Set'),
        (r'set\[Any\]', 'Set'),
        (r'Tuple\[str, \.\.\.\]', 'Tuple'),
        (r'Tuple\[Any, \.\.\.\]', 'Tuple'),
    ]
    
    for old_pattern, new_pattern in patterns:
        content = re.sub(old_pattern, new_pattern, content)
    
    # Also add Set to imports if we changed set to Set
    if 'Set' in content and 'from typing import' in content:
        # Check if Set is already imported
        typing_import_pattern = r'(from typing import [^)\n]+)'
        match = re.search(typing_import_pattern, content)
        if match and 'Set' not in match.group(1):
            # Add Set to the import
            old_import = match.group(1)
            if old_import.endswith('\n'):
                new_import = old_import.rstrip() + ', Set\n'
            else:
                new_import = old_import + ', Set'
            content = content.replace(old_import, new_import)
    
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
            
            fixed_content = fix_typing_imports(original_content)
            
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"Fixed typing imports in: {file_path}")
                fixed_count += 1
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed typing imports in {fixed_count} files")

if __name__ == "__main__":
    main()