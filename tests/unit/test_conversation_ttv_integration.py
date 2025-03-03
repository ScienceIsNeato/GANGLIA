"""Unit tests for the conversational interface's integration with TTV.

This module contains tests for the integration between the conversational
interface and the text-to-video functionality.
"""

import unittest
from unittest.mock import MagicMock, patch
from conversational_interface import Conversation
from story_generation_driver import StoryInfoType, StoryGenerationState
from pubsub import Event, EventType


class TestConversationTTVIntegration(unittest.TestCase):
    """Test cases for the conversational interface's integration with TTV."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_query_dispatcher = MagicMock()
        self.mock_tts = MagicMock()
        self.mock_dictation = MagicMock()
        self.mock_session_logger = MagicMock()
        self.mock_user_turn_indicator = MagicMock()
        self.mock_ai_turn_indicator = MagicMock()
        self.mock_hotword_manager = MagicMock()

        # Mock the pubsub system
        self.mock_pubsub = MagicMock()

        # Create a patcher for the pubsub system
        self.pubsub_patcher = patch('conversational_interface.get_pubsub')
        self.mock_get_pubsub = self.pubsub_patcher.start()
        self.mock_get_pubsub.return_value = self.mock_pubsub

        # Mock the story generation driver
        self.mock_story_driver = MagicMock()

        # Create a patcher for the story generation driver
        self.story_driver_patcher = patch('conversational_interface.StoryGenerationDriver')
        self.mock_story_driver_class = self.story_driver_patcher.start()
        self.mock_story_driver_class.return_value = self.mock_story_driver

        # Create a conversation instance with the mock dependencies
        self.conversation = Conversation(
            query_dispatcher=self.mock_query_dispatcher,
            tts=self.mock_tts,
            dictation=self.mock_dictation,
            session_logger=self.mock_session_logger,
            user_turn_indicator=self.mock_user_turn_indicator,
            ai_turn_indicator=self.mock_ai_turn_indicator,
            hotword_manager=self.mock_hotword_manager
        )

    def tearDown(self):
        """Tear down test fixtures."""
        # Stop the patchers
        self.pubsub_patcher.stop()
        self.story_driver_patcher.stop()

    def test_initialization(self):
        """Test initialization of the conversation."""
        # Verify pubsub subscriptions were set up
        self.mock_pubsub.subscribe.assert_any_call(
            EventType.STORY_INFO_NEEDED,
            self.conversation._handle_story_info_needed
        )
        self.mock_pubsub.subscribe.assert_any_call(
            EventType.TTV_PROCESS_STARTED,
            self.conversation._handle_ttv_process_started
        )
        self.mock_pubsub.subscribe.assert_any_call(
            EventType.TTV_PROCESS_COMPLETED,
            self.conversation._handle_ttv_process_completed
        )
        self.mock_pubsub.subscribe.assert_any_call(
            EventType.TTV_PROCESS_FAILED,
            self.conversation._handle_ttv_process_failed
        )

        # Verify conversation started event was published
        self.mock_pubsub.publish.assert_called_once()
        event = self.mock_pubsub.publish.call_args[0][0]
        self.assertEqual(event.event_type, EventType.CONVERSATION_STARTED)
        self.assertEqual(event.data['user_id'], self.conversation.user_id)

    def test_video_hotword_detection(self):
        """Test detection of the 'video' hotword."""
        # Set up the hotword manager to detect 'video'
        self.mock_hotword_manager.detect_hotwords.return_value = (True, "If you tell me an interesting story, I can try to make a video.")

        # Process user input with the 'video' hotword
        response = self.conversation.process_user_input("I want to make a video")

        # Verify the story generation driver was called
        self.mock_story_driver.start_story_gathering.assert_called_once()

        # Verify the response contains the expected text
        self.assertIn("interesting story", response)
        self.assertIn("make a video", response)

    def test_handle_story_info_needed(self):
        """Test handling a story information needed event."""
        # Create a story info needed event
        event = Event(
            event_type=EventType.STORY_INFO_NEEDED,
            data={
                'info_type': StoryInfoType.STORY_IDEA,
                'prompt': "Tell me a story idea",
                'current_state': StoryGenerationState.GATHERING_STORY_IDEA
            },
            source='story_generation_driver',
            target=self.conversation.user_id
        )

        # Handle the event
        self.conversation._handle_story_info_needed(event)

        # Verify the conversation state was updated
        self.assertTrue(self.conversation.waiting_for_ttv_info)
        self.assertEqual(self.conversation.current_ttv_info_type, StoryInfoType.STORY_IDEA)
        self.assertEqual(self.conversation.current_ttv_prompt, "Tell me a story idea")

    def test_handle_story_info_needed_cancelled(self):
        """Test handling a cancelled story information event."""
        # Create a cancelled story info event
        event = Event(
            event_type=EventType.STORY_INFO_NEEDED,
            data={
                'info_type': 'cancelled',
                'prompt': "No problem!",
                'current_state': StoryGenerationState.CANCELLED
            },
            source='story_generation_driver',
            target=self.conversation.user_id
        )

        # Handle the event
        self.conversation._handle_story_info_needed(event)

        # Verify the conversation state was reset
        self.assertFalse(self.conversation.waiting_for_ttv_info)
        self.assertIsNone(self.conversation.current_ttv_info_type)

    def test_handle_ttv_process_events(self):
        """Test handling TTV process events."""
        # Create a TTV process started event
        start_event = Event(
            event_type=EventType.TTV_PROCESS_STARTED,
            data={
                'config_path': '/path/to/config.json',
                'timestamp': 123456789,
                'estimated_duration': "5 minutes"
            },
            source='story_generation_driver',
            target=self.conversation.user_id
        )

        # Handle the event
        self.conversation._handle_ttv_process_started(start_event)

        # Verify the conversation state was updated
        self.assertTrue(self.conversation.ttv_process_running)
        self.assertEqual(self.conversation.ttv_estimated_duration, "5 minutes")

        # Create a TTV process completed event
        complete_event = Event(
            event_type=EventType.TTV_PROCESS_COMPLETED,
            data={
                'output_path': '/path/to/output.mp4',
                'timestamp': 123456789
            },
            source='story_generation_driver',
            target=self.conversation.user_id
        )

        # Handle the event
        self.conversation._handle_ttv_process_completed(complete_event)

        # Verify the conversation state was updated
        self.assertFalse(self.conversation.ttv_process_running)
        self.assertEqual(self.conversation.ttv_output_path, '/path/to/output.mp4')

        # Create a TTV process failed event
        fail_event = Event(
            event_type=EventType.TTV_PROCESS_FAILED,
            data={
                'error': 'Test error',
                'timestamp': 123456789
            },
            source='story_generation_driver',
            target=self.conversation.user_id
        )

        # Reset the conversation state
        self.conversation.ttv_process_running = True

        # Handle the event
        self.conversation._handle_ttv_process_failed(fail_event)

        # Verify the conversation state was updated
        self.assertFalse(self.conversation.ttv_process_running)
        self.assertEqual(self.conversation.ttv_error, 'Test error')

    def test_handle_ttv_info_response_valid(self):
        """Test handling a valid response to a TTV information request."""
        # Reset the mock pubsub
        self.mock_pubsub.reset_mock()

        # Set up the conversation state
        self.conversation.waiting_for_ttv_info = True
        self.conversation.current_ttv_info_type = StoryInfoType.STORY_IDEA

        # Process a valid response
        response = self.conversation._handle_ttv_info_response("A hero's journey through a magical land")

        # Verify the event was published
        self.mock_pubsub.publish.assert_called()

        # Get the last call arguments
        event = self.mock_pubsub.publish.call_args[0][0]
        self.assertEqual(event.event_type, EventType.STORY_INFO_RECEIVED)
        self.assertEqual(event.data['info_type'], StoryInfoType.STORY_IDEA)
        self.assertEqual(event.data['user_response'], "A hero's journey through a magical land")
        self.assertTrue(event.data['is_valid'])

        # Verify the conversation state was updated
        self.assertFalse(self.conversation.waiting_for_ttv_info)

        # Verify the response contains the expected text
        self.assertIn("Great story idea", response)

    def test_handle_ttv_info_response_decline(self):
        """Test handling a declined response to a TTV information request."""
        # Reset the mock pubsub
        self.mock_pubsub.reset_mock()

        # Set up the conversation state
        self.conversation.waiting_for_ttv_info = True
        self.conversation.current_ttv_info_type = StoryInfoType.STORY_IDEA

        # Process a declined response
        response = self.conversation._handle_ttv_info_response("No, I don't want to")

        # Verify the event was published
        self.mock_pubsub.publish.assert_called()

        # Get the last call arguments
        event = self.mock_pubsub.publish.call_args[0][0]
        self.assertEqual(event.event_type, EventType.STORY_INFO_RECEIVED)
        self.assertEqual(event.data['info_type'], StoryInfoType.STORY_IDEA)
        self.assertEqual(event.data['user_response'], "No, I don't want to")
        self.assertFalse(event.data['is_valid'])

        # Verify the conversation state was updated
        self.assertFalse(self.conversation.waiting_for_ttv_info)
        self.assertIsNone(self.conversation.current_ttv_info_type)

        # Verify the response contains the expected text
        self.assertIn("No problem", response)

    def test_handle_ttv_info_response_too_short(self):
        """Test handling a response that is too short."""
        # Reset the mock pubsub
        self.mock_pubsub.reset_mock()

        # Set up the conversation state
        self.conversation.waiting_for_ttv_info = True
        self.conversation.current_ttv_info_type = StoryInfoType.STORY_IDEA

        # Process a response that is too short
        response = self.conversation._handle_ttv_info_response("Yes")

        # Verify the conversation state was not updated
        self.assertTrue(self.conversation.waiting_for_ttv_info)

        # Verify the response contains the expected text
        self.assertIn("need a bit more information", response)

    def test_generate_ttv_status_response(self):
        """Test generating a response about the TTV process status."""
        # Set up the conversation state
        self.conversation.ttv_process_running = True
        self.conversation.ttv_estimated_duration = "5 minutes"

        # Generate a response for a status query
        response = self.conversation._generate_ttv_status_response("Is my video ready yet?")

        # Verify the response contains the expected text
        self.assertIn("still being generated", response)
        self.assertIn("5 minutes", response)

        # Generate a response for a non-status query
        self.mock_query_dispatcher.send_query.return_value = "I can help with that!"
        response = self.conversation._generate_ttv_status_response("Tell me a joke")

        # Verify the query dispatcher was called
        self.mock_query_dispatcher.send_query.assert_called_once_with("Tell me a joke")

        # Verify the response contains the expected text
        self.assertEqual(response, "I can help with that!")


if __name__ == "__main__":
    unittest.main()
