import pytest
import os
from query_dispatch import ChatGPTQueryDispatcher
from utils import get_config_path


def test_load_git_repo_into_history():
    dispatcher = ChatGPTQueryDispatcher(pre_prompt="Test pre-prompt")
    token_count = dispatcher.count_tokens()

    assert isinstance(token_count, int)
    assert token_count > 0

def test_query_dispatcher_init():
    """Test that the query dispatcher initializes correctly."""
    dispatcher = ChatGPTQueryDispatcher()
    assert dispatcher.client is not None
    assert dispatcher.messages == []

    # Test with pre_prompt
    pre_prompt = "You are a helpful assistant."
    dispatcher = ChatGPTQueryDispatcher(pre_prompt=pre_prompt)
    assert dispatcher.messages == [{"role": "system", "content": pre_prompt}]

def test_send_merged_query():
    """Test that the send_merged_query method correctly merges previous response with current input."""
    dispatcher = ChatGPTQueryDispatcher()

    # Mock the send_query method to avoid actual API calls
    original_send_query = dispatcher.send_query

    try:
        # Create a mock for send_query that returns the input
        def mock_send_query(input_text):
            return f"Response to: {input_text}"

        dispatcher.send_query = mock_send_query

        # Test the merged query
        previous_response = "This is my previous response"
        current_input = "What about this?"

        result = dispatcher.send_merged_query(previous_response, current_input)

        # Check that the result contains both the previous response and current input
        expected_merged_input = f"Your previous response was: '{previous_response}'. Now respond to: '{current_input}'"
        expected_result = f"Response to: {expected_merged_input}"

        assert result == expected_result

    finally:
        # Restore the original method
        dispatcher.send_query = original_send_query
