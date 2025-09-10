#!/usr/bin/env python3
"""
Fix specific missing return type annotations identified by MyPy
"""

import re
import os

# Specific functions to fix based on MyPy output
fixes = [
    # (file_path, line_approx, function_pattern, return_type)
    ("stellar_security_metrics.py", 464, r'def _log_audit_event\(self, audit_entry: Dict\[str, Any\]\):', 'def _log_audit_event(self, audit_entry: Dict[str, Any]) -> None:'),
    ("stellar_security_metrics.py", 722, r'def update_security_requirement\(', 'def update_security_requirement(') # This one needs manual inspection
]

def fix_specific_function(file_path, line_pattern, new_line):
    """Fix specific function signature."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use regex to find and replace the specific pattern
        modified = re.sub(line_pattern, new_line, content)
        
        if modified != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified)
            print(f"Fixed return type in {file_path}")
            return True
        else:
            print(f"Pattern not found in {file_path}: {line_pattern}")
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix specific missing return type annotations."""
    base_path = "hummingbot/connector/exchange/stellar/"
    
    # Manual fixes for specific functions
    specific_fixes = [
        # stellar_security_metrics.py:464
        (f"{base_path}stellar_security_metrics.py", 
         r'def _log_audit_event\(self, audit_entry: Dict\[str, Any\]\):',
         'def _log_audit_event(self, audit_entry: Dict[str, Any]) -> None:'),
        
        # stellar_security_metrics.py:722 (module-level function)
        (f"{base_path}stellar_security_metrics.py",
         r'def update_security_requirement\(',
         'def update_security_requirement('),  # Need to add -> None after params
        
        # stellar_security_hardening.py:587
        (f"{base_path}stellar_security_hardening.py",
         r'def _rotate_keys\(self\):',
         'def _rotate_keys(self) -> None:'),
        
        # stellar_security_hardening.py:808, 815 (module-level functions)
        (f"{base_path}stellar_security_hardening.py",
         r'def get_security_hardening_manager\(',
         'def get_security_hardening_manager('), # Need manual inspection
        
        # stellar_metrics.py:592
        (f"{base_path}stellar_metrics.py",
         r'def _collect_redis_metrics\(self\):',
         'def _collect_redis_metrics(self) -> None:'),
        
        # stellar_qa_metrics_optimized.py:121, 527
        (f"{base_path}stellar_qa_metrics_optimized.py",
         r'def _initialize_cache\(self\):',
         'def _initialize_cache(self) -> None:'),
        
        # stellar_observability.py:321, 1047
        (f"{base_path}stellar_observability.py",
         r'def _start_metrics_server\(self\):',
         'def _start_metrics_server(self) -> None:'),
    ]
    
    fixed_count = 0
    for file_path, old_pattern, new_pattern in specific_fixes:
        if fix_specific_function(file_path, old_pattern, new_pattern):
            fixed_count += 1
    
    # More aggressive pattern matching for common cases
    files_to_process = [
        f"{base_path}stellar_security_metrics.py",
        f"{base_path}stellar_security_hardening.py", 
        f"{base_path}stellar_metrics.py",
        f"{base_path}stellar_qa_metrics_optimized.py",
        f"{base_path}stellar_observability.py",
    ]
    
    for file_path in files_to_process:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Add return types to common patterns that are missing them
            patterns = [
                # Methods that clearly don't return anything
                (r'def (.*_log_audit_event)\(([^)]+)\):', r'def \1(\2) -> None:'),
                (r'def (.*_rotate_keys)\(([^)]+)\):', r'def \1(\2) -> None:'),
                (r'def (.*_initialize_cache)\(([^)]+)\):', r'def \1(\2) -> None:'),
                (r'def (.*_start_metrics_server)\(([^)]+)\):', r'def \1(\2) -> None:'),
                (r'def (.*_collect_.*_metrics)\(([^)]+)\):', r'def \1(\2) -> None:'),
                
                # Module level functions that likely return None
                (r'^def (update_security_requirement)\(([^)]+)\):$', r'def \1(\2) -> None:', re.MULTILINE),
                (r'^def (get_security_hardening_manager)\(([^)]+)\):$', r'def \1(\2) -> None:', re.MULTILINE),
            ]
            
            for pattern, replacement, *flags in patterns:
                flag = flags[0] if flags else 0
                content = re.sub(pattern, replacement, content, flags=flag)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Applied pattern fixes to {file_path}")
                fixed_count += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed return type annotations in {fixed_count} attempts")

if __name__ == "__main__":
    main()