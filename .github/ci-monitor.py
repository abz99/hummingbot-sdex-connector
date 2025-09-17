#!/usr/bin/env python3
"""
GitHub CI Pipeline Monitor & Health Check System
Verifies CI pipeline health and provides automated diagnosis
"""

import os
import sys
import json
import time
import requests
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path


class GitHubCIMonitor:
    """Monitor and validate GitHub CI pipeline health"""

    def __init__(self, repo_owner: str = "abz99", repo_name: str = "stellar-hummingbot-connector-v3"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"

        # Session for rate limiting
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            })

    def check_workflow_runs(self, workflow_name: str, branch: str = "main", limit: int = 10) -> List[Dict]:
        """Check recent workflow runs for a specific workflow"""
        try:
            # Try direct workflow file approach first
            workflows_response = self.session.get(f"{self.base_url}/actions/workflows")
            if workflows_response.status_code == 200:
                workflows = workflows_response.json().get('workflows', [])
                workflow_id = None

                for workflow in workflows:
                    if workflow['path'].endswith(workflow_name) or workflow['name'] == workflow_name:
                        workflow_id = workflow['id']
                        break

                if workflow_id:
                    url = f"{self.base_url}/actions/workflows/{workflow_id}/runs"
                    params = {
                        'branch': branch,
                        'per_page': limit,
                        'sort': 'created',
                        'order': 'desc'
                    }
                    response = self.session.get(url, params=params)
                    response.raise_for_status()
                    return response.json().get('workflow_runs', [])

            return []
        except Exception as e:
            print(f"Error checking workflow runs: {e}")
            return []

    def get_overall_health_status(self) -> Dict[str, Any]:
        """Generate comprehensive CI health status"""
        workflows = [
            'Stellar Hummingbot Connector CI',
            'Production Deployment Pipeline',
            'CI Health Dashboard'
        ]

        health_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'HEALTHY',
            'workflows': {},
            'summary': {
                'total_workflows': len(workflows),
                'healthy_workflows': 0,
                'failing_workflows': 0,
                'missing_workflows': 0
            }
        }

        for workflow_name in workflows:
            runs = self.check_workflow_runs(workflow_name, limit=5)

            if not runs:
                health_data['workflows'][workflow_name] = {
                    'status': 'MISSING',
                    'latest_run': None,
                    'recent_success_rate': 0.0
                }
                health_data['summary']['missing_workflows'] += 1
                continue

            latest_run = runs[0]
            recent_runs = runs[:5]

            success_count = sum(1 for run in recent_runs if run.get('conclusion') == 'success')
            success_rate = success_count / len(recent_runs) if recent_runs else 0.0

            status = 'HEALTHY' if success_rate >= 0.8 else 'DEGRADED' if success_rate >= 0.5 else 'FAILING'

            health_data['workflows'][workflow_name] = {
                'status': status,
                'latest_run': {
                    'id': latest_run.get('id'),
                    'status': latest_run.get('status'),
                    'conclusion': latest_run.get('conclusion'),
                    'created_at': latest_run.get('created_at'),
                    'html_url': latest_run.get('html_url')
                },
                'recent_success_rate': success_rate
            }

            if status == 'HEALTHY':
                health_data['summary']['healthy_workflows'] += 1
            else:
                health_data['summary']['failing_workflows'] += 1

        # Determine overall status
        if health_data['summary']['failing_workflows'] > 0 or health_data['summary']['missing_workflows'] > 0:
            health_data['overall_status'] = 'FAILING'
        elif health_data['summary']['healthy_workflows'] < len(workflows):
            health_data['overall_status'] = 'DEGRADED'

        return health_data

    def generate_health_report(self, output_file: str = "ci-health-report.md"):
        """Generate markdown health report"""
        health_data = self.get_overall_health_status()

        report = f"""# CI Health Report

**Generated**: {health_data['timestamp']}
**Overall Status**: {health_data['overall_status']}

## Summary
- Total Workflows: {health_data['summary']['total_workflows']}
- Healthy: {health_data['summary']['healthy_workflows']}
- Failing: {health_data['summary']['failing_workflows']}
- Missing: {health_data['summary']['missing_workflows']}

## Workflow Details

"""

        for workflow_name, data in health_data['workflows'].items():
            status_emoji = "✅" if data['status'] == 'HEALTHY' else "⚠️" if data['status'] == 'DEGRADED' else "❌"

            report += f"### {status_emoji} {workflow_name}\n"
            report += f"- **Status**: {data['status']}\n"

            if data['latest_run']:
                report += f"- **Latest Run**: {data['latest_run']['conclusion']} ({data['latest_run']['status']})\n"
                report += f"- **Created**: {data['latest_run']['created_at']}\n"
                report += f"- **Success Rate**: {data['recent_success_rate']:.1%}\n"
                if data['latest_run']['html_url']:
                    report += f"- **URL**: {data['latest_run']['html_url']}\n"
            else:
                report += "- **Latest Run**: No runs found\n"

            report += "\n"

        # Write report
        with open(output_file, 'w') as f:
            f.write(report)

        print(f"Health report written to {output_file}")
        return health_data


def main():
    """Main CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description='GitHub CI Pipeline Health Monitor')
    parser.add_argument('--output', default='ci-health-report.md',
                       help='Output file for health report')
    parser.add_argument('--workflow', help='Check specific workflow')
    parser.add_argument('--format', choices=['json', 'markdown'], default='markdown',
                       help='Output format')

    args = parser.parse_args()

    monitor = GitHubCIMonitor()

    if args.workflow:
        # Check specific workflow
        runs = monitor.check_workflow_runs(args.workflow, limit=5)
        if args.format == 'json':
            print(json.dumps(runs, indent=2))
        else:
            print(f"Recent runs for {args.workflow}:")
            for run in runs:
                print(f"- {run.get('conclusion', 'pending')} ({run.get('created_at')})")
    else:
        # Generate full health report
        health_data = monitor.generate_health_report(args.output)
        if args.format == 'json':
            print(json.dumps(health_data, indent=2))


if __name__ == '__main__':
    main()