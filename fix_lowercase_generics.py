#!/usr/bin/env python3
"""
Fix lowercase generic type annotations that require Python 3.9+
Converts dict[str, Any] -> Dict[str, Any], list[str] -> List[str], etc.
"""

import re
import os
import glob

def fix_lowercase_generics(content):
    """Fix lowercase generic type annotations."""
    # Patterns to fix lowercase generics
    patterns = [
        (r'\bdict\[([^]]+)\]', r'Dict[\1]'),
        (r'\blist\[([^]]+)\]', r'List[\1]'),
        (r'\bset\[([^]]+)\]', r'Set[\1]'),
        (r'\btuple\[([^]]+)\]', r'Tuple[\1]'),
    ]
    
    for old_pattern, new_pattern in patterns:
        content = re.sub(old_pattern, new_pattern, content)
    
    return content

def ensure_imports(content):
    """Ensure Dict, List, Set, Tuple are imported if used."""
    # Check if we have typing imports
    if 'from typing import' not in content:
        return content
    
    # Find what we need to import
    needed_imports = set()
    if re.search(r'\bDict\b', content):
        needed_imports.add('Dict')
    if re.search(r'\bList\b', content):
        needed_imports.add('List')
    if re.search(r'\bSet\b', content):
        needed_imports.add('Set')
    if re.search(r'\bTuple\b', content):
        needed_imports.add('Tuple')
    
    # Find existing typing import
    typing_import_pattern = r'(from typing import [^)\n]+)'
    match = re.search(typing_import_pattern, content)
    
    if match and needed_imports:
        old_import = match.group(1)
        # Parse existing imports
        import_part = old_import.replace('from typing import ', '')
        existing_imports = {imp.strip() for imp in import_part.split(',')}
        
        # Add missing imports
        all_imports = existing_imports | needed_imports
        new_import_list = ', '.join(sorted(all_imports))
        new_import = f'from typing import {new_import_list}'
        
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
            
            fixed_content = fix_lowercase_generics(original_content)
            fixed_content = ensure_imports(fixed_content)
            
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"Fixed lowercase generics in: {file_path}")
                fixed_count += 1
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed lowercase generics in {fixed_count} files")

if __name__ == "__main__":
    main()