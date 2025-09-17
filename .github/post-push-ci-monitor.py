#!/usr/bin/env python3
"""
Post-Push CI Health Monitor
Automatically validates CI pipeline health after every push to guarantee proper operation
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

class PostPushCIMonitor:
    """Monitor CI pipeline health immediately after push operations"""

    def __init__(self, repo_owner: str = "abz99", repo_name: str = "stellar-hummingbot-connector-v3"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"

        # Initialize session with authentication
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            })

        # Monitoring configuration
        self.workflows_to_monitor = [
            'ci.yml',
            'knowledge-base-ci.yml',
            'production-deploy.yml',
            'ci-health-dashboard.yml'
        ]
        self.check_interval = 30  # seconds
        self.max_wait_time = 1800  # 30 minutes

    def get_latest_commit_sha(self) -> Optional[str]:
        """Get the SHA of the latest commit on main branch"""
        try:
            result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            print(f"Error getting commit SHA: {e}")
        return None

    def wait_for_workflow_completion(self, commit_sha: str, timeout: int = 1800) -> Dict[str, Any]:
        """Wait for all workflows to complete for a specific commit"""
        start_time = time.time()
        results = {}

        print(f"Monitoring workflows for commit {commit_sha[:8]}...")

        while time.time() - start_time < timeout:
            all_complete = True
            current_results = {}

            for workflow_file in self.workflows_to_monitor:
                workflow_status = self.check_workflow_for_commit(workflow_file, commit_sha)
                current_results[workflow_file] = workflow_status

                if workflow_status['status'] in ['pending', 'queued', 'in_progress']:
                    all_complete = False

            results = current_results

            if all_complete:
                print("All workflows completed!")
                break

            print(f"Waiting for workflows... ({int(time.time() - start_time)}s elapsed)")
            time.sleep(self.check_interval)

        return results

    def check_workflow_for_commit(self, workflow_file: str, commit_sha: str) -> Dict[str, Any]:
        """Check the status of a specific workflow for a commit"""
        try:
            # Get workflow ID first
            workflows_url = f"{self.base_url}/actions/workflows"
            workflows_response = self.session.get(workflows_url)

            if workflows_response.status_code != 200:
                return {
                    'status': 'unknown',
                    'conclusion': 'unknown',
                    'error': f'Failed to fetch workflows: {workflows_response.status_code}'
                }

            workflows = workflows_response.json().get('workflows', [])
            workflow_id = None

            for workflow in workflows:
                if workflow['path'].endswith(workflow_file):
                    workflow_id = workflow['id']
                    break

            if not workflow_id:
                return {
                    'status': 'missing',
                    'conclusion': 'not_found',
                    'error': f'Workflow {workflow_file} not found'
                }

            # Get runs for this workflow
            runs_url = f"{self.base_url}/actions/workflows/{workflow_id}/runs"
            params = {
                'head_sha': commit_sha,
                'per_page': 5
            }

            runs_response = self.session.get(runs_url, params=params)

            if runs_response.status_code != 200:
                return {
                    'status': 'unknown',
                    'conclusion': 'unknown',
                    'error': f'Failed to fetch runs: {runs_response.status_code}'
                }

            runs = runs_response.json().get('workflow_runs', [])

            if not runs:
                return {
                    'status': 'not_triggered',
                    'conclusion': 'not_found',
                    'error': f'No runs found for commit {commit_sha[:8]}'
                }

            latest_run = runs[0]
            return {
                'status': latest_run.get('status', 'unknown'),
                'conclusion': latest_run.get('conclusion'),
                'html_url': latest_run.get('html_url'),
                'created_at': latest_run.get('created_at'),
                'run_id': latest_run.get('id')
            }

        except Exception as e:
            return {
                'status': 'error',
                'conclusion': 'error',
                'error': str(e)
            }

    def generate_health_report(self, results: Dict[str, Any], output_file: str = "post-push-health.json"):
        """Generate a health report from monitoring results"""
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'commit_sha': self.get_latest_commit_sha(),
            'workflow_results': results,
            'overall_health': 'HEALTHY',
            'summary': {
                'total_workflows': len(results),
                'successful_workflows': 0,
                'failed_workflows': 0,
                'pending_workflows': 0,
                'missing_workflows': 0
            }
        }

        for workflow, status in results.items():
            if status['conclusion'] == 'success':
                report['summary']['successful_workflows'] += 1
            elif status['conclusion'] in ['failure', 'cancelled', 'timed_out']:
                report['summary']['failed_workflows'] += 1
                report['overall_health'] = 'FAILING'
            elif status['status'] in ['pending', 'queued', 'in_progress']:
                report['summary']['pending_workflows'] += 1
                if report['overall_health'] == 'HEALTHY':
                    report['overall_health'] = 'PENDING'
            elif status['status'] in ['missing', 'not_triggered', 'not_found']:
                report['summary']['missing_workflows'] += 1
                report['overall_health'] = 'FAILING'

        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Health report saved to {output_file}")
        return report

    def monitor_commit(self, commit_sha: Optional[str] = None, save_results: bool = False) -> Dict[str, Any]:
        """Monitor CI health for a specific commit"""
        if not commit_sha:
            commit_sha = self.get_latest_commit_sha()

        if not commit_sha:
            print("Error: Could not determine commit SHA")
            return {}

        print(f"Starting post-push monitoring for commit {commit_sha[:8]}")

        # Wait for workflows to complete
        results = self.wait_for_workflow_completion(commit_sha)

        # Generate report
        report = self.generate_health_report(results)

        # Save results if requested
        if save_results:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"ci-health-{commit_sha[:8]}-{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Results saved to {filename}")

        return report


def main():
    """Main CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description='Post-Push CI Health Monitor')
    parser.add_argument('--commit', help='Specific commit SHA to monitor')
    parser.add_argument('--save-results', action='store_true',
                       help='Save monitoring results to file')
    parser.add_argument('--timeout', type=int, default=1800,
                       help='Timeout in seconds (default: 1800)')

    args = parser.parse_args()

    monitor = PostPushCIMonitor()
    report = monitor.monitor_commit(
        commit_sha=args.commit,
        save_results=args.save_results
    )

    # Print summary
    print("\n" + "="*50)
    print("POST-PUSH CI HEALTH SUMMARY")
    print("="*50)
    print(f"Overall Health: {report.get('overall_health', 'UNKNOWN')}")
    print(f"Successful Workflows: {report.get('summary', {}).get('successful_workflows', 0)}")
    print(f"Failed Workflows: {report.get('summary', {}).get('failed_workflows', 0)}")
    print(f"Missing Workflows: {report.get('summary', {}).get('missing_workflows', 0)}")

    # Exit with error code if health is not good
    if report.get('overall_health') in ['FAILING', 'UNKNOWN']:
        sys.exit(1)
    elif report.get('overall_health') == 'PENDING':
        print("Warning: Some workflows still pending")
        sys.exit(2)


if __name__ == '__main__':
    main()