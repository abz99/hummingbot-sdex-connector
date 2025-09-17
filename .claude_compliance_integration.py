#!/usr/bin/env python3
"""
Real-Time Compliance Integration for Claude Code
Mandatory verification system that blocks false claims BEFORE they are made
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class ComplianceIntegration:
    """Real-time compliance checking integrated into Claude Code operations"""

    def __init__(self, project_root: str = "/home/abz/projects/stellar-hummingbot-connector-v3"):
        self.project_root = Path(project_root)
        self.logs_dir = self.project_root / "logs"
        self.verification_file = self.logs_dir / "verified_system_status.json"
        self.violations_file = self.logs_dir / "critical_violations.json"

    def load_current_violations(self) -> List[Dict]:
        """Load current critical violations"""
        try:
            if self.violations_file.exists():
                with open(self.violations_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading violations: {e}")
        return []

    def load_system_status(self) -> Dict:
        """Load verified system status"""
        try:
            if self.verification_file.exists():
                with open(self.verification_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading system status: {e}")
        return {}

    def check_ci_pipeline_status(self) -> Dict[str, Any]:
        """Real-time CI pipeline status check via GitHub API"""
        try:
            # Use gh CLI to get actual pipeline status
            result = subprocess.run([
                'gh', 'run', 'list', '--limit', '3', '--json',
                'name,status,conclusion,created_at'
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                runs = json.loads(result.stdout)

                pipelines = {
                    'Stellar Hummingbot Connector CI': None,
                    'Production Deployment Pipeline': None,
                    'CI Health Dashboard': None
                }

                # Map latest runs to pipelines
                for run in runs:
                    name = run.get('name', '')
                    if name in pipelines:
                        pipelines[name] = {
                            'status': run.get('status'),
                            'conclusion': run.get('conclusion'),
                            'created_at': run.get('created_at')
                        }

                # Count successes
                successful_count = sum(1 for p in pipelines.values()
                                     if p and p.get('conclusion') == 'success')
                total_count = len(pipelines)

                return {
                    'timestamp': datetime.utcnow().isoformat(),
                    'total_pipelines': total_count,
                    'successful_pipelines': successful_count,
                    'failed_pipelines': total_count - successful_count,
                    'pipelines': pipelines,
                    'overall_status': 'SUCCESS' if successful_count == total_count else 'FAILURE'
                }

        except Exception as e:
            print(f"Error checking CI status: {e}")

        return {
            'timestamp': datetime.utcnow().isoformat(),
            'error': 'Unable to verify CI pipeline status',
            'overall_status': 'UNKNOWN'
        }

    def validate_claim(self, claim_type: str, claimed_status: str) -> Dict[str, Any]:
        """Validate a specific claim against real data"""
        validation_result = {
            'claim_type': claim_type,
            'claimed_status': claimed_status,
            'validation_timestamp': datetime.utcnow().isoformat(),
            'valid': False,
            'evidence': {},
            'enforcement_action': 'BLOCK_CLAIM'
        }

        if claim_type == 'ci_pipeline_status':
            # Get real CI status
            actual_status = self.check_ci_pipeline_status()
            validation_result['evidence'] = actual_status

            # Validate claim
            if claimed_status.upper() == 'SUCCESS' or claimed_status.upper() == 'RESOLVED':
                validation_result['valid'] = (
                    actual_status.get('overall_status') == 'SUCCESS' and
                    actual_status.get('successful_pipelines') == actual_status.get('total_pipelines')
                )
            elif claimed_status.upper() == 'FAILURE' or claimed_status.upper() == 'FAILING':
                validation_result['valid'] = (
                    actual_status.get('overall_status') != 'SUCCESS' or
                    actual_status.get('failed_pipelines', 0) > 0
                )

            if not validation_result['valid']:
                validation_result['enforcement_action'] = 'BLOCK_FALSE_CLAIM'
                validation_result['error'] = f"Claimed '{claimed_status}' but actual status is '{actual_status.get('overall_status')}'"

        elif claim_type == 'mission_status':
            # Check if any critical violations exist
            violations = self.load_current_violations()
            system_status = self.load_system_status()

            validation_result['evidence'] = {
                'violations_count': len(violations),
                'system_status': system_status.get('overall_status', 'UNKNOWN')
            }

            if claimed_status.upper() in ['ACCOMPLISHED', 'COMPLETE', 'SUCCESS']:
                # Mission can only be accomplished if no critical violations
                validation_result['valid'] = (
                    len(violations) == 0 and
                    system_status.get('overall_status') != 'CRITICAL FAILURES'
                )

                if not validation_result['valid']:
                    validation_result['enforcement_action'] = 'BLOCK_FALSE_SUCCESS_CLAIM'
                    validation_result['error'] = f"Cannot claim mission accomplished with {len(violations)} critical violations"

        return validation_result

    def enforce_compliance_check(self, message_content: str) -> Dict[str, Any]:
        """Scan message content for claims and validate them"""
        enforcement_result = {
            'timestamp': datetime.utcnow().isoformat(),
            'blocked_claims': [],
            'validated_claims': [],
            'overall_enforcement': 'ALLOW',
            'warnings': []
        }

        content_upper = message_content.upper()

        # Detect high-risk claims
        high_risk_phrases = [
            'MISSION ACCOMPLISHED',
            'CI PIPELINE.*RESOLVED',
            'ACCOUNTABILITY CRISIS.*RESOLVED',
            '3/3.*PIPELINES.*SUCCESS',
            '3/3.*PIPELINES.*OPERATIONAL',
            'ALL PIPELINES.*WORKING',
            'COMPLETE.*RESOLUTION',
            'FULLY OPERATIONAL'
        ]

        import re

        for phrase in high_risk_phrases:
            if re.search(phrase, content_upper):
                if 'MISSION' in phrase or 'ACCOMPLISHED' in phrase:
                    validation = self.validate_claim('mission_status', 'ACCOMPLISHED')
                elif 'PIPELINE' in phrase or 'CI' in phrase:
                    validation = self.validate_claim('ci_pipeline_status', 'SUCCESS')
                else:
                    validation = self.validate_claim('mission_status', 'COMPLETE')

                if not validation['valid']:
                    enforcement_result['blocked_claims'].append({
                        'phrase': phrase,
                        'validation': validation
                    })
                    enforcement_result['overall_enforcement'] = 'BLOCK'
                else:
                    enforcement_result['validated_claims'].append({
                        'phrase': phrase,
                        'validation': validation
                    })

        # Add warnings for suspicious language
        warning_phrases = [
            'SUCCESS',
            'RESOLVED',
            'OPERATIONAL',
            'WORKING',
            'COMPLETE'
        ]

        for phrase in warning_phrases:
            if phrase in content_upper and phrase not in [c['phrase'] for c in enforcement_result['validated_claims']]:
                enforcement_result['warnings'].append(f"Potentially unverified claim: '{phrase}'")

        return enforcement_result

    def generate_compliance_report(self) -> str:
        """Generate a comprehensive compliance status report"""
        ci_status = self.check_ci_pipeline_status()
        violations = self.load_current_violations()
        system_status = self.load_system_status()

        report = f"""
# 🛡️ REAL-TIME COMPLIANCE STATUS

**Generated**: {datetime.utcnow().isoformat()}
**Enforcement Level**: HARD ENFORCEMENT ACTIVE

## 🚦 CI Pipeline Status (Real-Time)
**Overall Status**: {ci_status.get('overall_status', 'UNKNOWN')}
**Successful Pipelines**: {ci_status.get('successful_pipelines', 0)}/{ci_status.get('total_pipelines', 3)}
**Failed Pipelines**: {ci_status.get('failed_pipelines', 'Unknown')}

### Pipeline Details:
"""

        for name, details in ci_status.get('pipelines', {}).items():
            if details:
                status_emoji = "✅" if details.get('conclusion') == 'success' else "❌"
                report += f"- {status_emoji} **{name}**: {details.get('status')} ({details.get('conclusion')})\n"
            else:
                report += f"- ❓ **{name}**: No recent runs found\n"

        report += f"""

## 🚨 Critical Violations
**Active Violations**: {len(violations)}
"""

        if violations:
            latest_violation = violations[-1]
            report += f"**Latest Violation**: {latest_violation.get('timestamp', 'Unknown')}\n"
            report += f"**Enforcement Action**: {latest_violation.get('enforcement_action', 'Unknown')}\n"
        else:
            report += "**Status**: No active critical violations\n"

        report += f"""

## 📋 System Status
**Overall Status**: {system_status.get('overall_status', 'UNKNOWN')}
**Critical Components**: {len(system_status.get('critical_violations', []))}

## ⚡ Enforcement Rules
- ❌ **BLOCKED**: Any "Mission Accomplished" claims while violations exist
- ❌ **BLOCKED**: Any "CI Pipeline Success" claims without 3/3 pipelines passing
- ❌ **BLOCKED**: Any "Resolved" claims without evidence verification
- ✅ **ALLOWED**: Honest status reporting with evidence
- ✅ **ALLOWED**: Work-in-progress updates with accurate status

## 🎯 Current Enforcement Decision
"""

        # Determine overall enforcement decision
        if ci_status.get('overall_status') == 'SUCCESS' and len(violations) == 0:
            report += "✅ **ALLOW SUCCESS CLAIMS**: All systems operational, no violations\n"
        elif len(violations) > 0:
            report += "❌ **BLOCK SUCCESS CLAIMS**: Critical violations active\n"
        elif ci_status.get('overall_status') != 'SUCCESS':
            report += "❌ **BLOCK SUCCESS CLAIMS**: CI pipelines not fully operational\n"
        else:
            report += "⚠️ **REQUIRE VERIFICATION**: Status unclear, manual verification required\n"

        return report


def main():
    """CLI interface for compliance checking"""
    import argparse

    parser = argparse.ArgumentParser(description='Real-Time Compliance Integration')
    parser.add_argument('--check-status', action='store_true', help='Check current compliance status')
    parser.add_argument('--validate-claim', help='Validate a specific claim')
    parser.add_argument('--claim-type', default='ci_pipeline_status', help='Type of claim to validate')
    parser.add_argument('--check-message', help='Check a message for compliance violations')
    parser.add_argument('--report', action='store_true', help='Generate compliance report')

    args = parser.parse_args()

    compliance = ComplianceIntegration()

    if args.check_status:
        ci_status = compliance.check_ci_pipeline_status()
        print(json.dumps(ci_status, indent=2))

    elif args.validate_claim:
        validation = compliance.validate_claim(args.claim_type, args.validate_claim)
        print(json.dumps(validation, indent=2))
        sys.exit(0 if validation['valid'] else 1)

    elif args.check_message:
        enforcement = compliance.enforce_compliance_check(args.check_message)
        print(json.dumps(enforcement, indent=2))
        sys.exit(0 if enforcement['overall_enforcement'] == 'ALLOW' else 1)

    elif args.report:
        report = compliance.generate_compliance_report()
        print(report)

    else:
        # Default: check current status
        ci_status = compliance.check_ci_pipeline_status()
        print(f"CI Pipeline Status: {ci_status.get('overall_status')}")
        print(f"Successful: {ci_status.get('successful_pipelines', 0)}/{ci_status.get('total_pipelines', 3)}")


if __name__ == '__main__':
    main()