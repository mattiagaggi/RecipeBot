import pytest
from app.services.chat_service import ChatService

@pytest.fixture
def chat_service():
    return ChatService()

def test_response_variability(chat_service):
    """Test that the model generates different responses for the same input"""
    message = "Hello, how are you?"
    responses = set()
    
    # Generate multiple responses and check they're not all identical
    for _ in range(3):
        _, response = chat_service.generate_response(message)
        responses.add(response)
    
    # We should have at least 2 different responses out of 3 attempts
    # due to the randomness parameters we set
    assert len(responses) >= 2, "Responses show no variability"

def test_conversation_history(chat_service):
    """Test that the model properly uses conversation history"""
    # First message
    history_ids, response1 = chat_service.generate_response("What's your name?")
    
    # Second message should be influenced by the first
    _, response2 = chat_service.generate_response(
        "Can you repeat your name?", 
        session_history_ids=history_ids
    )
    
    # The second response should be somewhat related to the first
    # We can check this by ensuring some overlap in word usage
    
    history_ids, response1 = chat_service.generate_response("What's your name?", do_sample=False)
    _, response2 = chat_service.generate_response("Can you repeat your name?", session_history_ids=history_ids, do_sample=False)
    words1 = set(response1.lower().split())
    words2 = set(response2.lower().split())
    common_words = words1.intersection(words2)
    
    assert len(common_words) > 0, "No connection between responses in conversation"

def test_response_length_limits(chat_service):
    """Test that responses don't exceed maximum length"""
    # Generate a very long input
    long_input = "Tell me a very long story. " * 10
    
    _, response = chat_service.generate_response(long_input)
    
    # Check that the response doesn't exceed our max_history limit
    response_tokens = len(chat_service.tokenizer.encode(response))
    assert response_tokens <= chat_service.max_history, \
        "Response exceeded maximum length limit"

def test_special_token_handling(chat_service):
    """Test that special tokens are properly handled"""
    message = "Hello!"
    _, response = chat_service.generate_response(message)
    
    # Response shouldn't contain visible special tokens
    special_tokens = [chat_service.tokenizer.eos_token, chat_service.tokenizer.pad_token]
    for token in special_tokens:
        if token:  # Some tokenizers might have None for certain special tokens
            assert token not in response, f"Special token {token} found in response"

