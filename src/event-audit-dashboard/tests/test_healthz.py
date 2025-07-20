# src/event-audit-dashboard/tests/test_healthz.py

def test_healthz_endpoint_returns_healthy_json(client):
    """
    Tests that the /healthz endpoint returns a 200 OK status
    and a JSON object with 'status': 'healthy'.
    """
    response = client.get('/healthz')
    assert response.status_code == 200
    # Assert the JSON response content
    assert response.json == {"status": "healthy", "service": "event-audit-dashboard"}