#!/usr/bin/env python3
"""
Quick Installation Validation for Stellar Hummingbot Connector v3.0
Fast validation of core installation components
"""

import subprocess
import sys
import os

def check_command(command, description):
    """Check if a command works."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ {description}")
            return True
        else:
            print(f"❌ {description} - Failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⚠️  {description} - Timed out")
        return False
    except Exception as e:
        print(f"❌ {description} - Error: {e}")
        return False

def main():
    print("🚀 Quick Installation Validation")
    print("================================")

    tests = [
        ("python3 --version", "Python 3 available"),
        ("python3 -m venv --help", "Python venv module available"),
        ("git --version", "Git available"),
        ("curl --version", "curl available"),
        ("python3 -c 'import tempfile; print(\"Python standard library OK\")'", "Python standard library"),
    ]

    passed = 0
    total = len(tests)

    for command, description in tests:
        if check_command(command, description):
            passed += 1

    print(f"\n📊 Validation Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All core components validated!")
        print("Installation scripts should work correctly.")
        return True
    else:
        print("⚠️  Some components failed validation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)