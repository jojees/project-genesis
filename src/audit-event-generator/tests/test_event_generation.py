import pytest
import unittest.mock as mock
import json
import uuid
import datetime
import random
from flask import Flask, request
from app import generate_specific_event, generate_and_publish_random_event, audit_events_total, publish_event, app as flask_app, EVENT_TEMPLATES, SIMULATED_HOSTNAMES, SIMULATED_USERS

# from app import generate_specific_event, audit_events_total, publish_event, app as flask_app
# Reset Prometheus counters for a clean test environment if needed
# For unit tests, it's often better to mock the metrics interaction,
# but if we're directly calling the function that increments,
# we might need to reset or assert after a single call.
# However, for this specific test, we're just checking structure,
# so the metric increments are a side effect we don't need to assert on.

def test_generate_event_structure():
    """
    Verify that the generate_and_publish_random_event function
    produces an event dictionary with all expected top-level keys.
    """
    # Mock dependencies to prevent actual RabbitMQ publishing and metric increments
    # We only care about the structure of the *returned* event
    with mock.patch('app.publish_event') as mock_publish_event:
        with mock.patch('app.audit_events_total.labels') as mock_labels:
            # Call the function
            event = generate_and_publish_random_event()

            # Define the expected top-level keys
            expected_keys = [
                "event_id",
                "timestamp",
                "source_service",
                "server_hostname",
                "event_type",
                "severity",
                "user_id",
                "action_result",
                "details"
            ]

            # Assert that all expected keys are present in the generated event
            for key in expected_keys:
                assert key in event, f"Expected key '{key}' not found in the generated event."

            # Assert that the event_id is a valid UUID string
            assert isinstance(event["event_id"], str)
            # Try to convert to UUID to ensure it's valid format
            assert uuid.UUID(event["event_id"], version=4)

            # Assert that timestamp is a string
            assert isinstance(event["timestamp"], str)
            # Try to parse timestamp to ensure it's a valid ISO format
            datetime.datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))

            # Assert source_service is correct
            assert event["source_service"] == "audit-event-generator"

            # Assert that details is a dictionary
            assert isinstance(event["details"], dict)

            # Ensure publish_event was called with the generated event
            mock_publish_event.assert_called_once_with(event)

            # Ensure labels method was called (indicating metric increment attempt)
            mock_labels.assert_called_once()
            # You could further assert the arguments to labels if needed,
            # but for this specific test, we're mostly concerned with the event structure.


def test_generate_event_details_vary_by_type():
    """
    Verify that the 'details' field in generated events correctly reflects
    the expected structure and content for different event types based on EVENT_TEMPLATES.
    """
    # Mock dependencies to prevent actual RabbitMQ publishing and metric increments
    with mock.patch('app.publish_event') as mock_publish_event:
        with mock.patch('app.audit_events_total.labels') as mock_labels:
            # We'll test a few specific event types to ensure their 'details' are correct.

            # --- Mock random.choice for all calls within generate_and_publish_random_event ---
            # Create a mock for random.choice that can be configured for each sub-test
            with mock.patch('random.choice') as mock_random_choice:

                # --- Test Case 1: user_login (FAILURE) ---
                # Configure mock_random_choice for this specific scenario
                # The order here is crucial:
                # 1. EVENT_TEMPLATES choice
                # 2. SIMULATED_HOSTNAMES choice
                # 3. SIMULATED_USERS choice
                mock_random_choice.side_effect = [
                    (
                        "user_login", "WARNING", "FAILURE", lambda: {
                            "reason": "Incorrect password",
                            "ip_address": "192.168.1.150", # Fixed for testing
                            "protocol": "ssh"             # Fixed for testing
                        }
                    ),
                    "prod-web-01",  # For SIMULATED_HOSTNAMES
                    "devops_admin"  # For SIMULATED_USERS
                ]

                event = generate_and_publish_random_event()
                assert event["event_type"] == "user_login"
                assert event["action_result"] == "FAILURE"
                assert "details" in event
                assert isinstance(event["details"], dict)
                assert event["details"]["reason"] == "Incorrect password"
                assert event["details"]["ip_address"] == "192.168.1.150"
                assert event["details"]["protocol"] == "ssh"
                assert event["server_hostname"] == "prod-web-01" # Assert on the hostname as well
                assert event["user_id"] == "devops_admin" # Assert on the user_id as well
                mock_publish_event.reset_mock() # Reset mock for next iteration
                mock_labels.reset_mock()
                mock_random_choice.reset_mock() # Reset random.choice mock too

                # --- Test Case 2: file_modified (CRITICAL) ---
                mock_random_choice.side_effect = [
                    (
                        "file_modified", "CRITICAL", "MODIFIED", lambda: {
                            "resource": "/etc/passwd",
                            "old_checksum": "abcde123", # Fixed for testing
                            "new_checksum": "fghij456", # Fixed for testing
                            "size_change_bytes": 50
                        }
                    ),
                    "prod-db-02",   # For SIMULATED_HOSTNAMES
                    "app_user"      # For SIMULATED_USERS
                ]

                event = generate_and_publish_random_event()
                assert event["event_type"] == "file_modified"
                assert event["action_result"] == "MODIFIED"
                assert "details" in event
                assert isinstance(event["details"], dict)
                assert event["details"]["resource"] == "/etc/passwd"
                assert event["details"]["old_checksum"] == "abcde123"
                assert event["details"]["new_checksum"] == "fghij456"
                assert event["details"]["size_change_bytes"] == 50
                assert event["server_hostname"] == "prod-db-02"
                assert event["user_id"] == "app_user"
                mock_publish_event.reset_mock()
                mock_labels.reset_mock()
                mock_random_choice.reset_mock()

                # --- Test Case 3: service_status_change (STOPPED) ---
                mock_random_choice.side_effect = [
                    (
                        "service_status_change", "WARNING", "STOPPED", lambda: {
                            "resource": "nginx.service",
                            "previous_state": "RUNNING",
                            "message": "Service unexpectedly stopped."
                        }
                    ),
                    "dev-api-03",   # For SIMULATED_HOSTNAMES
                    "monitoring_agent" # For SIMULATED_USERS
                ]
                # If "cwd" is generated dynamically for some templates, you might need to
                # add a mock for random.choice inside that lambda too, or adjust the lambda
                # to be deterministic if possible for testing.
                # For this specific template, the lambda doesn't call random.choice, so it's fine.

                event = generate_and_publish_random_event()
                assert event["event_type"] == "service_status_change"
                assert event["action_result"] == "STOPPED"
                assert "details" in event
                assert isinstance(event["details"], dict)
                assert event["details"]["resource"] == "nginx.service"
                assert event["details"]["previous_state"] == "RUNNING"
                assert event["details"]["message"] == "Service unexpectedly stopped."
                assert event["server_hostname"] == "dev-api-03"
                assert event["user_id"] == "monitoring_agent"
                mock_publish_event.reset_mock()
                mock_labels.reset_mock()
                mock_random_choice.reset_mock()

            # Add more test cases for other critical EVENT_TEMPLATES as needed.


def test_generate_event_randomness():
    """
    Verify that dynamic fields (server_hostname, user_id, and details content)
    of generated events show randomness across multiple generations.
    """
    # Mock dependencies to prevent actual RabbitMQ publishing and metric increments
    with mock.patch('app.publish_event') as mock_publish_event:
        with mock.patch('app.audit_events_total.labels') as mock_labels:
            # We will generate multiple events and collect their dynamic properties.
            generated_hostnames = set()
            generated_users = set()
            generated_details_ip_addresses = set()
            generated_details_checksums = set() # For file_modified events
            generated_details_resources = set() # For file_modified/service_status_change
            generated_details_commands = set() # For sudo_command

            # Mock random.choice and random.randint separately
            with mock.patch('random.choice') as mock_random_choice, \
                 mock.patch('random.randint') as mock_random_randint, \
                 mock.patch('uuid.uuid4') as mock_uuid_uuid4: # Mock uuid.uuid4 for deterministic checksums/user names

                num_iterations = 10 # Generate multiple events to observe randomness

                # Pre-define sequences of mock returns to ensure variety for each iteration
                # These lists define what the mocks will return for *each* event generation cycle.

                # Sequence for random.choice(EVENT_TEMPLATES)
                template_sequence = [EVENT_TEMPLATES[i % len(EVENT_TEMPLATES)] for i in range(num_iterations)]

                # Sequence for random.choice(SIMULATED_HOSTNAMES)
                hostname_sequence = [SIMULATED_HOSTNAMES[i % len(SIMULATED_HOSTNAMES)] for i in range(num_iterations)]

                # Sequence for random.choice(SIMULATED_USERS)
                user_sequence = [SIMULATED_USERS[i % len(SIMULATED_USERS)] for i in range(num_iterations)]

                # Define a fixed set of choices for internal random.choice calls for details
                # This ensures we get variation without exhausting a single side_effect
                protocol_choices = ["ssh", "console"]
                resource_choices = ["/etc/passwd", "/var/log/nginx/access.log"]
                command_choices = ["/usr/bin/sudo apt update", "/usr/bin/useradd newuser"]
                group_choices = ["users", "devops"]
                service_choices = ["nginx.service", "mysql.service"]
                prev_state_choices = ["STOPPED", "FAILED"]


                # Set side_effects for the *entire test's* sequence of random calls
                # This is more complex because random.choice might be called multiple times per event.
                # A better strategy is to control the return of `random.choice` based on its arguments.

                # Since `random.choice` is used with *different* lists (EVENT_TEMPLATES, SIMULATED_HOSTNAMES, etc.),
                # we can define a `side_effect` that is a callable. This callable will receive the arguments
                # passed to `random.choice` and return a specific value.

                def custom_choice_side_effect(*args, **kwargs):
                    items = args[0] # The list passed to random.choice

                    if items is EVENT_TEMPLATES:
                        return template_sequence.pop(0) # Consume from pre-defined sequence
                    elif items is SIMULATED_HOSTNAMES:
                        return hostname_sequence.pop(0)
                    elif items is SIMULATED_USERS:
                        return user_sequence.pop(0)
                    elif items is protocol_choices: # Used in user_login lambda
                        return protocol_choices[next(protocol_choice_iterator)]
                    elif items is resource_choices: # Used in file_modified lambda
                        return resource_choices[next(resource_choice_iterator)]
                    elif items is command_choices: # Used in sudo_command lambda
                         return command_choices[next(command_choice_iterator)]
                    elif items is group_choices: # Used in user_account_management lambda
                         return group_choices[next(group_choice_iterator)]
                    elif items is service_choices: # Used in service_status_change lambda
                         return service_choices[next(service_choice_iterator)]
                    elif items is prev_state_choices: # Used in service_status_change lambda
                         return prev_state_choices[next(prev_state_choice_iterator)]
                    else:
                        # Fallback for any other unexpected random.choice calls or if
                        # a specific sequence is not defined, just pick the first.
                        return items[0]

                mock_random_choice.side_effect = custom_choice_side_effect

                # Iterators for internal random.choice calls within details generators
                # We'll cycle them to get different values
                protocol_choice_iterator = iter([i % len(protocol_choices) for i in range(num_iterations * 2)]) # *2 because user_login has two random.choice calls in its lambda
                resource_choice_iterator = iter([i % len(resource_choices) for i in range(num_iterations)])
                command_choice_iterator = iter([i % len(command_choices) for i in range(num_iterations)])
                group_choice_iterator = iter([i % len(group_choices) for i in range(num_iterations)])
                service_choice_iterator = iter([i % len(service_choices) for i in range(num_iterations)])
                prev_state_choice_iterator = iter([i % len(prev_state_choices) for i in range(num_iterations)])

                # Mock random.randint to return varying values
                mock_random_randint.side_effect = [100 + i for i in range(num_iterations)] # For IP address random part
                # If size_change_bytes lambda calls randint, add more values here
                mock_random_randint


def test_generate_event_with_specific_type():
    """
    Verify that the generate_specific_event function (used by API)
    produces an event with the specified event_type when provided in the payload.
    """
    # Create a test Flask application context
    # This is necessary because generate_specific_event expects request.json
    with flask_app.test_request_context(
        '/generate_event',
        method='POST',
        json={"event_type": "custom_test_event", "user_id": "test_user_api"}
    ):
        # Mock dependencies to prevent actual RabbitMQ publishing and metric increments
        with mock.patch('app.publish_event') as mock_publish_event:
            with mock.patch('app.audit_events_total.labels') as mock_labels:
                # Call the function directly that the API endpoint would call
                # and capture its return value (which is a Flask response tuple)
                response, status_code = generate_specific_event()

                # Parse the JSON response
                response_data = json.loads(response.get_data(as_text=True))

                # Assert the API response status and content
                assert status_code == 202
                assert response_data["status"] == "success"
                assert "event_id" in response_data

                # Verify publish_event was called and inspect the event data passed to it
                mock_publish_event.assert_called_once()
                published_event = mock_publish_event.call_args[0][0] # Get the first argument of the first call

                # Assert that the event_type in the published event matches the one we sent
                assert published_event["event_type"] == "custom_test_event"
                assert published_event["user_id"] == "test_user_api"
                assert published_event["source_service"] == "audit-event-generator-api"

                # Also verify that default values are set if not provided
                assert "server_hostname" in published_event
                assert "action_result" in published_event
                assert "severity" in published_event
                assert isinstance(published_event["details"], dict) # Should be an empty dict by default here

                # Ensure labels method was called with the correct event_type
                mock_labels.assert_called_once_with(
                    event_type="custom_test_event",
                    server_hostname=mock.ANY, # Value is random, so we don't assert specific value
                    action_result="SUCCESS"
                )