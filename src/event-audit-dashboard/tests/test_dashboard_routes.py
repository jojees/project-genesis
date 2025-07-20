# src/event-audit-dashboard/tests/test_dashboard_routes.py

import requests
import json


def test_root_dashboard_displays_alerts_on_api_success(client, mocker):
    """
    Tests that the root dashboard displays alerts fetched successfully from
    the Notification Service API.
    """
    mock_alerts_data = [
        {
            "alert_id": "alert1",
            "alert_type": "SECURITY", # Changed to uppercase to match rendered HTML
            "alert_name": "Critical Event - Test 1",
            "severity": "CRITICAL", # Changed to uppercase to match rendered HTML
            "timestamp": "2025-07-20T10:00:00Z",
            "source_service_name": "test_source_1",
            "description": "This is a test description for alert 1."
        },
        {
            "alert_id": "alert2",
            "alert_type": "PERFORMANCE", # Changed to uppercase
            "alert_name": "Warning Sign - Test 2",
            "severity": "MEDIUM", # You can keep this or change to "MEDIUM" in HTML if it renders uppercase
            "timestamp": "2025-07-20T09:30:00Z",
            "source_service_name": "test_source_2",
            "description": "This is a test description for alert 2."
        }
    ]

    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_alerts_data

    # mocker.patch('requests.get', return_value=mock_response)
    # Capture the returned mock object when patching requests.get
    mock_get = mocker.patch('requests.get', return_value=mock_response)

    response = client.get('/')

    assert response.status_code == 200
    assert b"Critical Event - Test 1" in response.data
    assert b"Warning Sign - Test 2" in response.data
    assert b"View Details" in response.data
    assert b"ID: alert1" in response.data

    # --- UPDATED ASSERTIONS TO MATCH RENDERED HTML EXACTLY ---
    assert b"<strong>Source:</strong> test_source_1" in response.data
    assert b"This is a test description for alert 1." in response.data
    assert b"<strong>Severity:</strong> CRITICAL" in response.data # <--- CHANGED HERE
    assert b"<strong>Type:</strong> SECURITY" in response.data     # <--- CHANGED HERE
    # --- END UPDATED ASSERTIONS ---

    # Optional: Verify that requests.get was called with the correct arguments
    expected_url = f"http://localhost:8000/alerts?limit=30"
    # mocker.patch.assert_called_once_with(
    #     'requests.get',
    #     expected_url,
    #     timeout=10
    # )

    mock_get.assert_called_once_with(expected_url, timeout=10)


def test_root_dashboard_handles_api_connection_error(client, mocker):
    """
    Tests that the root dashboard displays an error message when it cannot
    connect to the Notification Service API.
    """
    # Define the base URL used by your app for consistency
    notification_service_base_url = "http://localhost:8000" # Assuming this is your NOTIFICATION_SERVICE_API_BASE_URL for testing

    # Patch requests.get to raise a ConnectionError
    mock_get = mocker.patch(
        'requests.get',
        side_effect=requests.exceptions.ConnectionError("Mocked connection error")
    )

    response = client.get('/')

    # Assertions
    assert response.status_code == 200

    # Verify that the specific error message from the ConnectionError handler is displayed
    expected_error_text = f"Could not connect to Notification Service at {notification_service_base_url}: Mocked connection error. Is it running and accessible?"
    assert b"Error:" in response.data # Check for the static 'Error:' label
    assert expected_error_text.encode('utf-8') in response.data # Check for the dynamic error message

    # Verify that no alerts or the "No alerts" message appear when an error is present
    assert b"No alerts to display." in response.data
    print(response.data)
    assert b'<div class="alert-item">' not in response.data

    # Verify that requests.get was called with the correct arguments
    expected_url = f"{notification_service_base_url}/alerts?limit=30"
    mock_get.assert_called_once_with(expected_url, timeout=10)


def test_root_dashboard_handles_api_timeout(client, mocker):
    """
    Tests that the root dashboard displays an error message when the
    Notification Service API call times out.
    """
    # Define the base URL used by your app for consistency
    notification_service_base_url = "http://localhost:8000"

    # Patch requests.get to raise a Timeout exception
    mock_get = mocker.patch(
        'requests.get',
        side_effect=requests.exceptions.Timeout("Mocked timeout error")
    )

    response = client.get('/')

    # Assertions
    assert response.status_code == 200

    # Verify that the specific error message from the Timeout handler is displayed
    # Based on app.py: error_message = f"Timeout when connecting to Notification Service at {NOTIFICATION_SERVICE_API_BASE_URL}."
    expected_error_text = f"Timeout when connecting to Notification Service at {notification_service_base_url}."
    assert b"Error:" in response.data # Check for the static 'Error:' label
    assert expected_error_text.encode('utf-8') in response.data # Check for the dynamic error message

    # Verify that no alerts are actually displayed (i.e., no div elements with class "alert-item")
    # This assertion checks for the actual HTML tag, not just the string in CSS.
    assert b'<div class="alert-item">' not in response.data
    # Verify that the "No alerts to display." message *is* present because `alerts` is empty
    assert b"No alerts to display." in response.data

    # Verify that requests.get was called with the correct arguments
    expected_url = f"{notification_service_base_url}/alerts?limit=30"
    mock_get.assert_called_once_with(expected_url, timeout=10)


def test_root_dashboard_handles_api_non_200_status(client, mocker):
    """
    Tests that the root dashboard displays an error message when the
    Notification Service API returns a non-200 status code.
    """
    # Define the base URL used by your app for consistency
    notification_service_base_url = "http://localhost:8000"

    # Simulate a non-200 response (e.g., 500 Internal Server Error)
    mock_response = mocker.Mock()
    mock_response.status_code = 500 # Simulate a server error
    mock_response.text = "Internal Server Error from Notification Service" # Provide some response text
    mock_response.json.side_effect = ValueError("Not valid JSON for non-200 status") # .json() might fail or not be called for non-200s

    mock_get = mocker.patch('requests.get', return_value=mock_response)

    response = client.get('/')

    # Assertions
    assert response.status_code == 200 # Dashboard still returns 200 OK for its own page

    # Verify that the specific error message for non-200 status is displayed
    # Based on app.py: error_message = f"Failed to fetch alerts: Status Code {response.status_code}. Response: {response.text}"
    expected_error_text = f"Failed to fetch alerts: Status Code 500. Response: Internal Server Error from Notification Service"
    assert b"Error:" in response.data
    assert expected_error_text.encode('utf-8') in response.data

    # Verify that no alerts are actually displayed (i.e., no div elements with class "alert-item")
    assert b'<div class="alert-item">' not in response.data
    # Verify that the "No alerts to display." message *is* present because `alerts` is empty
    assert b"No alerts to display." in response.data

    # Verify that requests.get was called with the correct arguments
    expected_url = f"{notification_service_base_url}/alerts?limit=30"
    mock_get.assert_called_once_with(expected_url, timeout=10)


def test_root_dashboard_handles_empty_alerts_list(client, mocker):
    """
    Tests that the root dashboard displays the 'No alerts to display' message
    when the Notification Service API returns an empty list.
    """
    # Simulate a successful API response with an empty list of alerts
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [] # Key change: API returns an empty list

    mock_get = mocker.patch('requests.get', return_value=mock_response)

    response = client.get('/')

    # Assertions
    assert response.status_code == 200 # Should still be a successful page load

    # Verify that the "No alerts to display." message is present
    assert b"No alerts to display." in response.data

    # Verify that no actual alert items are rendered (empty list)
    assert b'<div class="alert-item">' not in response.data

    # Verify that no error message is displayed
    assert b"Error:" not in response.data
    assert b"Failed to fetch alerts:" not in response.data
    assert b"Could not connect to Notification Service" not in response.data
    assert b"Timeout when connecting to Notification Service" not in response.data
    assert b"An unexpected error occurred" not in response.data

    # Verify that requests.get was called with the correct arguments
    expected_url = "http://localhost:8000/alerts?limit=30" # Adjust if your env vars are set differently
    mock_get.assert_called_once_with(expected_url, timeout=10)


def test_alert_detail_displays_specific_alert_on_api_success(client, mocker):
    """
    Tests that the alert detail page displays a specific alert fetched
    successfully from the Notification Service API, including all its fields.
    """
    mock_alert_id = "test-alert-123"
    # Make sure this mock description EXACTLY matches what's rendered in HTML for the assertion
    mock_alert_data = {
        "alert_id": mock_alert_id,
        "correlation_id": "corr-456",
        "alert_name": "Login Brute Force Detected",
        "alert_type": "SECURITY",
        "severity": "CRITICAL",
        "timestamp": "2025-07-20T15:30:00Z",
        "received_at": "2025-07-20T15:31:00Z",
        "description": "User 'bad_actor' attempted 5 failed logins within 30 seconds from suspicious IPs.", # <--- Ensure this matches the text in HTML
        "source_service_name": "auth-service",
        "action_observed": "login_attempt_failed",
        "rule_id": "rule-101",
        "rule_name": "Brute Force Login Rule",
        "analysis_rule_details": {"threshold": 5, "time_window_seconds": 30},
        "actor_id": "user-999",
        "actor_type": "User",
        "client_ip": "192.168.1.100",
        "triggered_by_details": {"username": "bad_actor"},
        "resource_id": "server-abc",
        "resource_type": "Server",
        "server_hostname": "api.example.com",
        "impacted_resource_details": {"port": 443, "protocol": "HTTPS"},
        "metadata": {"tags": ["critical", "login"]},
        "raw_event_data": {"event_type": "login_failure", "ip": "192.168.1.100"}
    }

    notification_service_base_url = "http://localhost:8000"

    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_alert_data

    mock_get = mocker.patch('requests.get', return_value=mock_response)

    response = client.get(f'/alert/{mock_alert_id}')

    assert response.status_code == 200
    assert b"<title>Alert Details</title>" in response.data
    assert b"<h1>Alert Details</h1>" in response.data

    # Verify specific alert details are present and correctly formatted
    assert b"Alert ID:</strong> test-alert-123" in response.data
    assert b"Correlation ID:</strong> corr-456" in response.data
    assert b"Alert Name:</strong> Login Brute Force Detected" in response.data
    assert b"Alert Type:</strong> SECURITY" in response.data
    assert b"Severity:</strong> CRITICAL" in response.data
    assert b"Timestamp:</strong> 2025-07-20T15:30:00Z" in response.data
    assert b"Received At:</strong> 2025-07-20T15:31:00Z" in response.data
    # <--- Corrected description assertion here
    assert b"Description:</strong> User &#39;bad_actor&#39; attempted 5 failed logins within 30 seconds from suspicious IPs." in response.data
    assert b"Source Service:</strong> auth-service" in response.data
    assert b"Action Observed:</strong> login_attempt_failed" in response.data

    # Check for optional sections if data is provided
    assert b"<h2>Analysis Rule Details</h2>" in response.data
    assert b"Rule ID:</strong> rule-101" in response.data
    assert b"Rule Name:</strong> Brute Force Login Rule" in response.data
    assert json.dumps({"threshold": 5, "time_window_seconds": 30}, indent=2).encode('utf-8') in response.data

    assert b"<h2>Triggered By Details</h2>" in response.data
    assert b"Actor Type:</strong> User" in response.data
    assert b"Actor ID:</strong> user-999" in response.data
    assert b"Client IP:</strong> 192.168.1.100" in response.data
    assert json.dumps({"username": "bad_actor"}, indent=2).encode('utf-8') in response.data

    assert b"<h2>Impacted Resource Details</h2>" in response.data
    assert b"Resource Type:</strong> Server" in response.data
    assert b"Resource ID:</strong> server-abc" in response.data
    assert b"Server Hostname:</strong> api.example.com" in response.data
    assert json.dumps({"port": 443, "protocol": "HTTPS"}, indent=2).encode('utf-8') in response.data

    assert b"<h2>Metadata</h2>" in response.data
    assert json.dumps({"tags": ["critical", "login"]}, indent=2).encode('utf-8') in response.data

    assert b"<h2>Raw Event Data</h2>" in response.data
    assert json.dumps({"event_type": "login_failure", "ip": "192.168.1.100"}, indent=2).encode('utf-8') in response.data

    # Ensure no general error messages or "no alert details" are displayed
    assert b"Error:" not in response.data
    assert b"No alert details available." not in response.data

    # Check for the back link
    assert b'<a href="/">Back to Dashboard</a>' in response.data

    # Verify that requests.get was called with the correct arguments for the specific alert
    expected_url = f"{notification_service_base_url}/alerts/{mock_alert_id}"
    mock_get.assert_called_once_with(expected_url, timeout=10)


def test_alert_detail_handles_alert_not_found(client, mocker):
    """
    Tests that the alert detail page displays an error when the API returns
    a 404 Not Found status for a specific alert ID.
    """
    mock_alert_id = "non-existent-alert-999"

    # Define the base URL used by your app for consistency
    notification_service_base_url = "http://localhost:8000"

    # Simulate a 404 Not Found response from the API
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mock_response.text = "Alert with ID non-existent-alert-999 not found." # Set text to match what Flask will use
    mock_response.json.side_effect = ValueError("Not valid JSON for non-200 status")

    mock_get = mocker.patch('requests.get', return_value=mock_response)

    response = client.get(f'/alert/{mock_alert_id}')

    # Assertions
    assert response.status_code == 200 # Dashboard itself still renders with 200 OK

    # Verify that the specific "No alert details available." message is NOT displayed
    # because the template shows a specific error message.
    assert b"No alert details available." not in response.data # <--- Change to NOT IN

    # Verify that no alert details are rendered
    assert b'<div class="alert-details">' not in response.data
    assert b"Alert ID:" not in response.data

    # Verify the specific 404 error message from the template is shown
    # <--- Corrected error message assertion here
    expected_error_text = f"Alert with ID {mock_alert_id} not found."
    assert b"Error:" in response.data
    assert expected_error_text.encode('utf-8') in response.data


    # Check for the back link (should always be present)
    assert b'<a href="/">Back to Dashboard</a>' in response.data

    # Verify that requests.get was called with the correct arguments
    expected_url = f"{notification_service_base_url}/alerts/{mock_alert_id}"
    mock_get.assert_called_once_with(expected_url, timeout=10)


def test_alert_detail_handles_api_failure(client, mocker):
    """
    Tests that the alert detail page displays a generic error message when the
    Notification Service API fails for a reason other than 404 (e.g., 500, or a connection/timeout error).
    This test focuses on the non-200/non-404 cases.
    """
    mock_alert_id = "some-alert-id"

    # Define the base URL used by your app for consistency
    notification_service_base_url = "http://localhost:8000"

    # Simulate a generic API failure (e.g., 500 Internal Server Error)
    mock_response = mocker.Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error from Notification Service API" # Match this if app.py uses it
    mock_response.json.side_effect = ValueError("Cannot decode JSON for non-200 status")

    mock_get = mocker.patch('requests.get', return_value=mock_response)

    response = client.get(f'/alert/{mock_alert_id}')

    # Assertions
    assert response.status_code == 200

    # Verify that no alert details are rendered
    assert b'<div class="alert-details">' not in response.data
    assert b"Alert ID:" not in response.data

    # Verify "No alert details available." is NOT present
    assert b"No alert details available." not in response.data

    # Verify the generic API failure error message is shown
    # <--- Corrected expected_error_text here
    expected_error_text = f"Failed to fetch alert ID {mock_alert_id}: Status Code 500. Response: Internal Server Error from Notification Service API"
    assert b"Error:" in response.data
    assert expected_error_text.encode('utf-8') in response.data

    # Check for the back link
    assert b'<a href="/">Back to Dashboard</a>' in response.data

    # Verify that requests.get was called with the correct arguments
    expected_url = f"{notification_service_base_url}/alerts/{mock_alert_id}"
    mock_get.assert_called_once_with(expected_url, timeout=10)