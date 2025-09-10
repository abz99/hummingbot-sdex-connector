#!/usr/bin/env python3
"""
Fix runtime type instantiation errors
Changes Dict[Type](value) to dict(value), List[Type](value) to list(value), etc.
"""

import re
import os
import glob

def fix_type_instantiation(content):
    """Fix runtime type instantiation issues."""
    
    # Patterns to fix type instantiations
    patterns = [
        # Dict[Type](...) -> dict(...)
        (r'Dict\[str, Any\]\(([^)]+)\)', r'dict(\1)'),
        (r'Dict\[str, str\]\(([^)]+)\)', r'dict(\1)'),
        (r'Dict\[str, int\]\(([^)]+)\)', r'dict(\1)'),
        (r'Dict\[str, float\]\(([^)]+)\)', r'dict(\1)'),
        (r'Dict\[str, bool\]\(([^)]+)\)', r'dict(\1)'),
        (r'Dict\[str, Optional\[str\]\]\(([^)]+)\)', r'dict(\1)'),
        (r'Dict\[Any, Any\]\(([^)]+)\)', r'dict(\1)'),
        (r'Dict\[[^\]]+\]\(([^)]+)\)', r'dict(\1)'),  # Catch-all for other Dict patterns
        
        # List[Type](...) -> list(...)
        (r'List\[str\]\(([^)]+)\)', r'list(\1)'),
        (r'List\[int\]\(([^)]+)\)', r'list(\1)'),
        (r'List\[float\]\(([^)]+)\)', r'list(\1)'),
        (r'List\[Any\]\(([^)]+)\)', r'list(\1)'),
        (r'List\[[^\]]+\]\(([^)]+)\)', r'list(\1)'),  # Catch-all for other List patterns
        
        # Set[Type](...) -> set(...)
        (r'Set\[str\]\(([^)]+)\)', r'set(\1)'),
        (r'Set\[int\]\(([^)]+)\)', r'set(\1)'),
        (r'Set\[[^\]]+\]\(([^)]+)\)', r'set(\1)'),  # Catch-all for other Set patterns
        
        # Tuple[Type](...) -> tuple(...)
        (r'Tuple\[[^\]]+\]\(([^)]+)\)', r'tuple(\1)'),
    ]
    
    for old_pattern, new_pattern in patterns:
        content = re.sub(old_pattern, new_pattern, content)
    
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
            
            fixed_content = fix_type_instantiation(original_content)
            
            if fixed_content != original_content:
                # Count the number of fixes made
                fixes_in_file = 0
                for pattern, _ in [
                    (r'Dict\[[^\]]+\]\([^)]+\)', ''),
                    (r'List\[[^\]]+\]\([^)]+\)', ''),
                    (r'Set\[[^\]]+\]\([^)]+\)', ''),
                    (r'Tuple\[[^\]]+\]\([^)]+\)', ''),
                ]:
                    fixes_in_file += len(re.findall(pattern, original_content))
                
                total_fixes += fixes_in_file
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"Fixed {fixes_in_file} type instantiations in: {file_path}")
                fixed_count += 1
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed type instantiations in {fixed_count} files ({total_fixes} total fixes)")

if __name__ == "__main__":
    main()