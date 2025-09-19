#!/usr/bin/env python3
"""
Compliance Guard - Pre-commit hook to prevent DEVELOPMENT_RULES.md violations
Automatically blocks commits that contain any of the resolved violation patterns.
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

class ComplianceGuard:
    """Automated compliance violation prevention system."""

    def __init__(self):
        self.violations_found = []
        self.violation_patterns = {
            # Category 1: Test Bypassing Violations
            "pytest_skip_violations": [
                r"pytest\.skip\s*\(",
                r"pytest\.mark\.skip\s*\(",
                r"@pytest\.mark\.skip\b",
                r"pytestmark\s*=\s*pytest\.mark\.skip",
            ],

            # Category 2: CI/CD Security Bypasses
            "cicd_bypasses": [
                r"\|\|\s*true\s*$",  # Command suppression
                r"--no-verify\b",    # Git hook bypass
                r"SKIP_COMPLIANCE_CHECK\s*=\s*1",
            ],

            # Category 3: Code Quality Bypasses
            "quality_bypasses": [
                r"# noqa\b",         # flake8 ignores (without specific codes)
                r"# type:\s*ignore\b", # mypy ignores (without specific codes)
                r"--ignore\s+\w+",   # Tool ignores
            ],

            # Category 4: Unauthorized Configurations
            "unauthorized_configs": [
                r"SKIP_.*=.*true",
                r"DISABLE_.*=.*true",
                r"bypass.*=.*true",
            ]
        }

        # Exceptions - legitimate conditional patterns
        self.allowed_patterns = [
            r"@pytest\.mark\.skipif\(",  # Conditional skipping is allowed
            r"pytest\.mark\.skipif\(",   # Conditional skipping is allowed
            r"# noqa: [A-Z]\d+",        # Specific flake8 codes are allowed
            r"# type: ignore\[[^\]]+\]", # Specific mypy codes are allowed
        ]

    def check_file(self, file_path: Path) -> List[Tuple[int, str, str]]:
        """Check a file for compliance violations."""
        violations = []

        if not file_path.exists() or not file_path.is_file():
            return violations

        # Skip binary files, documentation with historical examples, and certain extensions
        if file_path.suffix in ['.pyc', '.png', '.jpg', '.pdf', '.so']:
            return violations

        # Skip files that legitimately contain violation patterns for enforcement/documentation
        exclusions = [
            'COMPLIANCE_VIOLATIONS_REPORT.md',  # Historical documentation
            'COMPLIANCE_PREVENTION_GUIDE.md',   # Educational examples
            'COMPLIANCE_GOVERNANCE.md',         # Governance documentation
            'QUICK_COMPLIANCE_SETUP.md',        # Setup documentation
            'PROJECT_STATUS.md',                # Status with historical context
            'claude-resistant-enforcement.yml', # CI/CD enforcement patterns
            'compliance-enforcement.yml',       # CI/CD enforcement patterns
            'compliance-guard.py',              # This enforcement script
            'compliance-watchdog.py',           # Monitoring script
            'detect-compliance-tampering.sh',   # Detection script
            'setup-compliance-prevention.sh',   # Setup script
            'create-tamper-proof-enforcement.sh', # Advanced setup
            'check-compliance.sh',              # Checking script
            'immutable-patterns.dat',           # Pattern definitions
            '.claude/agent_memory/',            # Agent memory files
            '.vscode/settings.json',            # VS Code configuration
            'production-deploy.yml',            # CI/CD workflow files
            'ci-health-dashboard.yml',          # CI monitoring workflow
            'knowledge-base-ci.yml',            # Knowledge base workflow
            'ci.yml',                           # Main CI workflow
            '.github/workflows/',               # All workflow directory files
            '.compliance/',                     # All compliance directory files
            'scripts/detect-compliance-tampering.sh', # Full path detection script
            'scripts/setup-compliance-prevention.sh', # Full path setup script
            'scripts/create-tamper-proof-enforcement.sh', # Full path advanced setup
        ]

        if any(exclusion in str(file_path) for exclusion in exclusions):
            return violations  # These files legitimately contain patterns for enforcement

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return violations

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Check if line matches allowed patterns first
            is_allowed = any(re.search(pattern, line) for pattern in self.allowed_patterns)
            if is_allowed:
                continue

            # Check for violation patterns
            for category, patterns in self.violation_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append((line_num, category, line_stripped))

        return violations

    def check_staged_files(self) -> bool:
        """Check all staged files for violations."""
        try:
            # Get staged files
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True, text=True, check=True
            )
            staged_files = result.stdout.strip().split('\n')

            if not staged_files or staged_files == ['']:
                return True  # No staged files

        except subprocess.CalledProcessError:
            print("❌ Failed to get staged files")
            return False

        total_violations = 0

        for file_path_str in staged_files:
            if not file_path_str:
                continue

            file_path = Path(file_path_str)
            violations = self.check_file(file_path)

            if violations:
                total_violations += len(violations)
                print(f"\n🚨 COMPLIANCE VIOLATIONS in {file_path}:")

                for line_num, category, line_content in violations:
                    print(f"   Line {line_num}: {category}")
                    print(f"   Code: {line_content}")
                    print(f"   Rule: DEVELOPMENT_RULES.md prohibits this pattern")

        if total_violations > 0:
            print(f"\n❌ COMMIT BLOCKED: {total_violations} compliance violations found")
            print("\n🔧 To fix these violations:")
            print("   1. Remove pytest.skip patterns - fix the underlying test issues")
            print("   2. Remove CI/CD bypasses - fix the underlying quality issues")
            print("   3. Remove quality tool ignores - fix the actual code problems")
            print("   4. Use conditional patterns like @pytest.mark.skipif for external dependencies")
            print("\n📖 See DEVELOPMENT_RULES.md for guidance")
            print("💡 Need help? The multi-agent team can assist with systematic fixes")
            return False

        print("✅ No compliance violations detected - commit allowed")
        return True

    def install_hook(self):
        """Install this script as a pre-commit hook."""
        git_hooks_dir = Path(".git/hooks")
        git_hooks_dir.mkdir(exist_ok=True)

        hook_path = git_hooks_dir / "pre-commit"
        hook_content = f'''#!/bin/bash
# Compliance Guard - Prevent DEVELOPMENT_RULES.md violations

python3 {Path(__file__).absolute()} --check-staged
exit $?
'''

        with open(hook_path, 'w') as f:
            f.write(hook_content)

        # Make executable
        hook_path.chmod(0o755)
        print(f"✅ Compliance guard installed at {hook_path}")

def main():
    guard = ComplianceGuard()

    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        guard.install_hook()
        return 0

    elif len(sys.argv) > 1 and sys.argv[1] == "--check-staged":
        if guard.check_staged_files():
            return 0
        else:
            return 1

    else:
        print("Usage:")
        print("  python compliance-guard.py --install     # Install as pre-commit hook")
        print("  python compliance-guard.py --check-staged # Check staged files")
        return 1

if __name__ == "__main__":
    sys.exit(main())