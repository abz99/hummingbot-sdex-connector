#!/usr/bin/env python3
"""Test compliance integration is working correctly"""

import subprocess
import sys

def test_compliance_monitor():
    """Test compliance monitor works"""
    result = subprocess.run([sys.executable, ".claude_compliance_monitor.py"],
                          capture_output=True, text=True)
    return result.returncode in [0, 1]  # 0=pass, 1=violations, 2=critical

def test_session_guard():
    """Test session guard works"""
    result = subprocess.run([sys.executable, ".claude_session_guard.py"],
                          capture_output=True, text=True)
    return result.returncode in [0, 1]

def test_git_hooks():
    """Test git hooks are installed"""
    from pathlib import Path
    hooks_dir = Path(".git/hooks")
    return (hooks_dir / "pre-commit").exists() and (hooks_dir / "post-commit").exists()

def main():
    print("🧪 Testing compliance integration...")

    tests = [
        ("Compliance Monitor", test_compliance_monitor),
        ("Session Guard", test_session_guard),
        ("Git Hooks", test_git_hooks)
    ]

    passed = 0
    for name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {name}: PASS")
                passed += 1
            else:
                print(f"❌ {name}: FAIL")
        except Exception as e:
            print(f"❌ {name}: ERROR - {e}")

    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")
    return 0 if passed == len(tests) else 1

if __name__ == "__main__":
    sys.exit(main())
