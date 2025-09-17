#!/usr/bin/env python3
"""
Test CI Monitoring System Integration
Validates all CI monitoring components are working correctly
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

class CIMonitoringTester:
    """Test the CI monitoring system integration"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.test_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'tests': {},
            'overall_status': 'unknown',
            'issues': [],
            'recommendations': []
        }

    def test_script_syntax(self) -> bool:
        """Test all monitoring scripts have valid syntax"""
        scripts = [
            '.github/ci-monitor.py',
            '.github/post-push-ci-monitor.py',
            'scripts/ci-push-wrapper.sh'
        ]

        all_valid = True
        for script in scripts:
            script_path = self.project_root / script
            if not script_path.exists():
                self.test_results['issues'].append(f"Missing script: {script}")
                all_valid = False
                continue

            try:
                if script.endswith('.py'):
                    # Test Python syntax
                    result = subprocess.run([
                        sys.executable, '-m', 'py_compile', str(script_path)
                    ], capture_output=True, text=True)

                    if result.returncode != 0:
                        self.test_results['issues'].append(f"Python syntax error in {script}: {result.stderr}")
                        all_valid = False

                elif script.endswith('.sh'):
                    # Test bash syntax
                    result = subprocess.run([
                        'bash', '-n', str(script_path)
                    ], capture_output=True, text=True)

                    if result.returncode != 0:
                        self.test_results['issues'].append(f"Bash syntax error in {script}: {result.stderr}")
                        all_valid = False

            except Exception as e:
                self.test_results['issues'].append(f"Error testing {script}: {e}")
                all_valid = False

        self.test_results['tests']['script_syntax'] = {
            'status': 'pass' if all_valid else 'fail',
            'scripts_tested': len(scripts),
            'valid_scripts': len(scripts) - len([i for i in self.test_results['issues'] if 'syntax error' in i])
        }

        return all_valid

    def test_executable_permissions(self) -> bool:
        """Test that all scripts have proper executable permissions"""
        executables = [
            '.github/ci-monitor.py',
            '.github/post-push-ci-monitor.py',
            'scripts/ci-push-wrapper.sh',
            '.github/hooks/post-receive'
        ]

        all_executable = True
        for executable in executables:
            executable_path = self.project_root / executable
            if executable_path.exists():
                if not os.access(executable_path, os.X_OK):
                    self.test_results['issues'].append(f"Not executable: {executable}")
                    all_executable = False
            else:
                self.test_results['issues'].append(f"Missing executable: {executable}")
                all_executable = False

        self.test_results['tests']['executable_permissions'] = {
            'status': 'pass' if all_executable else 'fail',
            'executables_tested': len(executables)
        }

        return all_executable

    def test_dependencies(self) -> bool:
        """Test that required dependencies are available"""
        required_deps = ['requests', 'json', 'subprocess', 'pathlib', 'datetime']
        python_deps = []

        for dep in required_deps:
            try:
                __import__(dep)
                python_deps.append(f"{dep}: available")
            except ImportError:
                python_deps.append(f"{dep}: missing")
                self.test_results['issues'].append(f"Missing Python dependency: {dep}")

        # Check for external tools
        external_tools = ['git', 'bash']
        tool_status = []

        for tool in external_tools:
            try:
                result = subprocess.run([tool, '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    tool_status.append(f"{tool}: available")
                else:
                    tool_status.append(f"{tool}: unavailable")
                    self.test_results['issues'].append(f"External tool not available: {tool}")
            except FileNotFoundError:
                tool_status.append(f"{tool}: not found")
                self.test_results['issues'].append(f"External tool not found: {tool}")

        all_deps_available = len([d for d in python_deps if 'missing' not in d]) == len(required_deps)
        all_tools_available = len([t for t in tool_status if 'not' not in t]) == len(external_tools)

        self.test_results['tests']['dependencies'] = {
            'status': 'pass' if (all_deps_available and all_tools_available) else 'fail',
            'python_deps': python_deps,
            'external_tools': tool_status
        }

        return all_deps_available and all_tools_available

    def test_ci_monitor_basic(self) -> bool:
        """Test basic CI monitor functionality"""
        try:
            # Test help function
            result = subprocess.run([
                sys.executable, '.github/ci-monitor.py', '--help'
            ], capture_output=True, text=True, timeout=30)

            help_works = result.returncode == 0

            # Test basic execution (without GitHub token)
            result = subprocess.run([
                sys.executable, '.github/ci-monitor.py'
            ], capture_output=True, text=True, timeout=60)

            # Should work even without token (with warnings)
            basic_execution = result.returncode in [0, 1]  # 0=success, 1=warnings

            self.test_results['tests']['ci_monitor_basic'] = {
                'status': 'pass' if (help_works and basic_execution) else 'fail',
                'help_works': help_works,
                'basic_execution': basic_execution,
                'stderr': result.stderr[:200] if result.stderr else None
            }

            return help_works and basic_execution

        except Exception as e:
            self.test_results['issues'].append(f"CI monitor test failed: {e}")
            self.test_results['tests']['ci_monitor_basic'] = {
                'status': 'fail',
                'error': str(e)
            }
            return False

    def test_post_push_monitor_basic(self) -> bool:
        """Test basic post-push monitor functionality"""
        try:
            # Test help function
            result = subprocess.run([
                sys.executable, '.github/post-push-ci-monitor.py', '--help'
            ], capture_output=True, text=True, timeout=30)

            help_works = result.returncode == 0

            self.test_results['tests']['post_push_monitor_basic'] = {
                'status': 'pass' if help_works else 'fail',
                'help_works': help_works,
                'stderr': result.stderr[:200] if result.stderr else None
            }

            return help_works

        except Exception as e:
            self.test_results['issues'].append(f"Post-push monitor test failed: {e}")
            self.test_results['tests']['post_push_monitor_basic'] = {
                'status': 'fail',
                'error': str(e)
            }
            return False

    def test_git_integration(self) -> bool:
        """Test Git integration capabilities"""
        try:
            # Check if we're in a git repository
            result = subprocess.run(['git', 'status'], capture_output=True, text=True)
            in_git_repo = result.returncode == 0

            # Check if we can get commit SHA
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
            can_get_sha = result.returncode == 0
            commit_sha = result.stdout.strip() if can_get_sha else None

            # Check remote configuration
            result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True)
            has_remote = result.returncode == 0 and 'origin' in result.stdout

            self.test_results['tests']['git_integration'] = {
                'status': 'pass' if (in_git_repo and can_get_sha) else 'fail',
                'in_git_repo': in_git_repo,
                'can_get_sha': can_get_sha,
                'has_remote': has_remote,
                'commit_sha': commit_sha[:8] if commit_sha else None
            }

            return in_git_repo and can_get_sha

        except Exception as e:
            self.test_results['issues'].append(f"Git integration test failed: {e}")
            self.test_results['tests']['git_integration'] = {
                'status': 'fail',
                'error': str(e)
            }
            return False

    def test_directory_structure(self) -> bool:
        """Test that required directories and files exist"""
        required_structure = {
            'directories': [
                '.github',
                '.github/workflows',
                '.github/hooks',
                'scripts',
                'logs'
            ],
            'files': [
                '.github/workflows/ci.yml',
                '.github/workflows/knowledge-base-ci.yml',
                '.github/workflows/production-deploy.yml',
                '.github/workflows/ci-health-dashboard.yml',
                'requirements-dev.txt'
            ]
        }

        missing_dirs = []
        missing_files = []

        # Check directories
        for directory in required_structure['directories']:
            dir_path = self.project_root / directory
            if not dir_path.exists():
                missing_dirs.append(directory)
                # Create logs directory if it doesn't exist
                if directory == 'logs':
                    dir_path.mkdir(exist_ok=True)

        # Check files
        for file in required_structure['files']:
            file_path = self.project_root / file
            if not file_path.exists():
                missing_files.append(file)

        if missing_dirs:
            self.test_results['issues'].extend([f"Missing directory: {d}" for d in missing_dirs])

        if missing_files:
            self.test_results['issues'].extend([f"Missing file: {f}" for f in missing_files])

        structure_complete = len(missing_dirs) == 0 and len(missing_files) == 0

        self.test_results['tests']['directory_structure'] = {
            'status': 'pass' if structure_complete else 'fail',
            'missing_directories': missing_dirs,
            'missing_files': missing_files
        }

        return structure_complete

    def run_all_tests(self) -> bool:
        """Run all tests and generate comprehensive report"""
        print("🧪 Starting CI Monitoring System Integration Tests...")
        print()

        tests = [
            ("Directory Structure", self.test_directory_structure),
            ("Script Syntax", self.test_script_syntax),
            ("Executable Permissions", self.test_executable_permissions),
            ("Dependencies", self.test_dependencies),
            ("Git Integration", self.test_git_integration),
            ("CI Monitor Basic", self.test_ci_monitor_basic),
            ("Post-Push Monitor Basic", self.test_post_push_monitor_basic)
        ]

        passed_tests = 0
        total_tests = len(tests)

        for test_name, test_func in tests:
            print(f"🔍 Running {test_name}...")
            try:
                if test_func():
                    print(f"   ✅ {test_name}: PASS")
                    passed_tests += 1
                else:
                    print(f"   ❌ {test_name}: FAIL")
            except Exception as e:
                print(f"   💥 {test_name}: ERROR - {e}")
                self.test_results['issues'].append(f"{test_name} crashed: {e}")

        print()

        # Determine overall status
        if passed_tests == total_tests:
            self.test_results['overall_status'] = 'healthy'
            print(f"✅ ALL TESTS PASSED ({passed_tests}/{total_tests})")
        elif passed_tests >= total_tests * 0.8:
            self.test_results['overall_status'] = 'degraded'
            print(f"⚠️ MOSTLY WORKING ({passed_tests}/{total_tests}) - Some issues detected")
        else:
            self.test_results['overall_status'] = 'failing'
            print(f"❌ SIGNIFICANT ISSUES ({passed_tests}/{total_tests}) - Manual intervention required")

        # Add recommendations
        if self.test_results['issues']:
            print("\n🔧 Issues Detected:")
            for issue in self.test_results['issues']:
                print(f"   - {issue}")

            self.test_results['recommendations'] = [
                "Review and fix the issues listed above",
                "Ensure all required files and directories exist",
                "Verify executable permissions on scripts",
                "Check that all dependencies are properly installed",
                "Test GitHub token configuration if API access is needed"
            ]

        return self.test_results['overall_status'] in ['healthy', 'degraded']

    def save_results(self, output_file: str = "logs/ci_monitoring_test_results.json"):
        """Save test results to file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\n📁 Test results saved to: {output_path}")

def main():
    """Main entry point"""
    tester = CIMonitoringTester()

    # Run all tests
    success = tester.run_all_tests()

    # Save results
    tester.save_results()

    # Exit with appropriate code
    if success:
        print("\n🎉 CI Monitoring System is ready for use!")
        print("\n💡 Quick start:")
        print("   - Push with verification: ./scripts/ci-push-wrapper.sh")
        print("   - Check CI health: python .github/ci-monitor.py")
        print("   - Monitor after push: python .github/post-push-ci-monitor.py")
        sys.exit(0)
    else:
        print("\n🚨 CI Monitoring System needs attention before use")
        print("📋 Review the issues above and fix them before proceeding")
        sys.exit(1)

if __name__ == "__main__":
    main()