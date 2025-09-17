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

    def __init__(self, repo_owner: str, repo_name: str, github_token: Optional[str] = None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
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
            url = f"{self.base_url}/actions/workflows/{workflow_name}/runs"
            params = {
                'branch': branch,
                'per_page': limit,
                'sort': 'created',
                'order': 'desc'
            }

            response = self.session.get(url, params=params)
            response.raise_for_status()

            return response.json().get('workflow_runs', [])

        except Exception as e:
            print(f"❌ Error checking workflow runs for {workflow_name}: {e}")
            return []

    def get_workflow_run_details(self, run_id: int) -> Dict:
        """Get detailed information about a specific workflow run"""
        try:
            url = f"{self.base_url}/actions/runs/{run_id}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting workflow run details for {run_id}: {e}")
            return {}

    def get_workflow_run_jobs(self, run_id: int) -> List[Dict]:
        """Get jobs for a specific workflow run"""
        try:
            url = f"{self.base_url}/actions/runs/{run_id}/jobs"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json().get('jobs', [])
        except Exception as e:
            print(f"❌ Error getting workflow jobs for {run_id}: {e}")
            return []

    def analyze_ci_health(self) -> Dict[str, Any]:
        """Analyze overall CI pipeline health"""
        workflows = ['ci.yml', 'knowledge-base-ci.yml', 'production-deploy.yml']

        health_report = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'workflows': {},
            'issues': [],
            'recommendations': []
        }

        for workflow in workflows:
            print(f"🔍 Analyzing {workflow}...")
            runs = self.check_workflow_runs(workflow)

            if not runs:
                health_report['workflows'][workflow] = {
                    'status': 'no_runs',
                    'last_run': None,
                    'success_rate': 0.0
                }
                health_report['issues'].append(f"No recent runs found for {workflow}")
                continue

            # Calculate success rate
            successful_runs = sum(1 for run in runs if run['conclusion'] == 'success')
            success_rate = successful_runs / len(runs) * 100

            latest_run = runs[0]
            workflow_health = {
                'status': latest_run['conclusion'],
                'last_run': latest_run['created_at'],
                'success_rate': success_rate,
                'recent_runs': len(runs),
                'latest_run_id': latest_run['id']
            }

            health_report['workflows'][workflow] = workflow_health

            # Analyze issues
            if success_rate < 80:
                health_report['issues'].append(f"{workflow} has low success rate: {success_rate:.1f}%")
                health_report['overall_status'] = 'degraded'

            if latest_run['conclusion'] in ['failure', 'cancelled', 'timed_out']:
                health_report['issues'].append(f"{workflow} latest run failed: {latest_run['conclusion']}")
                health_report['overall_status'] = 'failing'

        return health_report

    def diagnose_workflow_failures(self, workflow_name: str) -> Dict[str, Any]:
        """Diagnose specific failures in a workflow"""
        print(f"🔬 Diagnosing failures in {workflow_name}...")

        runs = self.check_workflow_runs(workflow_name, limit=5)
        failed_runs = [run for run in runs if run['conclusion'] in ['failure', 'cancelled', 'timed_out']]

        if not failed_runs:
            return {'status': 'healthy', 'message': 'No recent failures found'}

        # Analyze most recent failure
        latest_failure = failed_runs[0]
        jobs = self.get_workflow_run_jobs(latest_failure['id'])

        failure_analysis = {
            'workflow': workflow_name,
            'run_id': latest_failure['id'],
            'conclusion': latest_failure['conclusion'],
            'created_at': latest_failure['created_at'],
            'failed_jobs': [],
            'common_issues': []
        }

        for job in jobs:
            if job['conclusion'] in ['failure', 'cancelled', 'timed_out']:
                failure_analysis['failed_jobs'].append({
                    'name': job['name'],
                    'conclusion': job['conclusion'],
                    'started_at': job['started_at'],
                    'completed_at': job['completed_at']
                })

        # Identify common failure patterns
        failure_analysis['common_issues'] = self._identify_common_issues(jobs)

        return failure_analysis

    def _identify_common_issues(self, jobs: List[Dict]) -> List[str]:
        """Identify common CI failure patterns"""
        issues = []

        for job in jobs:
            job_name = job['name'].lower()
            conclusion = job['conclusion']

            if conclusion == 'failure':
                if 'security' in job_name:
                    issues.append("Security scanning tools may not be installed or configured properly")
                elif 'test' in job_name:
                    issues.append("Test execution failures - check test environment setup")
                elif 'build' in job_name:
                    issues.append("Build failures - check dependencies and package configuration")
                elif 'deploy' in job_name:
                    issues.append("Deployment failures - check secrets and infrastructure configuration")

            elif conclusion == 'cancelled':
                issues.append("Jobs being cancelled - may indicate timeout or resource issues")

            elif conclusion == 'timed_out':
                issues.append("Jobs timing out - increase timeout or optimize performance")

        return list(set(issues))  # Remove duplicates

    def validate_local_environment(self) -> Dict[str, Any]:
        """Validate local environment matches CI requirements"""
        print("🔧 Validating local environment...")

        validation_results = {
            'python_version': self._check_python_version(),
            'dependencies': self._check_dependencies(),
            'test_structure': self._check_test_structure(),
            'scripts': self._check_required_scripts(),
            'docker_files': self._check_docker_files(),
            'github_workflows': self._check_workflow_files()
        }

        return validation_results

    def _check_python_version(self) -> Dict[str, Any]:
        """Check Python version compatibility"""
        try:
            result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True)
            version = result.stdout.strip()

            # Extract version number
            version_parts = version.split()[1].split('.')
            major, minor = int(version_parts[0]), int(version_parts[1])

            return {
                'status': 'pass' if (major == 3 and minor >= 9) else 'fail',
                'version': version,
                'required': 'Python 3.9+'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def _check_dependencies(self) -> Dict[str, Any]:
        """Check if required dependencies are available"""
        dependencies = ['pytest', 'flake8', 'black', 'mypy', 'safety', 'bandit']
        results = {}

        for dep in dependencies:
            try:
                result = subprocess.run([sys.executable, '-m', dep, '--version'],
                                      capture_output=True, text=True)
                results[dep] = {
                    'status': 'pass' if result.returncode == 0 else 'fail',
                    'version': result.stdout.strip().split('\n')[0] if result.returncode == 0 else 'not_found'
                }
            except Exception:
                results[dep] = {'status': 'fail', 'version': 'not_found'}

        return results

    def _check_test_structure(self) -> Dict[str, Any]:
        """Check test directory structure"""
        test_dirs = ['tests/unit', 'tests/integration', 'tests/security', 'tests/performance']
        results = {}

        for test_dir in test_dirs:
            path = Path(test_dir)
            results[test_dir] = {
                'exists': path.exists(),
                'test_files': len(list(path.glob('test_*.py'))) if path.exists() else 0
            }

        return results

    def _check_required_scripts(self) -> Dict[str, Any]:
        """Check if required scripts exist"""
        required_scripts = [
            'scripts/check_sdk_compatibility.py',
            'scripts/check_critical_coverage.py',
            'scripts/validate_knowledge_base_config.py',
            'scripts/knowledge_base_indexer.py'
        ]

        results = {}
        for script in required_scripts:
            path = Path(script)
            results[script] = {
                'exists': path.exists(),
                'executable': path.is_file() and os.access(path, os.X_OK) if path.exists() else False
            }

        return results

    def _check_docker_files(self) -> Dict[str, Any]:
        """Check Docker configuration files"""
        docker_files = [
            'deployment/docker/Dockerfile.production',
            'deployment/kubernetes/deployment-production.yaml'
        ]

        results = {}
        for docker_file in docker_files:
            path = Path(docker_file)
            results[docker_file] = {'exists': path.exists()}

        return results

    def _check_workflow_files(self) -> Dict[str, Any]:
        """Check GitHub workflow configuration"""
        workflow_files = [
            '.github/workflows/ci.yml',
            '.github/workflows/knowledge-base-ci.yml',
            '.github/workflows/production-deploy.yml'
        ]

        results = {}
        for workflow_file in workflow_files:
            path = Path(workflow_file)
            results[workflow_file] = {'exists': path.exists()}

        return results

    def generate_ci_health_report(self) -> str:
        """Generate comprehensive CI health report"""
        print("📊 Generating CI health report...")

        # Analyze CI health
        ci_health = self.analyze_ci_health()

        # Validate local environment
        local_validation = self.validate_local_environment()

        # Generate workflow-specific diagnostics
        workflow_diagnostics = {}
        for workflow in ['ci.yml', 'knowledge-base-ci.yml', 'production-deploy.yml']:
            workflow_diagnostics[workflow] = self.diagnose_workflow_failures(workflow)

        # Create comprehensive report
        report = f"""
# GitHub CI Pipeline Health Report
**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Repository**: {self.repo_owner}/{self.repo_name}

## Overall Status: {ci_health['overall_status'].upper()}

## Workflow Status
"""

        for workflow, status in ci_health['workflows'].items():
            report += f"""
### {workflow}
- **Status**: {status['status']}
- **Success Rate**: {status['success_rate']:.1f}%
- **Last Run**: {status['last_run']}
"""

        if ci_health['issues']:
            report += "\n## Issues Identified\n"
            for issue in ci_health['issues']:
                report += f"- ❌ {issue}\n"

        report += "\n## Local Environment Validation\n"

        # Python version
        py_status = local_validation['python_version']
        report += f"- **Python**: {py_status['status'].upper()} - {py_status.get('version', 'unknown')}\n"

        # Dependencies
        dep_results = local_validation['dependencies']
        missing_deps = [dep for dep, result in dep_results.items() if result['status'] == 'fail']
        if missing_deps:
            report += f"- **Missing Dependencies**: {', '.join(missing_deps)}\n"
        else:
            report += "- **Dependencies**: ✅ All required tools available\n"

        # Test structure
        test_results = local_validation['test_structure']
        for test_dir, result in test_results.items():
            status = "✅" if result['exists'] else "❌"
            report += f"- **{test_dir}**: {status} ({result['test_files']} test files)\n"

        report += "\n## Recommendations\n"

        # Add specific recommendations based on findings
        if missing_deps:
            report += f"1. Install missing dependencies: `pip install {' '.join(missing_deps)}`\n"

        if any(not result['exists'] for result in local_validation['test_structure'].values()):
            report += "2. Ensure all test directories exist and contain test files\n"

        if ci_health['overall_status'] == 'failing':
            report += "3. Review recent workflow run logs in GitHub Actions\n"
            report += "4. Check GitHub repository secrets are properly configured\n"

        report += "5. Run local tests before pushing: `pytest tests/ -v`\n"
        report += "6. Validate code quality: `flake8 . && black --check . && mypy .`\n"

        return report


def main():
    """Main entry point for CI monitoring"""
    import argparse

    parser = argparse.ArgumentParser(description='Monitor GitHub CI pipeline health')
    parser.add_argument('--repo', default='hummingbot-sdex-connector',
                       help='Repository name')
    parser.add_argument('--owner', default='abz99',
                       help='Repository owner')
    parser.add_argument('--token',
                       help='GitHub token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--output', '-o',
                       help='Output file for health report')
    parser.add_argument('--workflow',
                       help='Analyze specific workflow only')

    args = parser.parse_args()

    # Initialize monitor
    monitor = GitHubCIMonitor(args.owner, args.repo, args.token)

    if args.workflow:
        # Analyze specific workflow
        diagnosis = monitor.diagnose_workflow_failures(args.workflow)
        print(json.dumps(diagnosis, indent=2))
    else:
        # Generate full health report
        report = monitor.generate_ci_health_report()

        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"✅ Health report saved to {args.output}")
        else:
            print(report)


if __name__ == "__main__":
    main()