#!/usr/bin/env python3
"""
Fix missing type parameters for Dict in function signatures and variable annotations
"""

import re
import os
import glob

def fix_dict_type_parameters(content):
    """Fix missing type parameters for Dict."""
    
    # Patterns to fix missing Dict type parameters in different contexts
    patterns = [
        # Function parameters: func(param: Dict) -> func(param: Dict[str, Any])
        (r'([,\(]\s*\w+:\s*)Dict(\s*[,\)])', r'\1Dict[str, Any]\2'),
        
        # Function return types: -> Dict -> -> Dict[str, Any]
        (r'(\s+->\s*)Dict(\s*:)', r'\1Dict[str, Any]\2'),
        
        # Variable annotations: var: Dict = -> var: Dict[str, Any] =
        (r'(\w+:\s*)Dict(\s*=)', r'\1Dict[str, Any]\2'),
        
        # Class attributes: attr: Dict -> attr: Dict[str, Any]
        (r'(\s+\w+:\s*)Dict(\s*$)', r'\1Dict[str, Any]\2'),
    ]
    
    for old_pattern, new_pattern in patterns:
        content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE)
    
    return content

def fix_deque_type_parameters(content):
    """Fix missing type parameters for deque."""
    
    patterns = [
        # deque without type parameters
        (r'([,\(]\s*\w+:\s*)deque(\s*[,\)])', r'\1deque[Any]\2'),
        (r'(\s+->\s*)deque(\s*:)', r'\1deque[Any]\2'),
        (r'(\w+:\s*)deque(\s*=)', r'\1deque[Any]\2'),
        (r'(\s+\w+:\s*)deque(\s*$)', r'\1deque[Any]\2'),
    ]
    
    for old_pattern, new_pattern in patterns:
        content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE)
    
    return content

def fix_list_type_parameters(content):
    """Fix missing type parameters for List."""
    
    patterns = [
        # List without type parameters in function signatures
        (r'([,\(]\s*\w+:\s*)List(\s*[,\)])', r'\1List[Any]\2'),
        (r'(\s+->\s*)List(\s*:)', r'\1List[Any]\2'),
        (r'(\w+:\s*)List(\s*=)', r'\1List[Any]\2'),
        (r'(\s+\w+:\s*)List(\s*$)', r'\1List[Any]\2'),
    ]
    
    for old_pattern, new_pattern in patterns:
        content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE)
    
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
            
            fixed_content = original_content
            fixed_content = fix_dict_type_parameters(fixed_content)
            fixed_content = fix_deque_type_parameters(fixed_content)
            fixed_content = fix_list_type_parameters(fixed_content)
            
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"Fixed missing type parameters in: {file_path}")
                fixed_count += 1
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed missing type parameters in {fixed_count} files")

if __name__ == "__main__":
    main()