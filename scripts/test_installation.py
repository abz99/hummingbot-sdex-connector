#!/usr/bin/env python3
"""
Installation Test Suite for Stellar Hummingbot Connector v3.0
Tests core installation components and functionality
"""

import subprocess
import sys
import os
import tempfile
import shutil
from pathlib import Path

def run_command(command, timeout=30):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def test_python_installation():
    """Test Python installation and virtual environment creation."""
    print("🐍 Testing Python Installation...")

    # Check Python version
    success, stdout, stderr = run_command("python3 --version")
    if not success:
        return False, "Python 3 not found"

    python_version = stdout.strip().split()[-1]
    print(f"   ✅ Python version: {python_version}")

    # Test virtual environment creation
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = os.path.join(temp_dir, "test_venv")
        success, stdout, stderr = run_command(f"python3 -m venv {venv_path}")
        if not success:
            return False, f"Virtual environment creation failed: {stderr}"

        print("   ✅ Virtual environment creation works")

    return True, "Python installation tests passed"

def test_git_functionality():
    """Test Git functionality."""
    print("📁 Testing Git Functionality...")

    # Check Git version
    success, stdout, stderr = run_command("git --version")
    if not success:
        return False, "Git not found"

    git_version = stdout.strip()
    print(f"   ✅ {git_version}")

    # Test Git clone functionality
    with tempfile.TemporaryDirectory() as temp_dir:
        test_repo = os.path.join(temp_dir, "test_repo")
        success, stdout, stderr = run_command(f"git init {test_repo}")
        if not success:
            return False, f"Git init failed: {stderr}"

        print("   ✅ Git initialization works")

    return True, "Git functionality tests passed"

def test_network_connectivity():
    """Test network connectivity to required endpoints."""
    print("🌐 Testing Network Connectivity...")

    endpoints = [
        ("GitHub", "https://github.com"),
        ("PyPI", "https://pypi.org"),
        ("Stellar Testnet", "https://horizon-testnet.stellar.org"),
        ("Soroban Testnet", "https://soroban-testnet.stellar.org/health")
    ]

    all_passed = True
    for name, url in endpoints:
        success, stdout, stderr = run_command(f"curl -s --max-time 10 {url}")
        if success:
            print(f"   ✅ {name} connectivity OK")
        else:
            print(f"   ⚠️  {name} connectivity failed (may be temporary)")
            # Don't fail the test for network issues

    return True, "Network connectivity tests completed"

def test_package_installation():
    """Test Python package installation."""
    print("📦 Testing Package Installation...")

    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = os.path.join(temp_dir, "test_venv")

        # Create virtual environment
        success, stdout, stderr = run_command(f"python3 -m venv {venv_path}")
        if not success:
            return False, f"Failed to create test venv: {stderr}"

        # Use the venv python directly instead of activating
        venv_python = f"{venv_path}/bin/python"
        venv_pip = f"{venv_path}/bin/pip"
        pip_install = f"{venv_pip} install requests"

        success, stdout, stderr = run_command(pip_install)
        if not success:
            return False, f"Package installation failed: {stderr}"

        print("   ✅ Package installation works")

        # Test package import
        test_import = f"{venv_python} -c 'import requests; print(requests.__version__)'"
        success, stdout, stderr = run_command(test_import)
        if not success:
            return False, f"Package import failed: {stderr}"

        print(f"   ✅ Package import works (requests {stdout.strip()})")

    return True, "Package installation tests passed"

def test_stellar_sdk_installation():
    """Test Stellar SDK installation."""
    print("⭐ Testing Stellar SDK Installation...")

    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = os.path.join(temp_dir, "test_venv")

        # Create virtual environment
        success, stdout, stderr = run_command(f"python3 -m venv {venv_path}")
        if not success:
            return False, f"Failed to create test venv: {stderr}"

        # Install Stellar SDK
        venv_python = f"{venv_path}/bin/python"
        venv_pip = f"{venv_path}/bin/pip"
        sdk_install = f"{venv_pip} install stellar-sdk"

        success, stdout, stderr = run_command(sdk_install, timeout=60)
        if not success:
            return False, f"Stellar SDK installation failed: {stderr}"

        print("   ✅ Stellar SDK installation works")

        # Test SDK import
        test_import = f"{venv_python} -c 'from stellar_sdk import Server, Keypair; print(\"SDK import successful\")'"
        success, stdout, stderr = run_command(test_import)
        if not success:
            return False, f"Stellar SDK import failed: {stderr}"

        print("   ✅ Stellar SDK import works")

    return True, "Stellar SDK installation tests passed"

def test_ai_dependencies():
    """Test AI/ML dependencies installation."""
    print("🧠 Testing AI Dependencies Installation...")

    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = os.path.join(temp_dir, "test_venv")

        # Create virtual environment
        success, stdout, stderr = run_command(f"python3 -m venv {venv_path}")
        if not success:
            return False, f"Failed to create test venv: {stderr}"

        # Install AI dependencies
        venv_python = f"{venv_path}/bin/python"
        venv_pip = f"{venv_path}/bin/pip"
        ai_install = f"{venv_pip} install pandas numpy scikit-learn"

        success, stdout, stderr = run_command(ai_install, timeout=120)
        if not success:
            return False, f"AI dependencies installation failed: {stderr}"

        print("   ✅ AI dependencies installation works")

        # Test imports
        test_import = f"{venv_python} -c 'import pandas, numpy, sklearn; print(\"AI imports successful\")'"
        success, stdout, stderr = run_command(test_import)
        if not success:
            return False, f"AI dependencies import failed: {stderr}"

        print("   ✅ AI dependencies import works")

    return True, "AI dependencies installation tests passed"

def test_project_structure():
    """Test project structure requirements."""
    print("📁 Testing Project Structure...")

    required_files = [
        "README.md",
        "INSTALL.md",
        "OPERATIONS_MANUAL.md",
        "CONFIGURATION.md",
        "scripts/install.sh",
        "scripts/check_prerequisites.sh"
    ]

    project_root = Path(__file__).parent.parent

    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"   ✅ {file_path} exists")
        else:
            return False, f"Required file missing: {file_path}"

    return True, "Project structure tests passed"

def run_installation_tests():
    """Run all installation tests."""
    print("🧪 Stellar Hummingbot Connector v3.0 - Installation Tests")
    print("=" * 60)
    print()

    tests = [
        test_python_installation,
        test_git_functionality,
        test_network_connectivity,
        test_package_installation,
        test_stellar_sdk_installation,
        test_ai_dependencies,
        test_project_structure
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            success, message = test()
            if success:
                print(f"   ✅ {message}")
                passed += 1
            else:
                print(f"   ❌ {message}")
                failed += 1
        except Exception as e:
            print(f"   ❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()

    print("📊 Test Summary")
    print("=" * 30)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📋 Total: {passed + failed}")

    if failed == 0:
        print("\n🎉 All installation tests passed!")
        print("The installation scripts should work correctly.")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed.")
        print("Please review the failures before proceeding.")
        return False

if __name__ == "__main__":
    success = run_installation_tests()
    sys.exit(0 if success else 1)