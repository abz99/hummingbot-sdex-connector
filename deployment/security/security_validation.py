#!/usr/bin/env python3
"""
Production Security Validation Suite
Stellar Hummingbot Connector v3.0

Validates production security configurations before deployment.
"""

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import yaml
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SecurityCheckResult:
    """Security check result"""
    check_name: str
    passed: bool
    details: str
    severity: str  # critical, high, medium, low
    remediation: Optional[str] = None

class ProductionSecurityValidator:
    """Comprehensive production security validation"""
    
    def __init__(self, deployment_path: Path):
        self.deployment_path = deployment_path
        self.results: List[SecurityCheckResult] = []
        
    async def validate_all(self) -> Dict[str, any]:
        """Run all security validations"""
        logger.info("Starting comprehensive security validation...")
        
        # Kubernetes security validation
        await self.validate_kubernetes_security()
        
        # Container security validation
        await self.validate_container_security()
        
        # Secret management validation
        await self.validate_secret_management()
        
        # Network security validation
        await self.validate_network_security()
        
        # RBAC validation
        await self.validate_rbac()
        
        # Pod security validation
        await self.validate_pod_security()
        
        # Monitoring security validation
        await self.validate_monitoring_security()
        
        return self._generate_report()
        
    async def validate_kubernetes_security(self):
        """Validate Kubernetes security configurations"""
        logger.info("Validating Kubernetes security configurations...")
        
        # Check namespace isolation
        namespace_file = self.deployment_path / "kubernetes" / "namespace.yaml"
        if namespace_file.exists():
            # Check resource quotas
            resource_quota_found = any(
                doc.get("kind") == "ResourceQuota" 
                for doc in yaml.safe_load_all(namespace_file.read_text())
            )
            
            self.results.append(SecurityCheckResult(
                check_name="namespace_resource_quotas",
                passed=resource_quota_found,
                details="ResourceQuota configured for namespace isolation" if resource_quota_found else "Missing ResourceQuota",
                severity="high" if not resource_quota_found else "low"
            ))
            
            # Check network policies
            network_policy_found = any(
                doc.get("kind") == "NetworkPolicy"
                for doc in yaml.safe_load_all(namespace_file.read_text())
            )
            
            self.results.append(SecurityCheckResult(
                check_name="namespace_network_policies",
                passed=network_policy_found,
                details="NetworkPolicy configured for network isolation" if network_policy_found else "Missing NetworkPolicy",
                severity="critical" if not network_policy_found else "low"
            ))
        
    async def validate_container_security(self):
        """Validate container security configurations"""
        logger.info("Validating container security...")
        
        # Check Dockerfile security
        dockerfile_path = self.deployment_path / "docker" / "Dockerfile.production"
        if dockerfile_path.exists():
            dockerfile_content = dockerfile_path.read_text()
            
            # Check for non-root user
            user_lines = [line for line in dockerfile_content.split('\n') if line.strip().startswith('USER ')]
            non_root_user = len(user_lines) > 0 and all('root' not in line and '0' not in line for line in user_lines)
            self.results.append(SecurityCheckResult(
                check_name="container_non_root_user",
                passed=non_root_user,
                details="Container runs as non-root user" if non_root_user else "Container may run as root",
                severity="critical" if not non_root_user else "low"
            ))
            
            # Check for health checks
            health_check = "HEALTHCHECK" in dockerfile_content
            self.results.append(SecurityCheckResult(
                check_name="container_health_checks",
                passed=health_check,
                details="Health checks configured" if health_check else "Missing health checks",
                severity="medium" if not health_check else "low"
            ))
            
            # Check for minimal base image
            slim_image = "slim" in dockerfile_content.lower() or "alpine" in dockerfile_content.lower()
            self.results.append(SecurityCheckResult(
                check_name="container_minimal_image",
                passed=slim_image,
                details="Using minimal base image" if slim_image else "Consider using minimal base image",
                severity="low"
            ))
            
    async def validate_secret_management(self):
        """Validate secret management configurations"""
        logger.info("Validating secret management...")
        
        secrets_file = self.deployment_path / "security" / "secrets.yaml"
        if secrets_file.exists():
            secrets_config = list(yaml.safe_load_all(secrets_file.read_text()))
                
            # Check for external secrets operator
            external_secret_found = any(
                doc.get("kind") == "ExternalSecret"
                for doc in secrets_config
            )
            
            self.results.append(SecurityCheckResult(
                check_name="external_secret_management",
                passed=external_secret_found,
                details="External Secrets Operator configured" if external_secret_found else "Missing external secret management",
                severity="critical" if not external_secret_found else "low"
            ))
            
            # Check for hardcoded secrets (excluding legitimate external references)
            secrets_content = secrets_file.read_text()
            hardcoded_secrets = []
            
            for line in secrets_content.split('\n'):
                line = line.strip()
                # Skip comments, empty lines, and legitimate external references
                if (line.startswith('#') or not line or 
                    '""' in line or 
                    'Managed externally' in line or
                    'remoteRef:' in line or
                    'property:' in line or
                    'key:' in line or
                    'secretKey:' in line or  # These are key names, not values
                    'name:' in line or  # These are resource names, not secrets
                    line.startswith('apiVersion:') or
                    line.startswith('kind:') or
                    line.startswith('metadata:') or
                    line.startswith('spec:') or
                    line.startswith('data:') or
                    line.startswith('  - ') or  # List items in external secrets
                    'external-secrets.io/' in line or  # Annotations, not secrets
                    '---' in line):
                    continue
                    
                # Look for actual hardcoded values
                if ':' in line and any(keyword in line.lower() for keyword in ['password', 'key', 'token', 'secret']):
                    value_part = line.split(':', 1)[1].strip()
                    # Check if it's a non-empty value that's not a placeholder
                    if (value_part and 
                        value_part != '""' and 
                        not value_part.startswith('${') and
                        'base64' not in value_part.lower() and
                        len(value_part) > 10):  # Actual secrets tend to be longer
                        hardcoded_secrets.append(line)
            
            self.results.append(SecurityCheckResult(
                check_name="no_hardcoded_secrets",
                passed=len(hardcoded_secrets) == 0,
                details=f"No hardcoded secrets found" if len(hardcoded_secrets) == 0 else f"Found {len(hardcoded_secrets)} potential hardcoded secrets",
                severity="critical" if len(hardcoded_secrets) > 0 else "low"
            ))
            
    async def validate_network_security(self):
        """Validate network security configurations"""
        logger.info("Validating network security...")
        
        # Check service configurations
        service_files = list((self.deployment_path / "kubernetes").glob("*service*.yaml"))
        service_files.extend(list((self.deployment_path / "monitoring").glob("*service*.yaml")))
        
        for service_file in service_files:
            if service_file.exists():
                service_docs = list(yaml.safe_load_all(service_file.read_text()))
                    
                for doc in service_docs:
                    if doc and doc.get("kind") == "Service":
                        service_type = doc.get("spec", {}).get("type", "ClusterIP")
                        
                        # Check for secure service types
                        secure_service = service_type in ["ClusterIP", "NodePort"]
                        self.results.append(SecurityCheckResult(
                            check_name=f"service_security_{service_file.stem}",
                            passed=secure_service,
                            details=f"Service type: {service_type}" + (" (secure)" if secure_service else " (review required)"),
                            severity="medium" if not secure_service else "low"
                        ))
                        
    async def validate_rbac(self):
        """Validate RBAC configurations"""
        logger.info("Validating RBAC...")
        
        # Check for ServiceAccount, Role, RoleBinding
        rbac_files = list((self.deployment_path / "kubernetes").glob("*rbac*.yaml"))
        rbac_files.extend(list((self.deployment_path / "kubernetes").glob("*service-account*.yaml")))
        
        rbac_components = {"ServiceAccount": False, "Role": False, "RoleBinding": False}
        
        for rbac_file in rbac_files:
            if rbac_file.exists():
                rbac_docs = list(yaml.safe_load_all(rbac_file.read_text()))
                    
                for doc in rbac_docs:
                    if doc and doc.get("kind") in rbac_components:
                        rbac_components[doc["kind"]] = True
                        
        for component, found in rbac_components.items():
            self.results.append(SecurityCheckResult(
                check_name=f"rbac_{component.lower()}",
                passed=found,
                details=f"{component} configured" if found else f"Missing {component}",
                severity="high" if not found else "low"
            ))
            
    async def validate_pod_security(self):
        """Validate Pod Security configurations"""
        logger.info("Validating Pod Security...")
        
        # Check deployment security contexts
        deployment_files = list((self.deployment_path / "kubernetes").glob("*deployment*.yaml"))
        deployment_files.extend(list((self.deployment_path / "monitoring").glob("*deployment*.yaml")))
        
        for deployment_file in deployment_files:
            if deployment_file.exists():
                deployment_docs = list(yaml.safe_load_all(deployment_file.read_text()))
                    
                for doc in deployment_docs:
                    if doc and doc.get("kind") == "Deployment":
                        spec = doc.get("spec", {})
                        template = spec.get("template", {})
                        pod_spec = template.get("spec", {})
                        
                        # Check security context
                        security_context = pod_spec.get("securityContext", {})
                        
                        run_as_non_root = security_context.get("runAsNonRoot", False)
                        run_as_user = security_context.get("runAsUser", 0)
                        self.results.append(SecurityCheckResult(
                            check_name=f"pod_security_non_root_{deployment_file.stem}",
                            passed=run_as_non_root and run_as_user > 0,
                            details=f"Pod runs as non-root: {run_as_non_root}, User ID: {run_as_user}",
                            severity="critical" if not (run_as_non_root and run_as_user > 0) else "low"
                        ))
                        
                        # Check for security capabilities
                        containers = pod_spec.get("containers", [])
                        for container in containers:
                            container_security = container.get("securityContext", {})
                            allow_privilege_escalation = container_security.get("allowPrivilegeEscalation", True)
                            container_run_as_non_root = container_security.get("runAsNonRoot", False)
                            container_run_as_user = container_security.get("runAsUser", 0)
                            
                            self.results.append(SecurityCheckResult(
                                check_name=f"container_privilege_escalation_{container.get('name', 'unknown')}",
                                passed=not allow_privilege_escalation,
                                details=f"Privilege escalation allowed: {allow_privilege_escalation}",
                                severity="high" if allow_privilege_escalation else "low"
                            ))
                            
                            # Check container-level non-root configuration
                            self.results.append(SecurityCheckResult(
                                check_name=f"container_non_root_{container.get('name', 'unknown')}",
                                passed=container_run_as_non_root and container_run_as_user > 0,
                                details=f"Container runs as non-root: {container_run_as_non_root}, User ID: {container_run_as_user}",
                                severity="critical" if not (container_run_as_non_root and container_run_as_user > 0) else "low"
                            ))
                            
    async def validate_monitoring_security(self):
        """Validate monitoring security configurations"""
        logger.info("Validating monitoring security...")
        
        # Check Prometheus security
        prometheus_file = self.deployment_path / "monitoring" / "prometheus.yaml"
        if prometheus_file.exists():
            prometheus_docs = list(yaml.safe_load_all(prometheus_file.read_text()))
                
            # Check for authentication
            auth_configured = False
            for doc in prometheus_docs:
                if doc and doc.get("kind") == "Secret":
                    if "auth" in doc.get("metadata", {}).get("name", "").lower():
                        auth_configured = True
                        
            self.results.append(SecurityCheckResult(
                check_name="prometheus_authentication",
                passed=auth_configured,
                details="Authentication configured for Prometheus" if auth_configured else "Missing authentication for Prometheus",
                severity="medium" if not auth_configured else "low"
            ))
            
        # Check Grafana security
        grafana_file = self.deployment_path / "monitoring" / "grafana.yaml"
        if grafana_file.exists():
            grafana_content = grafana_file.read_text()
            
            # Check for default password
            default_password = "admin123" in grafana_content
            self.results.append(SecurityCheckResult(
                check_name="grafana_default_password",
                passed=not default_password,
                details="Using default password" if default_password else "Custom password configured",
                severity="critical" if default_password else "low",
                remediation="Change default Grafana password in production" if default_password else None
            ))
            
    def _generate_report(self) -> Dict[str, any]:
        """Generate comprehensive security report"""
        
        # Categorize results by severity
        critical = [r for r in self.results if r.severity == "critical" and not r.passed]
        high = [r for r in self.results if r.severity == "high" and not r.passed]
        medium = [r for r in self.results if r.severity == "medium" and not r.passed]
        low = [r for r in self.results if r.severity == "low" and not r.passed]
        
        passed_count = len([r for r in self.results if r.passed])
        total_count = len(self.results)
        
        report = {
            "summary": {
                "total_checks": total_count,
                "passed": passed_count,
                "failed": total_count - passed_count,
                "success_rate": f"{(passed_count / total_count * 100):.1f}%" if total_count > 0 else "0%"
            },
            "severity_breakdown": {
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium),
                "low": len(low)
            },
            "failed_checks": {
                "critical": [{"name": r.check_name, "details": r.details, "remediation": r.remediation} for r in critical],
                "high": [{"name": r.check_name, "details": r.details, "remediation": r.remediation} for r in high],
                "medium": [{"name": r.check_name, "details": r.details, "remediation": r.remediation} for r in medium],
                "low": [{"name": r.check_name, "details": r.details, "remediation": r.remediation} for r in low]
            },
            "deployment_readiness": {
                "ready_for_staging": len(critical) == 0 and len(high) <= 2,
                "ready_for_production": len(critical) == 0 and len(high) == 0 and len(medium) <= 1,
                "recommendations": self._get_recommendations(critical, high, medium)
            }
        }
        
        return report
        
    def _get_recommendations(self, critical: List, high: List, medium: List) -> List[str]:
        """Get deployment recommendations based on security findings"""
        recommendations = []
        
        if len(critical) > 0:
            recommendations.append("❌ CRITICAL ISSUES FOUND - DO NOT DEPLOY TO PRODUCTION")
            recommendations.append("Fix all critical security issues before proceeding")
            
        if len(high) > 0:
            recommendations.append("⚠️ High severity issues detected - address before production deployment")
            
        if len(medium) > 2:
            recommendations.append("📋 Multiple medium severity issues - consider addressing for enhanced security")
            
        if len(critical) == 0 and len(high) <= 1:
            recommendations.append("✅ Security validation passed - ready for staging deployment")
            
        if len(critical) == 0 and len(high) == 0:
            recommendations.append("🚀 Excellent security posture - ready for production deployment")
            
        return recommendations


async def main():
    """Main execution function"""
    deployment_path = Path(__file__).parent.parent
    
    validator = ProductionSecurityValidator(deployment_path)
    report = await validator.validate_all()
    
    # Print results
    print("\n" + "="*80)
    print("🔒 PRODUCTION SECURITY VALIDATION REPORT")
    print("="*80)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total Checks: {report['summary']['total_checks']}")
    print(f"   Passed: {report['summary']['passed']}")
    print(f"   Failed: {report['summary']['failed']}")
    print(f"   Success Rate: {report['summary']['success_rate']}")
    
    print(f"\n📈 SEVERITY BREAKDOWN:")
    for severity, count in report['severity_breakdown'].items():
        if count > 0:
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[severity]
            print(f"   {emoji} {severity.upper()}: {count}")
    
    if report['failed_checks']['critical']:
        print(f"\n🔴 CRITICAL ISSUES:")
        for issue in report['failed_checks']['critical']:
            print(f"   • {issue['name']}: {issue['details']}")
            if issue['remediation']:
                print(f"     💡 {issue['remediation']}")
    
    if report['failed_checks']['high']:
        print(f"\n🟠 HIGH SEVERITY ISSUES:")
        for issue in report['failed_checks']['high']:
            print(f"   • {issue['name']}: {issue['details']}")
    
    print(f"\n🎯 DEPLOYMENT READINESS:")
    print(f"   Staging Ready: {'✅ Yes' if report['deployment_readiness']['ready_for_staging'] else '❌ No'}")
    print(f"   Production Ready: {'✅ Yes' if report['deployment_readiness']['ready_for_production'] else '❌ No'}")
    
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in report['deployment_readiness']['recommendations']:
        print(f"   {rec}")
    
    # Save detailed report
    report_file = deployment_path / "security" / "security_validation_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
        
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Exit with appropriate code
    if report['deployment_readiness']['ready_for_staging']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())