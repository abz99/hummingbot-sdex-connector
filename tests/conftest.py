"""
Global pytest configuration and fixtures for Stellar connector tests.
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import all fixtures from our fixtures module
from tests.fixtures.stellar_component_fixtures import *