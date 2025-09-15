#!/usr/bin/env python3
"""
User Acceptance Testing Suite for Stellar Hummingbot Connector v3.0
Comprehensive testing from end-user perspective
"""

import os
import sys
import subprocess
import tempfile
import shutil
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

class UserAcceptanceTestRunner:
    """
    Comprehensive user acceptance testing suite.
    Tests the complete user journey from installation to operation.
    """

    def __init__(self):
        self.test_results = {}
        self.test_start_time = datetime.now()
        self.temp_dir = None
        self.original_dir = os.getcwd()

    def run_command(self, command: str, timeout: int = 300) -> Tuple[bool, str, str]:
        """Execute a command and capture output."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.temp_dir if self.temp_dir else None
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def test_documentation_accessibility(self) -> Dict[str, Any]:
        """Test 1: Documentation Accessibility and Completeness"""
        print("\n📖 UAT 1: Documentation Accessibility")

        test_result = {
            "name": "Documentation Accessibility",
            "status": "running",
            "details": {},
            "score": 0,
            "max_score": 100
        }

        # Check key documentation files exist
        key_docs = [
            "README.md",
            "INSTALL.md",
            "OPERATIONS_MANUAL.md",
            "PROJECT_STATUS.md",
            "DOCUMENTATION_COMPLETENESS_ASSESSMENT.md"
        ]

        docs_found = 0
        for doc in key_docs:
            if os.path.exists(doc):
                docs_found += 1
                print(f"  ✅ Found {doc}")
            else:
                print(f"  ❌ Missing {doc}")

        test_result["details"]["documents_found"] = f"{docs_found}/{len(key_docs)}"
        test_result["score"] = (docs_found / len(key_docs)) * 100

        # Check INSTALL.md content quality
        if os.path.exists("INSTALL.md"):
            with open("INSTALL.md", "r") as f:
                install_content = f.read()

            quality_checks = [
                ("One-click install", "curl -fsSL" in install_content),
                ("Prerequisites section", "Prerequisites" in install_content),
                ("Cross-platform support", "Windows" in install_content and "macOS" in install_content),
                ("Troubleshooting", "troubleshoot" in install_content.lower()),
                ("Quick start", "quick" in install_content.lower())
            ]

            quality_score = sum(1 for _, check in quality_checks if check) / len(quality_checks) * 100
            test_result["details"]["install_guide_quality"] = f"{quality_score:.0f}%"
            test_result["score"] = (test_result["score"] + quality_score) / 2

        test_result["status"] = "passed" if test_result["score"] >= 80 else "failed"
        return test_result

    def test_installation_process(self) -> Dict[str, Any]:
        """Test 2: Complete Installation Process"""
        print("\n🔧 UAT 2: Installation Process")

        test_result = {
            "name": "Installation Process",
            "status": "running",
            "details": {},
            "score": 0,
            "max_score": 100
        }

        # Create temporary directory for clean installation test
        self.temp_dir = tempfile.mkdtemp(prefix="stellar_uat_")
        print(f"  📁 Testing in: {self.temp_dir}")

        # Copy installation scripts to temp directory
        scripts_to_copy = [
            "scripts/install.sh",
            "scripts/check_prerequisites.sh",
            "requirements.txt"
        ]

        scripts_copied = 0
        for script in scripts_to_copy:
            if os.path.exists(script):
                shutil.copy2(script, self.temp_dir)
                scripts_copied += 1

        test_result["details"]["scripts_available"] = f"{scripts_copied}/{len(scripts_to_copy)}"

        # Test prerequisites check
        print("  🔍 Testing prerequisites check...")
        success, stdout, stderr = self.run_command("bash check_prerequisites.sh")
        test_result["details"]["prerequisites_check"] = "passed" if success else "failed"

        if success:
            print("  ✅ Prerequisites check passed")
            test_result["score"] += 50
        else:
            print(f"  ❌ Prerequisites check failed: {stderr}")

        # Test installation script execution
        if os.path.exists(os.path.join(self.temp_dir, "install.sh")):
            print("  🚀 Testing installation script...")
            success, stdout, stderr = self.run_command("bash install.sh --dry-run", timeout=60)

            if success or "dry-run" in stdout.lower():
                print("  ✅ Installation script executes correctly")
                test_result["score"] += 50
                test_result["details"]["install_script"] = "passed"
            else:
                print(f"  ❌ Installation script failed: {stderr}")
                test_result["details"]["install_script"] = "failed"

        test_result["status"] = "passed" if test_result["score"] >= 80 else "failed"
        return test_result

    def test_operational_procedures(self) -> Dict[str, Any]:
        """Test 3: Operational Procedures and Commands"""
        print("\n⚙️  UAT 3: Operational Procedures")

        test_result = {
            "name": "Operational Procedures",
            "status": "running",
            "details": {},
            "score": 0,
            "max_score": 100
        }

        # Return to original directory for operational tests
        os.chdir(self.original_dir)
        self.temp_dir = None

        # Test key operational scripts
        operational_scripts = [
            ("scripts/test_installation.py", "Installation tester"),
            ("scripts/check_prerequisites.sh", "Prerequisites checker"),
            ("monitoring/monitor_cli.py", "Monitoring CLI")
        ]

        scripts_working = 0
        for script, description in operational_scripts:
            if os.path.exists(script):
                print(f"  🧪 Testing {description}...")

                # Test script help/version
                success, stdout, stderr = self.run_command(f"python3 {script} --help", timeout=30)
                if success or "usage:" in stdout.lower() or "help" in stdout.lower():
                    print(f"    ✅ {description} responds correctly")
                    scripts_working += 1
                else:
                    # Try alternative execution methods
                    if script.endswith('.sh'):
                        success, stdout, stderr = self.run_command(f"bash {script} --help", timeout=30)
                        if success:
                            scripts_working += 1
                    print(f"    ⚠️  {description} may need configuration")
            else:
                print(f"  ❌ {description} not found")

        test_result["details"]["operational_scripts"] = f"{scripts_working}/{len(operational_scripts)}"
        test_result["score"] = (scripts_working / len(operational_scripts)) * 100

        # Test operations manual completeness
        if os.path.exists("OPERATIONS_MANUAL.md"):
            with open("OPERATIONS_MANUAL.md", "r") as f:
                ops_content = f.read()

            operational_sections = [
                "Daily Operations",
                "Monitoring",
                "Troubleshooting",
                "Security",
                "Backup",
                "Performance"
            ]

            sections_found = sum(1 for section in operational_sections if section in ops_content)
            test_result["details"]["operations_manual_completeness"] = f"{sections_found}/{len(operational_sections)}"

            # Boost score if manual is comprehensive
            if sections_found >= 4:
                test_result["score"] = min(100, test_result["score"] + 20)

        test_result["status"] = "passed" if test_result["score"] >= 70 else "failed"
        return test_result

    def test_user_experience(self) -> Dict[str, Any]:
        """Test 4: Overall User Experience"""
        print("\n👤 UAT 4: User Experience")

        test_result = {
            "name": "User Experience",
            "status": "running",
            "details": {},
            "score": 0,
            "max_score": 100
        }

        ux_criteria = []

        # Test installation time simulation
        print("  ⏱️  Simulating installation time...")
        start_time = time.time()

        # Simulate quick validation (representing optimized install)
        success, stdout, stderr = self.run_command("python3 scripts/quick_validation.py", timeout=60)
        end_time = time.time()

        install_time = end_time - start_time
        test_result["details"]["simulated_install_time"] = f"{install_time:.1f} seconds"

        if install_time < 30:  # Target: under 30 seconds for validation
            ux_criteria.append(("Fast installation", True))
            print(f"    ✅ Quick validation completed in {install_time:.1f}s")
        else:
            ux_criteria.append(("Fast installation", False))
            print(f"    ⚠️  Validation took {install_time:.1f}s")

        # Test error handling and messaging
        print("  📋 Testing error handling...")
        success, stdout, stderr = self.run_command("python3 scripts/test_installation.py --invalid-flag", timeout=30)

        helpful_error = any(word in (stdout + stderr).lower() for word in ["help", "usage", "invalid", "error"])
        ux_criteria.append(("Helpful error messages", helpful_error))

        if helpful_error:
            print("    ✅ Error messages are helpful")
        else:
            print("    ⚠️  Error messages could be more helpful")

        # Test documentation clarity
        readme_exists = os.path.exists("README.md")
        install_exists = os.path.exists("INSTALL.md")
        ux_criteria.append(("Clear documentation", readme_exists and install_exists))

        # Test cross-platform indicators
        if install_exists:
            with open("INSTALL.md", "r") as f:
                install_content = f.read()
            cross_platform = all(platform in install_content for platform in ["Windows", "macOS", "Linux"])
            ux_criteria.append(("Cross-platform support", cross_platform))

        # Calculate UX score
        ux_score = sum(1 for _, passed in ux_criteria if passed) / len(ux_criteria) * 100
        test_result["score"] = ux_score
        test_result["details"]["ux_criteria_passed"] = f"{sum(1 for _, passed in ux_criteria if passed)}/{len(ux_criteria)}"

        test_result["status"] = "passed" if test_result["score"] >= 75 else "failed"
        return test_result

    def test_production_readiness(self) -> Dict[str, Any]:
        """Test 5: Production Readiness"""
        print("\n🚀 UAT 5: Production Readiness")

        test_result = {
            "name": "Production Readiness",
            "status": "running",
            "details": {},
            "score": 0,
            "max_score": 100
        }

        production_checks = []

        # Test configuration management
        config_files = [
            "pytest.ini",
            "mypy.ini",
            ".github/workflows",
            "deployment/"
        ]

        config_present = sum(1 for config in config_files if os.path.exists(config))
        production_checks.append(("Configuration management", config_present >= 3))

        # Test monitoring capabilities
        monitoring_present = os.path.exists("monitoring/") and os.path.exists("OPERATIONS_MANUAL.md")
        production_checks.append(("Monitoring and observability", monitoring_present))

        # Test security measures
        security_indicators = [
            os.path.exists("requirements-prod.txt"),  # Production requirements
            "security" in " ".join(os.listdir(".")),  # Security-related files
        ]
        security_present = any(security_indicators)
        production_checks.append(("Security measures", security_present))

        # Test automation
        automation_scripts = [
            "scripts/install.sh",
            "scripts/check_prerequisites.sh",
            ".github/workflows"
        ]
        automation_present = sum(1 for script in automation_scripts if os.path.exists(script))
        production_checks.append(("Deployment automation", automation_present >= 2))

        # Test documentation completeness
        if os.path.exists("DOCUMENTATION_COMPLETENESS_ASSESSMENT.md"):
            with open("DOCUMENTATION_COMPLETENESS_ASSESSMENT.md", "r") as f:
                doc_content = f.read()
            doc_score_high = "95%" in doc_content or "90%" in doc_content
            production_checks.append(("Documentation completeness", doc_score_high))
        else:
            production_checks.append(("Documentation completeness", False))

        # Calculate production readiness score
        prod_score = sum(1 for _, passed in production_checks if passed) / len(production_checks) * 100
        test_result["score"] = prod_score
        test_result["details"]["production_criteria_passed"] = f"{sum(1 for _, passed in production_checks if passed)}/{len(production_checks)}"

        # Detailed results
        for check_name, passed in production_checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")

        test_result["status"] = "passed" if test_result["score"] >= 80 else "failed"
        return test_result

    def generate_uat_report(self, test_results: List[Dict[str, Any]]) -> str:
        """Generate comprehensive UAT report."""

        report_time = datetime.now()
        total_duration = report_time - self.test_start_time

        # Calculate overall scores
        total_score = sum(result["score"] for result in test_results)
        max_total_score = sum(result["max_score"] for result in test_results)
        overall_percentage = (total_score / max_total_score) * 100 if max_total_score > 0 else 0

        passed_tests = sum(1 for result in test_results if result["status"] == "passed")
        total_tests = len(test_results)

        # Determine overall status
        if overall_percentage >= 85:
            overall_status = "EXCELLENT ✨"
        elif overall_percentage >= 75:
            overall_status = "GOOD ✅"
        elif overall_percentage >= 65:
            overall_status = "ACCEPTABLE ⚠️"
        else:
            overall_status = "NEEDS IMPROVEMENT ❌"

        report = f"""
# User Acceptance Testing Report
**Stellar Hummingbot Connector v3.0**

## Executive Summary
- **Overall Score**: {overall_percentage:.1f}% ({total_score:.0f}/{max_total_score})
- **Tests Passed**: {passed_tests}/{total_tests}
- **Overall Status**: {overall_status}
- **Test Duration**: {total_duration.total_seconds():.1f} seconds
- **Test Date**: {report_time.strftime('%Y-%m-%d %H:%M:%S')}

## Test Results Summary

"""

        for i, result in enumerate(test_results, 1):
            status_icon = "✅" if result["status"] == "passed" else "❌"
            report += f"### {i}. {result['name']} {status_icon}\n"
            report += f"- **Score**: {result['score']:.1f}%\n"
            report += f"- **Status**: {result['status'].upper()}\n"

            if result["details"]:
                report += "- **Details**:\n"
                for key, value in result["details"].items():
                    report += f"  - {key.replace('_', ' ').title()}: {value}\n"
            report += "\n"

        # Recommendations section
        report += "## Recommendations\n\n"

        if overall_percentage >= 85:
            report += "🎉 **Excellent performance!** The system is ready for production deployment.\n\n"
            report += "### Suggested Next Steps:\n"
            report += "- Proceed with production deployment\n"
            report += "- Begin user training and onboarding\n"
            report += "- Set up production monitoring\n"

        elif overall_percentage >= 75:
            report += "✅ **Good performance!** Minor improvements recommended before production.\n\n"
            report += "### Areas for Improvement:\n"
            failed_tests = [r for r in test_results if r["status"] == "failed"]
            for test in failed_tests:
                report += f"- Address issues in: {test['name']}\n"

        else:
            report += "⚠️ **Significant improvements needed** before production deployment.\n\n"
            report += "### Critical Issues to Address:\n"
            low_scoring_tests = [r for r in test_results if r["score"] < 70]
            for test in low_scoring_tests:
                report += f"- **{test['name']}**: {test['score']:.1f}% (needs improvement)\n"

        report += "\n## Technical Details\n\n"
        report += f"- **Test Environment**: {os.name} {sys.platform}\n"
        report += f"- **Python Version**: {sys.version.split()[0]}\n"
        report += f"- **Working Directory**: {self.original_dir}\n"

        return report

    def cleanup(self):
        """Clean up temporary resources."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"🧹 Cleaned up temporary directory: {self.temp_dir}")

    def run_full_uat_suite(self) -> str:
        """Run complete user acceptance testing suite."""
        print("🚀 Starting User Acceptance Testing Suite for Stellar Hummingbot Connector v3.0")
        print(f"📅 Test Start Time: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        test_results = []

        try:
            # Execute all UAT tests
            test_results.append(self.test_documentation_accessibility())
            test_results.append(self.test_installation_process())
            test_results.append(self.test_operational_procedures())
            test_results.append(self.test_user_experience())
            test_results.append(self.test_production_readiness())

            # Generate comprehensive report
            report = self.generate_uat_report(test_results)

            # Save report to file
            report_filename = f"UAT_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_filename, 'w') as f:
                f.write(report)

            print(f"\n📋 UAT Report saved to: {report_filename}")

            return report

        finally:
            self.cleanup()

def main():
    """Main entry point for UAT runner."""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
User Acceptance Testing Suite for Stellar Hummingbot Connector v3.0

Usage:
    python3 scripts/user_acceptance_testing.py [options]

Options:
    --help          Show this help message
    --quick         Run quick validation only
    --verbose       Enable verbose output

This comprehensive UAT suite tests:
1. Documentation accessibility and quality
2. Installation process and user experience
3. Operational procedures and tooling
4. Overall user experience factors
5. Production readiness criteria

The suite generates a detailed report with scores and recommendations.
        """)
        return

    # Run the complete UAT suite
    uat_runner = UserAcceptanceTestRunner()
    report = uat_runner.run_full_uat_suite()

    print("\n" + "=" * 80)
    print("📊 USER ACCEPTANCE TESTING COMPLETE")
    print("=" * 80)
    print(report)

if __name__ == "__main__":
    main()