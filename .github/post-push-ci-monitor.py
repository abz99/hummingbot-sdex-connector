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

    def __init__(self, repo_owner: str = "abz99", repo_name: str = "hummingbot-sdex-connector"):
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
            'production-deploy.yml'
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
            print(f"❌ Error getting latest commit SHA: {e}")
        return None

    def wait_for_workflow_runs(self, commit_sha: str, timeout: int = 300) -> List[Dict]:
        """Wait for workflow runs to be triggered for the specified commit"""
        print(f"🔍 Waiting for workflow runs to start for commit {commit_sha[:8]}...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            runs = self.get_workflow_runs_for_commit(commit_sha)
            if runs:
                print(f"✅ Found {len(runs)} workflow runs")
                return runs

            print("⏳ Workflows not yet triggered, waiting...")
            time.sleep(self.check_interval)

        print("⚠️ Timeout waiting for workflows to start")
        return []

    def get_workflow_runs_for_commit(self, commit_sha: str) -> List[Dict]:
        """Get all workflow runs for a specific commit"""
        all_runs = []

        for workflow in self.workflows_to_monitor:
            try:
                url = f"{self.base_url}/actions/workflows/{workflow}/runs"
                params = {
                    'head_sha': commit_sha,
                    'per_page': 10
                }

                response = self.session.get(url, params=params)
                if response.status_code == 200:
                    runs = response.json().get('workflow_runs', [])
                    for run in runs:
                        run['workflow_file'] = workflow
                    all_runs.extend(runs)
                else:
                    print(f"⚠️ Failed to get runs for {workflow}: {response.status_code}")

            except Exception as e:
                print(f"❌ Error getting runs for {workflow}: {e}")

        return all_runs

    def monitor_workflow_completion(self, runs: List[Dict]) -> Dict[str, Any]:
        """Monitor workflow runs until completion"""
        print(f"📊 Monitoring {len(runs)} workflow runs...")

        monitoring_result = {
            'start_time': datetime.utcnow().isoformat(),
            'runs': {run['id']: {
                'workflow': run['workflow_file'],
                'status': run['status'],
                'conclusion': run.get('conclusion'),
                'url': run['html_url']
            } for run in runs},
            'final_status': 'monitoring',
            'completion_time': None
        }

        start_time = time.time()

        while time.time() - start_time < self.max_wait_time:
            all_completed = True

            for run in runs:
                run_id = run['id']
                current_status = self.get_run_status(run_id)

                if current_status:
                    monitoring_result['runs'][run_id].update(current_status)

                    if current_status['status'] != 'completed':
                        all_completed = False

                    # Print status update
                    workflow = monitoring_result['runs'][run_id]['workflow']
                    status = current_status['status']
                    conclusion = current_status.get('conclusion', 'running')

                    if status == 'completed':
                        if conclusion == 'success':
                            print(f"✅ {workflow}: {conclusion}")
                        else:
                            print(f"❌ {workflow}: {conclusion}")
                    else:
                        print(f"⏳ {workflow}: {status}")

            if all_completed:
                monitoring_result['final_status'] = 'completed'
                monitoring_result['completion_time'] = datetime.utcnow().isoformat()
                break

            time.sleep(self.check_interval)

        if monitoring_result['final_status'] != 'completed':
            monitoring_result['final_status'] = 'timeout'
            monitoring_result['completion_time'] = datetime.utcnow().isoformat()

        return monitoring_result

    def get_run_status(self, run_id: int) -> Optional[Dict]:
        """Get current status of a workflow run"""
        try:
            url = f"{self.base_url}/actions/runs/{run_id}"
            response = self.session.get(url)

            if response.status_code == 200:
                run_data = response.json()
                return {
                    'status': run_data.get('status'),
                    'conclusion': run_data.get('conclusion'),
                    'created_at': run_data.get('created_at'),
                    'updated_at': run_data.get('updated_at')
                }
        except Exception as e:
            print(f"❌ Error getting run status for {run_id}: {e}")

        return None

    def analyze_results(self, monitoring_result: Dict) -> Dict[str, Any]:
        """Analyze monitoring results and generate health report"""
        analysis = {
            'overall_health': 'healthy',
            'successful_workflows': 0,
            'failed_workflows': 0,
            'issues': [],
            'recommendations': []
        }

        for run_id, run_data in monitoring_result['runs'].items():
            workflow = run_data['workflow']
            conclusion = run_data.get('conclusion')

            if conclusion == 'success':
                analysis['successful_workflows'] += 1
            elif conclusion in ['failure', 'cancelled', 'timed_out']:
                analysis['failed_workflows'] += 1
                analysis['issues'].append(f"{workflow} failed with: {conclusion}")
                analysis['overall_health'] = 'degraded'

        # Generate recommendations
        if analysis['failed_workflows'] > 0:
            analysis['recommendations'].extend([
                "Review failed workflow logs in GitHub Actions",
                "Check if dependencies in requirements-dev.txt are properly installed",
                "Verify all required secrets are configured in repository settings",
                "Run local tests before pushing: pytest tests/ -v"
            ])

        if monitoring_result['final_status'] == 'timeout':
            analysis['issues'].append("Some workflows did not complete within timeout period")
            analysis['recommendations'].append("Consider increasing workflow timeout limits")
            analysis['overall_health'] = 'degraded'

        return analysis

    def generate_health_report(self, monitoring_result: Dict, analysis: Dict) -> str:
        """Generate comprehensive post-push health report"""
        report = f"""
# Post-Push CI Health Report
**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Repository**: {self.repo_owner}/{self.repo_name}

## Overall Status: {analysis['overall_health'].upper()}

## Monitoring Summary
- **Start Time**: {monitoring_result['start_time']}
- **Completion Time**: {monitoring_result.get('completion_time', 'N/A')}
- **Final Status**: {monitoring_result['final_status']}

## Workflow Results
"""

        for run_id, run_data in monitoring_result['runs'].items():
            workflow = run_data['workflow']
            conclusion = run_data.get('conclusion', 'unknown')
            status_icon = "✅" if conclusion == 'success' else "❌" if conclusion in ['failure', 'cancelled', 'timed_out'] else "⏳"

            report += f"- **{workflow}**: {status_icon} {conclusion}\n"

        report += f"""
## Statistics
- **Successful Workflows**: {analysis['successful_workflows']}
- **Failed Workflows**: {analysis['failed_workflows']}
- **Total Monitored**: {len(monitoring_result['runs'])}
"""

        if analysis['issues']:
            report += "\n## Issues Detected\n"
            for issue in analysis['issues']:
                report += f"- ❌ {issue}\n"

        if analysis['recommendations']:
            report += "\n## Recommendations\n"
            for rec in analysis['recommendations']:
                report += f"- 💡 {rec}\n"

        return report

    def run_post_push_monitoring(self, commit_sha: Optional[str] = None) -> Dict[str, Any]:
        """Run complete post-push monitoring cycle"""
        print("🚀 Starting post-push CI monitoring...")

        # Get commit SHA if not provided
        if not commit_sha:
            commit_sha = self.get_latest_commit_sha()
            if not commit_sha:
                return {'error': 'Could not determine commit SHA'}

        print(f"📍 Monitoring commit: {commit_sha[:8]}")

        # Wait for workflows to be triggered
        runs = self.wait_for_workflow_runs(commit_sha)
        if not runs:
            return {
                'error': 'No workflow runs found for commit',
                'commit_sha': commit_sha
            }

        # Monitor workflow completion
        monitoring_result = self.monitor_workflow_completion(runs)

        # Analyze results
        analysis = self.analyze_results(monitoring_result)

        # Generate report
        report = self.generate_health_report(monitoring_result, analysis)

        return {
            'commit_sha': commit_sha,
            'monitoring_result': monitoring_result,
            'analysis': analysis,
            'report': report,
            'success': analysis['overall_health'] in ['healthy', 'degraded']
        }

def save_monitoring_results(results: Dict, output_dir: str = "logs"):
    """Save monitoring results to files"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    # Save detailed results as JSON
    json_file = output_path / f"ci_monitoring_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Save report as markdown
    if 'report' in results:
        report_file = output_path / f"ci_health_report_{timestamp}.md"
        with open(report_file, 'w') as f:
            f.write(results['report'])

    print(f"📁 Results saved:")
    print(f"   - JSON: {json_file}")
    print(f"   - Report: {report_file}")

def main():
    """Main entry point for post-push CI monitoring"""
    import argparse

    parser = argparse.ArgumentParser(description='Post-push CI health monitoring')
    parser.add_argument('--commit', help='Specific commit SHA to monitor')
    parser.add_argument('--save-results', action='store_true',
                       help='Save monitoring results to files')
    parser.add_argument('--timeout', type=int, default=1800,
                       help='Maximum wait time in seconds (default: 1800)')

    args = parser.parse_args()

    # Initialize monitor
    monitor = PostPushCIMonitor()
    monitor.max_wait_time = args.timeout

    # Run monitoring
    results = monitor.run_post_push_monitoring(args.commit)

    if 'error' in results:
        print(f"❌ Monitoring failed: {results['error']}")
        sys.exit(1)

    # Print report
    print(results['report'])

    # Save results if requested
    if args.save_results:
        save_monitoring_results(results)

    # Exit with appropriate code
    if results['analysis']['overall_health'] == 'healthy':
        print("\n✅ All CI workflows completed successfully!")
        sys.exit(0)
    else:
        print(f"\n⚠️ CI health status: {results['analysis']['overall_health']}")
        sys.exit(1)

if __name__ == "__main__":
    main()