#!/usr/bin/env python3
"""
Compliance Prevention System
Automatically detects and prevents policy violations in CI pipelines
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple


class ComplianceViolation:
    def __init__(self, file_path: str, line_number: int, violation_type: str, description: str):
        self.file_path = file_path
        self.line_number = line_number
        self.violation_type = violation_type
        self.description = description

    def __str__(self):
        return f"🚨 {self.violation_type} in {self.file_path}:{self.line_number} - {self.description}"


class CompliancePreventionSystem:
    """Automated compliance violation prevention system"""

    PROHIBITED_PATTERNS = {
        'flake8_extend_ignore': {
            'pattern': r'flake8.*--extend-ignore',
            'description': 'Use of --extend-ignore violates zero-tolerance quality policy',
            'severity': 'CRITICAL'
        },
        'pytest_skip': {
            'pattern': r'@pytest\.mark\.skip\(|pytest\.skip\(',
            'description': 'Skipping tests violates NEVER SKIP FAILING TESTS policy',
            'severity': 'CRITICAL'
        },
        'quality_bypass': {
            'pattern': r'--ignore.*C901|--extend-ignore.*C901',
            'description': 'Bypassing complexity checks violates code quality standards',
            'severity': 'CRITICAL'
        },
        'config_override': {
            'pattern': r'flake8.*--max-line-length|flake8.*--max-complexity',
            'description': 'Manual config override instead of using .flake8 file',
            'severity': 'HIGH'
        }
    }

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.violations = []

    def scan_file(self, file_path: Path) -> List[ComplianceViolation]:
        """Scan a single file for compliance violations"""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except (UnicodeDecodeError, PermissionError):
            return violations

        for line_num, line in enumerate(lines, 1):
            for violation_type, rule in self.PROHIBITED_PATTERNS.items():
                if re.search(rule['pattern'], line, re.IGNORECASE):
                    violations.append(ComplianceViolation(
                        file_path=str(file_path),
                        line_number=line_num,
                        violation_type=violation_type,
                        description=rule['description']
                    ))

        return violations

    def scan_ci_pipelines(self) -> List[ComplianceViolation]:
        """Scan all CI pipeline files for violations"""
        violations = []
        ci_files = []

        # Find all CI/CD files
        ci_patterns = [
            '.github/workflows/*.yml',
            '.github/workflows/*.yaml',
            '.gitlab-ci.yml',
            'azure-pipelines.yml',
            'Jenkinsfile',
            '.circleci/config.yml'
        ]

        for pattern in ci_patterns:
            ci_files.extend(self.project_root.glob(pattern))

        # Scan each CI file
        for ci_file in ci_files:
            file_violations = self.scan_file(ci_file)
            violations.extend(file_violations)

        return violations

    def scan_test_files(self) -> List[ComplianceViolation]:
        """Scan test files for compliance violations"""
        violations = []
        test_files = []

        # Find all test files, excluding venv and other directories
        test_patterns = [
            'test/**/*.py',
            'tests/**/*.py',
            '**/test_*.py'
        ]

        excluded_dirs = {'venv', '.venv', 'env', '.env', 'node_modules', '.git', '__pycache__', '.pytest_cache', '.mypy_cache'}

        for pattern in test_patterns:
            for test_file in self.project_root.glob(pattern):
                # Skip files in excluded directories
                if any(excluded_dir in test_file.parts for excluded_dir in excluded_dirs):
                    continue
                test_files.append(test_file)

        # Scan each test file
        for test_file in test_files:
            file_violations = self.scan_file(test_file)
            violations.extend(file_violations)

        return violations

    def check_flake8_config_consistency(self) -> List[ComplianceViolation]:
        """Ensure all flake8 usage points to .flake8 config file"""
        violations = []

        # Check if .flake8 exists
        flake8_config = self.project_root / '.flake8'
        if not flake8_config.exists():
            violations.append(ComplianceViolation(
                file_path=str(flake8_config),
                line_number=0,
                violation_type='missing_config',
                description='Missing .flake8 configuration file'
            ))

        return violations

    def run_full_scan(self) -> Dict[str, List[ComplianceViolation]]:
        """Run complete compliance scan"""
        results = {
            'ci_pipelines': self.scan_ci_pipelines(),
            'test_files': self.scan_test_files(),
            'config_consistency': self.check_flake8_config_consistency()
        }

        # Flatten all violations
        all_violations = []
        for category, violations in results.items():
            all_violations.extend(violations)

        self.violations = all_violations
        return results

    def generate_report(self) -> str:
        """Generate compliance report"""
        if not self.violations:
            return "✅ No compliance violations detected"

        report = ["🚨 COMPLIANCE VIOLATIONS DETECTED", "=" * 50]

        critical_count = sum(1 for v in self.violations if 'CRITICAL' in str(v))
        high_count = sum(1 for v in self.violations if 'HIGH' in str(v))

        report.append(f"Critical Violations: {critical_count}")
        report.append(f"High Priority Violations: {high_count}")
        report.append(f"Total Violations: {len(self.violations)}")
        report.append("")

        for violation in self.violations:
            report.append(str(violation))

        report.append("")
        report.append("🔧 REMEDIATION REQUIRED:")
        report.append("1. Fix all violations before proceeding")
        report.append("2. Use .flake8 config file for consistent standards")
        report.append("3. Never use --extend-ignore or quality bypasses")
        report.append("4. Follow DEVELOPMENT_RULES.md strictly")

        return "\n".join(report)

    def install_git_hooks(self):
        """Install git hooks to prevent violations"""
        hooks_dir = self.project_root / '.git' / 'hooks'
        hooks_dir.mkdir(exist_ok=True)

        pre_commit_hook = hooks_dir / 'pre-commit'
        hook_content = """#!/bin/bash
# Compliance Prevention Git Hook
echo "🔍 Running compliance check..."
python scripts/compliance_prevention.py --check
if [ $? -ne 0 ]; then
    echo "❌ Compliance violations detected - commit blocked"
    exit 1
fi
echo "✅ Compliance check passed"
"""

        with open(pre_commit_hook, 'w') as f:
            f.write(hook_content)

        # Make executable
        os.chmod(pre_commit_hook, 0o755)
        print("✅ Git pre-commit hook installed")


def main():
    """Main function for CLI usage"""
    scanner = CompliancePreventionSystem()

    if len(sys.argv) > 1 and sys.argv[1] == '--install-hooks':
        scanner.install_git_hooks()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        results = scanner.run_full_scan()
        if scanner.violations:
            print(scanner.generate_report())
            sys.exit(1)
        else:
            print("✅ No compliance violations detected")
            sys.exit(0)

    # Default: run scan and display results
    results = scanner.run_full_scan()
    print(scanner.generate_report())

    if scanner.violations:
        print("\n🚨 ENFORCEMENT: Fix all violations before proceeding")
        sys.exit(1)


if __name__ == "__main__":
    main()