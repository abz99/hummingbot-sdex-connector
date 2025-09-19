#!/usr/bin/env python3
"""
Compliance Watchdog - Continuous monitoring for Claude bypass attempts
Runs independently of Claude sessions to detect tampering
"""

import os
import sys
import time
import json
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

class ComplianceWatchdog:
    """Independent watchdog monitoring compliance integrity."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.compliance_dir = self.project_root / ".compliance"
        self.last_check = None

    def check_file_integrity(self):
        """Check if critical files have been tampered with."""
        integrity_file = self.compliance_dir / "integrity-checksums.txt"

        if not integrity_file.exists():
            return False, "Integrity checksum file missing"

        violations = []

        with open(integrity_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue

                parts = line.split(' ', 1)
                if len(parts) != 2:
                    continue

                expected_hash, filename = parts
                file_path = self.project_root / filename

                if not file_path.exists():
                    violations.append(f"Critical file missing: {filename}")
                    continue

                with open(file_path, 'rb') as f:
                    actual_hash = hashlib.sha256(f.read()).hexdigest()

                if actual_hash != expected_hash:
                    violations.append(f"File modified: {filename}")

        return len(violations) == 0, violations

    def scan_for_bypass_patterns(self):
        """Scan for known Claude bypass patterns."""
        bypass_patterns = [
            r"git.*commit.*--no-verify",
            r"SKIP_COMPLIANCE_CHECK.*=.*1",
            r"pytest\.skip\(",
            r"\|\|\s*true",
            r"export.*SKIP.*=.*true"
        ]

        violations = []

        for pattern in bypass_patterns:
            try:
                result = subprocess.run([
                    "grep", "-r", "-E", pattern, ".",
                    "--exclude-dir=.git",
                    "--exclude-dir=venv",
                    "--exclude-dir=logs",
                    "--exclude=*.pyc"
                ], cwd=self.project_root, capture_output=True, text=True)

                if result.returncode == 0 and result.stdout.strip():
                    # Filter out documentation files
                    lines = result.stdout.strip().split('\n')
                    filtered_lines = [
                        line for line in lines
                        if not any(doc in line for doc in [
                            'COMPLIANCE_VIOLATIONS_REPORT.md',
                            'docs/',
                            'COMPLIANCE_PREVENTION_GUIDE.md'
                        ])
                    ]

                    if filtered_lines:
                        violations.extend(filtered_lines)

            except Exception:
                pass  # Skip if grep fails

        return violations

    def log_alert(self, alert_type, details):
        """Log tamper alert to compliance database."""
        db_file = self.compliance_dir / "violation-database.json"

        try:
            with open(db_file) as f:
                data = json.load(f)
        except:
            data = {"tamper_alerts": []}

        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": alert_type,
            "details": details,
            "session_id": os.environ.get('SESSION_ID', 'unknown')
        }

        data.setdefault("tamper_alerts", []).append(alert)

        try:
            with open(db_file, 'w') as f:
                json.dump(data, f, indent=2)
        except:
            pass  # Fail silently if can't write

    def run_check(self):
        """Run a single compliance check."""
        print(f"🔍 Compliance Watchdog Check - {datetime.now()}")

        # Check file integrity
        integrity_ok, integrity_issues = self.check_file_integrity()
        if not integrity_ok:
            print("❌ INTEGRITY VIOLATION DETECTED:")
            for issue in integrity_issues:
                print(f"   {issue}")
            self.log_alert("integrity_violation", integrity_issues)
            return False

        # Scan for bypass patterns
        bypass_violations = self.scan_for_bypass_patterns()
        if bypass_violations:
            print("❌ BYPASS PATTERN DETECTED:")
            for violation in bypass_violations[:5]:  # Show first 5
                print(f"   {violation}")
            self.log_alert("bypass_pattern", bypass_violations)
            return False

        print("✅ Compliance check passed")
        return True

    def continuous_monitor(self, interval=300):  # 5 minutes
        """Run continuous monitoring."""
        print("🛡️ Starting Compliance Watchdog (Continuous Mode)")
        print(f"   Check interval: {interval} seconds")

        while True:
            try:
                self.run_check()
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\n🛑 Watchdog stopped by user")
                break
            except Exception as e:
                print(f"⚠️  Watchdog error: {e}")
                time.sleep(60)  # Wait 1 minute on error

def main():
    watchdog = ComplianceWatchdog()

    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        watchdog.continuous_monitor()
    else:
        success = watchdog.run_check()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
