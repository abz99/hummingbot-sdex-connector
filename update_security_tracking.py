#!/usr/bin/env python3
"""
Automated Security Requirements Tracking Updater
Updates PROJECT_STATUS.md with current security requirements status.
"""

import os
import re
import sys
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from hummingbot.connector.exchange.stellar.stellar_security_metrics import (
    get_security_tracker,
    SecurityRequirementsTracker,
    RequirementStatus,
    RequirementPriority
)


class SecurityTrackingUpdater:
    """Updates PROJECT_STATUS.md with current security tracking information."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.project_status_file = project_root / "PROJECT_STATUS.md"
        self.tracker = get_security_tracker()
    
    def update_project_status(self, dry_run: bool = False) -> bool:
        """Update PROJECT_STATUS.md with current security metrics."""
        if not self.project_status_file.exists():
            print(f"❌ PROJECT_STATUS.md not found at {self.project_status_file}")
            return False
        
        # Read current file
        with open(self.project_status_file, 'r') as f:
            content = f.read()
        
        # Generate new security section
        new_security_section = self.tracker.export_project_status_section()
        
        # Find existing security section and replace it
        security_section_pattern = r'### 🔒 SECURITY REQUIREMENTS TRACKING.*?(?=### |\n## |\Z)'
        
        if re.search(security_section_pattern, content, re.DOTALL):
            # Replace existing section
            updated_content = re.sub(
                security_section_pattern,
                new_security_section + '\n\n',
                content,
                flags=re.DOTALL
            )
        else:
            # Add new section after quality metrics
            quality_metrics_pattern = r'(### 📈 QUALITY METRICS.*?)(\n\n### )'
            if re.search(quality_metrics_pattern, content, re.DOTALL):
                updated_content = re.sub(
                    quality_metrics_pattern,
                    r'\1\n\n' + new_security_section + r'\2',
                    content,
                    flags=re.DOTALL
                )
            else:
                print("⚠️  Could not find insertion point for security section")
                return False
        
        if dry_run:
            print("🔍 DRY RUN - Would update PROJECT_STATUS.md with:")
            print("=" * 60)
            print(new_security_section)
            print("=" * 60)
            return True
        
        # Write updated content
        with open(self.project_status_file, 'w') as f:
            f.write(updated_content)
        
        print(f"✅ Updated PROJECT_STATUS.md with current security metrics")
        return True
    
    def show_security_summary(self):
        """Display current security status summary."""
        report = self.tracker.generate_status_report()
        
        print("\n🔒 SECURITY REQUIREMENTS SUMMARY")
        print("=" * 50)
        
        print(f"Overall Security Score: {report['overall_security_score']:.1f}/100")
        
        summary = report['requirement_summary']
        print(f"Requirements: {summary['completed']}/{summary['total']} Complete")
        print(f"In Progress: {summary['in_progress']}")
        print(f"Not Started: {summary['not_started']}")
        print(f"Overdue: {summary['overdue']}")
        
        print("\nCompletion Rates by Priority:")
        rates = report['completion_rates']
        print(f"  Critical (P0): {rates['critical']:.0f}%")
        print(f"  High (P1): {rates['high']:.0f}%")
        print(f"  Medium (P2): {rates['medium']:.0f}%")
        print(f"  Regulatory: {rates['regulatory']:.0f}%")
        
        print("\nOperational Metrics:")
        ops = report['operational_metrics']
        print(f"  Security Incidents: {ops['security_incidents']}")
        print(f"  Vulnerability Response Time: {ops['vulnerability_response_time_days']:.1f} days")
        print(f"  HSM Success Rate: {ops['hsm_success_rate']:.1f}%")
        print(f"  Auth Failure Rate: {ops['auth_failure_rate']:.1f}%")
        
        if report['overdue_requirements']:
            print("\n⚠️  OVERDUE REQUIREMENTS:")
            for req in report['overdue_requirements']:
                print(f"  - {req['id']}: {req['title']} ({req['days_overdue']} days overdue)")
        
        print("\n📋 ACTIVE REQUIREMENTS:")
        for req in report['active_requirements'][:5]:  # Top 5
            status_emoji = "🔄" if req['status'] == "in_progress" else "📋"
            print(f"  {status_emoji} {req['id']}: {req['title']} ({req['completion_percentage']}%)")
    
    def update_requirement_status_interactive(self):
        """Interactive requirement status update."""
        print("\n🔧 INTERACTIVE REQUIREMENT UPDATE")
        print("=" * 40)
        
        # Show current requirements
        active_reqs = [
            req for req in self.tracker.requirements.values()
            if req.status in [RequirementStatus.IN_PROGRESS, RequirementStatus.NOT_STARTED]
        ]
        
        if not active_reqs:
            print("✅ No active requirements to update!")
            return
        
        print("Active Requirements:")
        for i, req in enumerate(active_reqs):
            print(f"  {i+1}. {req.id}: {req.title} ({req.status.value}, {req.completion_percentage}%)")
        
        try:
            choice = int(input(f"\nSelect requirement to update (1-{len(active_reqs)}): "))
            if choice < 1 or choice > len(active_reqs):
                print("❌ Invalid selection")
                return
            
            selected_req = active_reqs[choice - 1]
            
            print(f"\nSelected: {selected_req.id} - {selected_req.title}")
            print(f"Current Status: {selected_req.status.value}")
            print(f"Current Completion: {selected_req.completion_percentage}%")
            
            # Status options
            status_options = [
                RequirementStatus.NOT_STARTED,
                RequirementStatus.IN_PROGRESS,
                RequirementStatus.COMPLETED,
                RequirementStatus.BLOCKED
            ]
            
            print("\nStatus Options:")
            for i, status in enumerate(status_options):
                print(f"  {i+1}. {status.value}")
            
            status_choice = int(input(f"Select new status (1-{len(status_options)}): "))
            if status_choice < 1 or status_choice > len(status_options):
                print("❌ Invalid status selection")
                return
            
            new_status = status_options[status_choice - 1]
            
            # Completion percentage
            if new_status == RequirementStatus.COMPLETED:
                completion = 100
            elif new_status == RequirementStatus.NOT_STARTED:
                completion = 0
            else:
                completion = int(input("Enter completion percentage (0-100): "))
                if completion < 0 or completion > 100:
                    print("❌ Invalid completion percentage")
                    return
            
            # Notes
            notes = input("Enter update notes (optional): ").strip()
            user = input("Enter your name: ").strip() or "updater_script"
            
            # Update requirement
            self.tracker.update_requirement_status(
                selected_req.id,
                new_status,
                completion_percentage=completion,
                notes=notes,
                user=user
            )
            
            print(f"✅ Updated {selected_req.id} to {new_status.value} ({completion}%)")
            
            # Ask if user wants to update PROJECT_STATUS.md
            update_file = input("\nUpdate PROJECT_STATUS.md with new metrics? (y/N): ").lower()
            if update_file == 'y':
                self.update_project_status()
            
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Update cancelled")
    
    def validate_security_requirements(self) -> bool:
        """Validate security requirements configuration."""
        print("\n🔍 VALIDATING SECURITY REQUIREMENTS")
        print("=" * 40)
        
        issues = []
        
        # Check for critical requirements
        critical_reqs = self.tracker.get_requirements_by_priority(RequirementPriority.P0_CRITICAL)
        if len(critical_reqs) == 0:
            issues.append("No critical (P0) requirements defined")
        
        # Check for overdue requirements
        overdue_reqs = self.tracker.get_overdue_requirements()
        if overdue_reqs:
            issues.append(f"{len(overdue_reqs)} requirements are overdue")
        
        # Check implementation files
        for req in self.tracker.requirements.values():
            if req.status == RequirementStatus.COMPLETED and not req.implementation_file:
                issues.append(f"{req.id} is completed but has no implementation file specified")
        
        # Check metrics calculation
        try:
            metrics = self.tracker.calculate_security_metrics()
            if metrics.security_posture_score < 70:
                issues.append(f"Security posture score is low: {metrics.security_posture_score:.1f}")
        except Exception as e:
            issues.append(f"Failed to calculate metrics: {e}")
        
        if issues:
            print("⚠️  VALIDATION ISSUES FOUND:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("✅ Security requirements validation passed")
            return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Security Requirements Tracking Updater")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")
    parser.add_argument("--summary", action="store_true", help="Show security status summary")
    parser.add_argument("--interactive", action="store_true", help="Interactive requirement update")
    parser.add_argument("--validate", action="store_true", help="Validate security requirements")
    parser.add_argument("--update", action="store_true", help="Update PROJECT_STATUS.md")
    
    args = parser.parse_args()
    
    # Find project root
    current_dir = Path.cwd()
    project_root = current_dir
    
    # Look for PROJECT_STATUS.md to identify project root
    while project_root.parent != project_root:
        if (project_root / "PROJECT_STATUS.md").exists():
            break
        project_root = project_root.parent
    else:
        print("❌ Could not find PROJECT_STATUS.md in current directory or parents")
        sys.exit(1)
    
    print(f"📁 Project root: {project_root}")
    
    updater = SecurityTrackingUpdater(project_root)
    
    if args.summary or not any([args.dry_run, args.interactive, args.validate, args.update]):
        updater.show_security_summary()
    
    if args.validate:
        if not updater.validate_security_requirements():
            sys.exit(1)
    
    if args.interactive:
        updater.update_requirement_status_interactive()
    
    if args.update or args.dry_run:
        success = updater.update_project_status(dry_run=args.dry_run)
        if not success:
            sys.exit(1)
    
    print("\n✅ Security tracking update completed successfully!")


if __name__ == "__main__":
    main()