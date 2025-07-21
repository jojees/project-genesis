# src/audit-log-analysis/tests/conftest.py

import sys
import os

# Get the absolute path to the directory containing the 'audit_analysis' package
# This goes up one level from 'tests/' to 'audit-log-analysis/'
# Then it adds 'src' to the path to include 'src/audit-log-analysis'
# However, given your tree, 'audit_analysis' is directly inside 'audit-log-analysis'
# So, we need to add the parent directory of `tests/` to the sys.path.
# Corrected path for your specific tree:
# Go up from 'tests/' to 'audit-log-analysis/'
# Then add this directory itself to the path, so 'audit_analysis' is discoverable.

current_dir = os.path.dirname(os.path.abspath(__file__))
# Path to 'audit-log-analysis' directory (parent of 'tests')
project_root = os.path.join(current_dir, '..')

# Add the project root to sys.path
# This makes 'audit_analysis' importable as `import audit_analysis.config`
sys.path.insert(0, project_root)

print(f"\nAdded '{project_root}' to sys.path for testing.")