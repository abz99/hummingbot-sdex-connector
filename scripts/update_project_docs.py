#!/usr/bin/env python3
"""
Automated Project Documentation Updater
Ensures project status documents are always current and synchronized.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Key project documents to maintain
PROJECT_DOCS = {
    "PROJECT_STATUS.md": PROJECT_ROOT / "PROJECT_STATUS.md",
    "LAST_SESSION.md": PROJECT_ROOT / "LAST_SESSION.md", 
    "SESSION_SNAPSHOT.md": PROJECT_ROOT / "SESSION_SNAPSHOT.md",
}

# Phase tracking configuration
PHASES = {
    "Phase 1: Foundation": {"complete": True, "progress": 100},
    "Phase 2: Integration": {"complete": True, "progress": 95},
    "Phase 3: Advanced Features": {"complete": True, "progress": 90},
    "Phase 4A: Real-World Validation": {"complete": True, "progress": 100},
    "Phase 4B: Integration Testing": {"complete": False, "progress": 10},
    "Phase 4C: Production Deployment": {"complete": False, "progress": 0},
}

class ProjectDocumentationUpdater:
    """Automated documentation updater for project status files."""
    
    def __init__(self):
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.project_stats = self._gather_project_stats()
    
    def _gather_project_stats(self) -> Dict:
        """Gather current project statistics."""
        stats = {
            "last_updated": self.current_date,
            "git_commits": self._count_recent_commits(),
            "test_files": self._count_test_files(),
            "code_lines": self._count_code_lines(),
            "overall_progress": self._calculate_overall_progress(),
        }
        return stats
    
    def _count_recent_commits(self) -> int:
        """Count git commits from the last 7 days."""
        try:
            import subprocess
            result = subprocess.run([
                "git", "log", "--oneline", "--since=7.days.ago"
            ], capture_output=True, text=True, cwd=PROJECT_ROOT)
            return len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        except Exception:
            return 0
    
    def _count_test_files(self) -> int:
        """Count test files in the project."""
        test_dir = PROJECT_ROOT / "tests"
        if not test_dir.exists():
            return 0
        return len(list(test_dir.rglob("test_*.py")))
    
    def _count_code_lines(self) -> int:
        """Count lines of code in main connector modules."""
        connector_dir = PROJECT_ROOT / "hummingbot" / "connector" / "exchange" / "stellar"
        if not connector_dir.exists():
            return 0
        
        total_lines = 0
        for py_file in connector_dir.glob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    total_lines += len([line for line in f if line.strip() and not line.strip().startswith('#')])
            except Exception:
                continue
        return total_lines
    
    def _calculate_overall_progress(self) -> int:
        """Calculate overall project progress percentage."""
        total_phases = len(PHASES)
        completed_phases = sum(1 for phase_data in PHASES.values() if phase_data["complete"])
        current_progress = sum(phase_data["progress"] for phase_data in PHASES.values()) / total_phases
        return int(current_progress)
    
    def update_project_status(self):
        """Update PROJECT_STATUS.md with current information."""
        status_file = PROJECT_DOCS["PROJECT_STATUS.md"]
        if not status_file.exists():
            print(f"Warning: {status_file} not found")
            return
        
        content = status_file.read_text(encoding='utf-8')
        
        # Update last updated date
        content = re.sub(
            r'\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2}',
            f'**Last Updated:** {self.current_date}',
            content
        )
        
        # Update overall progress
        content = re.sub(
            r'- \*\*Overall Progress\*\*: \d+% complete',
            f'- **Overall Progress**: {self.project_stats["overall_progress"]}% complete',
            content
        )
        
        # Update quality metrics
        content = re.sub(
            r'- \*\*Test Coverage\*\*: [^\\n]+',
            f'- **Test Coverage**: {self.project_stats["test_files"]} test files, {self.project_stats["code_lines"]}+ lines of code',
            content
        )
        
        status_file.write_text(content, encoding='utf-8')
        print(f"✅ Updated PROJECT_STATUS.md")
    
    def update_last_session(self):
        """Update LAST_SESSION.md with current session information."""
        session_file = PROJECT_DOCS["LAST_SESSION.md"]
        if not session_file.exists():
            print(f"Warning: {session_file} not found")
            return
        
        content = session_file.read_text(encoding='utf-8')
        
        # Update the date in the header
        content = re.sub(
            r'# Last Session Quick Start - \d{4}-\d{2}-\d{2}',
            f'# Last Session Quick Start - {self.current_date}',
            content
        )
        
        # Update progress percentage
        content = re.sub(
            r'- \*\*Progress\*\*: \d+% complete',
            f'- **Progress**: {self.project_stats["overall_progress"]}% complete',
            content
        )
        
        session_file.write_text(content, encoding='utf-8')
        print(f"✅ Updated LAST_SESSION.md")
    
    def create_session_snapshot(self):
        """Create or update SESSION_SNAPSHOT.md with current session state."""
        snapshot_content = f"""# Session Snapshot - {self.current_date}

## 📊 Current Project State
- **Date**: {self.current_date}
- **Overall Progress**: {self.project_stats["overall_progress"]}%
- **Recent Commits**: {self.project_stats["git_commits"]} (last 7 days)
- **Test Files**: {self.project_stats["test_files"]}
- **Code Lines**: {self.project_stats["code_lines"]}+

## 📋 Phase Progress
"""
        
        for phase_name, phase_data in PHASES.items():
            status_icon = "✅" if phase_data["complete"] else "🔄"
            snapshot_content += f"- {status_icon} **{phase_name}**: {phase_data['progress']}%\\n"
        
        snapshot_content += f"""
## 🎯 Current Focus
- **Active Phase**: {"Phase 4B: Integration Testing" if not PHASES["Phase 4B: Integration Testing"]["complete"] else "Phase 4C: Production Deployment"}
- **Next Milestone**: Live network validation execution
- **Team Status**: 8-agent development team operational

## 📝 Session Notes
- Documentation automatically updated: {self.current_date}
- Project status documents synchronized
- Ready for next development session

---
*This snapshot was automatically generated by scripts/update_project_docs.py*
"""
        
        snapshot_file = PROJECT_DOCS["SESSION_SNAPSHOT.md"]
        snapshot_file.write_text(snapshot_content, encoding='utf-8')
        print(f"✅ Created/Updated SESSION_SNAPSHOT.md")
    
    def validate_documentation_sync(self) -> List[str]:
        """Validate that all documentation is synchronized."""
        issues = []
        
        # Check if all key files exist
        for doc_name, doc_path in PROJECT_DOCS.items():
            if not doc_path.exists():
                issues.append(f"Missing: {doc_name}")
        
        # Check if dates are current
        for doc_name, doc_path in PROJECT_DOCS.items():
            if doc_path.exists():
                content = doc_path.read_text(encoding='utf-8')
                if self.current_date not in content:
                    issues.append(f"Outdated: {doc_name} (no current date found)")
        
        return issues
    
    def run_full_update(self):
        """Run complete documentation update process."""
        print(f"🚀 Starting documentation update process - {self.current_date}")
        print(f"📊 Project Statistics:")
        for key, value in self.project_stats.items():
            print(f"   - {key}: {value}")
        
        # Update all documentation files
        self.update_project_status()
        self.update_last_session()  
        self.create_session_snapshot()
        
        # Validate synchronization
        issues = self.validate_documentation_sync()
        if issues:
            print("⚠️  Documentation Issues Found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ All documentation is synchronized and current")
        
        print(f"🎉 Documentation update complete!")

def main():
    """Main execution function."""
    updater = ProjectDocumentationUpdater()
    updater.run_full_update()

if __name__ == "__main__":
    main()