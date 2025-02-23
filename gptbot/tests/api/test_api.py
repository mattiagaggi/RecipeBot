import pytest
import requests

@pytest.fixture(scope="session")
def base_url():
    # Adjust port if needed, or read from environment
    return "http://localhost:8000"

def test_health_endpoint(base_url):
    """Test that the health endpoint returns status 200 and expected payload."""
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200, "Health endpoint should return 200"
    data = response.json()
    assert data.get("status") == "ok", "Health endpoint status should be 'ok'"

def test_chat_endpoint(base_url):
    """
    Test that the chat endpoint returns a response and a session ID.
    """
    payload = {"message": "Hello, how are you?"}
    response = requests.post(f"{base_url}/api/chat", json=payload)
    assert response.status_code == 200, "Chat endpoint should return 200"

    data = response.json()
    assert "response" in data, "Response payload should include 'response'"
    assert "session_id" in data, "Response payload should include 'session_id'"
    assert len(data["session_id"]) > 0, "session_id should not be empty"
    assert len(data["response"]) > 0, "Bot response should not be empty"

def test_chat_endpoint_continuation(base_url):
    """
    Test that providing an existing session continues the conversation.
    """
    # Start a conversation
    start_payload = {"message": "What's your name?"}
    start_response = requests.post(f"{base_url}/api/chat", json=start_payload)
    start_data = start_response.json()
    assert start_response.status_code == 200

    session_id = start_data["session_id"]
    first_bot_reply = start_data["response"]
    assert len(first_bot_reply) > 0

    # Continue conversation with the same session_id
    continue_payload = {
        "message": "Nice to meet you. How old are you?",
        "session_id": session_id
    }
    continue_response = requests.post(f"{base_url}/api/chat", json=continue_payload)
    continue_data = continue_response.json()
    assert continue_response.status_code == 200

    second_bot_reply = continue_data["response"]
    # Some minimal check to ensure the new reply is different or not empty
    assert len(second_bot_reply) > 0, "Second response should not be empty"
