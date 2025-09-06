#!/usr/bin/env python3
"""
Python Auto-Accept Configuration
Override input functions to eliminate all interactive prompts.
"""

import builtins
import sys
import os

# Store original functions
_original_input = builtins.input
_original_print = builtins.print

def auto_accept_input(prompt=""):
    """Override input() to auto-accept with empty string."""
    if prompt:
        print(f"{prompt}[AUTO-ACCEPT: '']")
    return ""

def quiet_print(*args, **kwargs):
    """Optionally quiet print statements."""
    # Only suppress prompts/questions, allow normal output
    text = " ".join(str(arg) for arg in args)
    if any(keyword in text.lower() for keyword in [
        "continue?", "proceed?", "confirm", "y/n", "(y/n)", "[y/n]", 
        "press enter", "press any key", "do you want"
    ]):
        print(f"{text} [AUTO-ACCEPT: YES]", **kwargs)
        return
    
    # Allow normal output
    _original_print(*args, **kwargs)

# Override built-in functions
builtins.input = auto_accept_input

# Set environment variables
os.environ.update({
    "PYTHONUNBUFFERED": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "NO_INTERACTIVE": "1",
    "CI": "true",
    "AUTOMATED": "true",
})

# Disable pdb
import pdb
pdb.set_trace = lambda: None

print("Python auto-accept configuration loaded")