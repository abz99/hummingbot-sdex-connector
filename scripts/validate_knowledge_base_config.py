#!/usr/bin/env python3
"""Validate knowledge base configuration."""

import sys
import yaml
from pathlib import Path

def validate_config(config_file):
    """Validate team_startup.yaml configuration."""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}")
        return False
    
    # Check knowledge_base section
    if 'knowledge_base' not in config:
        print("ERROR: No knowledge_base section found in config")
        return False
    
    knowledge_bases = config['knowledge_base']
    if not isinstance(knowledge_bases, list):
        print("ERROR: knowledge_base must be a list")
        return False
    
    valid = True
    for i, kb in enumerate(knowledge_bases):
        if not isinstance(kb, dict):
            print(f"ERROR: knowledge_base[{i}] must be a dictionary")
            valid = False
            continue
        
        # Check required fields
        required_fields = ['id', 'type', 'description']
        for field in required_fields:
            if field not in kb:
                print(f"ERROR: knowledge_base[{i}] missing required field: {field}")
                valid = False
        
        # Type-specific validation
        kb_type = kb.get('type')
        if kb_type in ['file', 'directory']:
            if 'path' not in kb:
                print(f"ERROR: knowledge_base[{i}] type '{kb_type}' requires 'path' field")
                valid = False
        elif kb_type == 'multi_file':
            if 'files' not in kb:
                print(f"ERROR: knowledge_base[{i}] type 'multi_file' requires 'files' field")
                valid = False
        elif kb_type == 'web':
            if 'url' not in kb:
                print(f"ERROR: knowledge_base[{i}] type 'web' requires 'url' field")
                valid = False
    
    if valid:
        print(f"SUCCESS: Configuration is valid ({len(knowledge_bases)} knowledge bases)")
    
    return valid

if __name__ == '__main__':
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'team_startup.yaml'
    valid = validate_config(config_file)
    sys.exit(0 if valid else 1)