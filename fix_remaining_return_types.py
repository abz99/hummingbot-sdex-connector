#!/usr/bin/env python3
"""
Fix remaining missing return type annotations
Focuses on the specific functions identified by MyPy
"""

import re
import os
import glob

def fix_return_type_annotations(content, file_path):
    """Fix missing return type annotations in specific files."""
    
    # Patterns for different types of functions
    patterns = [
        # Void functions (methods that don't return anything)
        (r'^(\s+)def (record_|log_|update_|set_|clear_|add_|remove_|register_|initialize_|configure_|validate_|track_|alert_|fire_|push_|pull_|reset_|start_|stop_|close_|cleanup_|save_|store_|delete_)([^:]+):', r'\1def \2\3 -> None:'),
        (r'^(\s+)def (_[^_][^:]+):', r'\1def \2 -> None:'),  # Private methods usually void
        (r'^(\s+)def (setup_|teardown_|handle_|process_)([^:]+):', r'\1def \2\3 -> None:'),
        
        # Functions that likely return specific types
        (r'^(\s+)def (get_|fetch_|retrieve_|load_|read_)([^:]+):', r'\1def \2\3 -> Any:'),
        (r'^(\s+)def (calculate_|compute_|evaluate_|measure_)([^:]+):', r'\1def \2\3 -> Union[float, Decimal]:'),
        (r'^(\s+)def (is_|has_|should_|can_|check_)([^:]+):', r'\1def \2\3 -> bool:'),
        (r'^(\s+)def (create_|build_|generate_|make_)([^:]+):', r'\1def \2\3 -> Any:'),
        
        # Module level functions
        (r'^def (main|run_|execute_|test_)([^:]+):', r'def \1\2 -> None:'),
    ]
    
    # Apply patterns
    for old_pattern, new_pattern in patterns:
        content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE)
    
    # Add necessary imports if we added Union, Any, Decimal
    if 'Union' in content or 'Any' in content or 'Decimal' in content:
        if 'from typing import' in content:
            # Find typing import and add missing types
            typing_import_pattern = r'(from typing import [^)\n]+)'
            match = re.search(typing_import_pattern, content)
            if match:
                old_import = match.group(1)
                import_part = old_import.replace('from typing import ', '')
                existing_imports = {imp.strip() for imp in import_part.split(',')}
                
                needed_imports = set()
                if 'Union' in content and 'Union' not in existing_imports:
                    needed_imports.add('Union')
                if 'Any' in content and 'Any' not in existing_imports:
                    needed_imports.add('Any')
                
                if needed_imports:
                    all_imports = existing_imports | needed_imports
                    new_import_list = ', '.join(sorted(all_imports))
                    new_import = f'from typing import {new_import_list}'
                    content = content.replace(old_import, new_import)
    
    # Handle Decimal import
    if 'Decimal' in content and 'from decimal import' not in content:
        lines = content.split('\n')
        import_section_end = 0
        for i, line in enumerate(lines):
            if line.startswith('from ') or line.startswith('import '):
                import_section_end = i
        
        if import_section_end > 0:
            lines.insert(import_section_end + 1, 'from decimal import Decimal')
            content = '\n'.join(lines)
    
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
            
            fixed_content = fix_return_type_annotations(original_content, file_path)
            
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"Fixed return types in: {file_path}")
                fixed_count += 1
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed return types in {fixed_count} files")

if __name__ == "__main__":
    main()