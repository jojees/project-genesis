# tests/conftest.py
import sys
import os

# Add the project root directory to the Python path
# This assumes conftest.py is directly inside the 'tests' directory
# which is at the same level as 'app.py'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))