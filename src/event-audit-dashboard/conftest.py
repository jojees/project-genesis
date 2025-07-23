import sys
import os
import pytest

# Add the parent directory of 'event_audit_dashboard' to sys.path
# This makes 'event_audit_dashboard' importable as a top-level package.
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# IMPORT THE 'app' INSTANCE DIRECTLY from your Flask application file
from event_audit_dashboard.app import app

@pytest.fixture
def client():
    """
    Provides a test client for the Flask application.
    The 'app' instance is imported directly from event_audit_dashboard.app.
    """
    app.config['TESTING'] = True # Enable testing mode for Flask
    with app.test_client() as client:
        yield client