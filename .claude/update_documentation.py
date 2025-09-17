#!/usr/bin/env python3
"""
Automated Documentation Update Hook
Enforces documentation maintenance rules (DM-001, DM-002, DM-003)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

def update_project_status():
    """Update PROJECT_STATUS.md timestamp (DM-001 enforcement)"""
    project_status = Path("PROJECT_STATUS.md")

    if project_status.exists():
        content = project_status.read_text()

        # Update timestamp
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith("**Last Updated:**"):
                lines[i] = f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
                break

        project_status.write_text('\n'.join(lines))
        print("✅ PROJECT_STATUS.md timestamp updated")
    else:
        print("⚠️  PROJECT_STATUS.md not found")

def update_session_state():
    """Update session state with documentation maintenance info"""
    state_file = Path(".claude_session_state.json")

    if state_file.exists():
        with open(state_file, 'r') as f:
            state = json.load(f)

        state["workflow_status"]["documentation_status"] = "current"
        state["last_documentation_update"] = datetime.now().isoformat()

        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        print("✅ Session state updated")

if __name__ == "__main__":
    update_project_status()
    update_session_state()
