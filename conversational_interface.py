"""
Conversational interface module for GANGLIA.

This module provides a Conversation class that manages the interaction
with a user, replacing the direct chatbot functionality from ganglia.py.
"""

import time
import uuid
from typing import Optional, Dict, Any

from query_dispatch import ChatGPTQueryDispatcher
from session_logger import CLISessionLogger, SessionEvent
from audio_turn_indicator import UserTurnIndicator, AiTurnIndicator
from user_management import UserProfile
from logger import Logger
from pubsub import get_pubsub, Event, EventType
from story_generation_driver import StoryGenerationDriver, StoryInfoType, StoryGenerationState


class Conversation:
    """
    Manages the conversation with a user.

    This class replaces the direct chatbot functionality in ganglia.py with a more
    modular approach.
    """

    def __init__(self, query_dispatcher: ChatGPTQueryDispatcher,
                 tts, dictation, session_logger: Optional[CLISessionLogger] = None,
                 user_turn_indicator: Optional[UserTurnIndicator] = None,
                 ai_turn_indicator: Optional[AiTurnIndicator] = None,
                 hotword_manager = None):
        """
        Initialize a new conversation.

        Args:
            query_dispatcher: The ChatGPT query dispatcher to use
            tts: The text-to-speech interface to use
            dictation: The dictation interface to use
            session_logger: Optional session logger
            user_turn_indicator: Optional user turn indicator
            ai_turn_indicator: Optional AI turn indicator
            hotword_manager: Optional hotword manager
        """
        self.query_dispatcher = query_dispatcher
        self.tts = tts
        self.dictation = dictation
        self.session_logger = session_logger
        self.user_turn_indicator = user_turn_indicator
        self.ai_turn_indicator = ai_turn_indicator
        self.hotword_manager = hotword_manager

        # Initialize user profile
        self.user_profile = UserProfile()
        self.user_id = str(uuid.uuid4())  # Generate a unique ID for this user

        # Initialize pubsub
        self.pubsub = get_pubsub()

        # Initialize story generation driver
        self.story_driver = StoryGenerationDriver(query_dispatcher=query_dispatcher)

        # Set up event subscribers
        self._setup_pubsub_subscribers()

        # TTV state tracking
        self.waiting_for_ttv_info = False
        self.current_ttv_info_type = None
        self.ttv_process_running = False

        # Publish conversation started event
        self.pubsub.publish(Event(
            event_type=EventType.CONVERSATION_STARTED,
            data={'user_id': self.user_id},
            source='conversation',
            target=None  # Broadcast
        ))

        Logger.print_debug("Conversation initialized successfully.")

    def _setup_pubsub_subscribers(self):
        """Set up the PubSub subscribers for the conversation."""
        # Subscribe to story information needed events
        self.pubsub.subscribe(
            EventType.STORY_INFO_NEEDED,
            self._handle_story_info_needed
        )

        # Subscribe to TTV process events
        self.pubsub.subscribe(
            EventType.TTV_PROCESS_STARTED,
            self._handle_ttv_process_started
        )

        self.pubsub.subscribe(
            EventType.TTV_PROCESS_COMPLETED,
            self._handle_ttv_process_completed
        )

        self.pubsub.subscribe(
            EventType.TTV_PROCESS_FAILED,
            self._handle_ttv_process_failed
        )

    def _handle_story_info_needed(self, event: Event):
        """
        Handle a story information needed event.

        Args:
            event: The event to handle
        """
        if event.target and event.target != self.user_id:
            return

        # Store the information type and prompt for the next user interaction
        self.waiting_for_ttv_info = True
        self.current_ttv_info_type = event.data.get('info_type')
        self.current_ttv_prompt = event.data.get('prompt')

        # If this is a cancellation, reset the state
        if self.current_ttv_info_type == 'cancelled':
            self.waiting_for_ttv_info = False
            self.current_ttv_info_type = None

        Logger.print_debug(f"Waiting for TTV info: {self.current_ttv_info_type}")

    def _handle_ttv_process_started(self, event: Event):
        """
        Handle a TTV process started event.

        Args:
            event: The event to handle
        """
        if event.target != self.user_id:
            return

        self.ttv_process_running = True
        self.ttv_estimated_duration = event.data.get('estimated_duration', 'a few minutes')
        Logger.print_debug("TTV process started")

    def _handle_ttv_process_completed(self, event: Event):
        """
        Handle a TTV process completed event.

        Args:
            event: The event to handle
        """
        if event.target != self.user_id:
            return

        self.ttv_process_running = False
        self.ttv_output_path = event.data.get('output_path')
        Logger.print_debug(f"TTV process completed: {self.ttv_output_path}")

    def _handle_ttv_process_failed(self, event: Event):
        """
        Handle a TTV process failed event.

        Args:
            event: The event to handle
        """
        if event.target != self.user_id:
            return

        self.ttv_process_running = False
        self.ttv_error = event.data.get('error')
        Logger.print_debug(f"TTV process failed: {self.ttv_error}")

    def process_user_input(self, user_input: str) -> str:
        """
        Process user input and generate a response.

        Args:
            user_input: The user's input

        Returns:
            The response to the user
        """
        # Update user activity
        self.user_profile.update_activity()

        # Add the user input to the conversation history
        self.user_profile.add_conversation_entry({
            'role': 'user',
            'content': user_input
        })

        # Check for hotwords
        hotword_detected, hotword_phrase = self.hotword_manager.detect_hotwords(user_input) if self.hotword_manager else (False, None)

        # Handle TTV hotword
        if hotword_detected and "video" in user_input.lower():
            # Start the story generation process
            self.story_driver.start_story_gathering()
            response = "If you tell me an interesting story, I can try to make a video. Give me some broad strokes and I can fill in the details. What do you have in mind for the protagonist? The conflict? The resolution?"
        # Handle waiting for TTV information
        elif self.waiting_for_ttv_info:
            response = self._handle_ttv_info_response(user_input)
        # Handle TTV process running
        elif self.ttv_process_running:
            response = self._generate_ttv_status_response(user_input)
        # Handle regular hotwords
        elif hotword_detected:
            response = hotword_phrase
        # Regular conversation
        else:
            # Generate a response
            response = self.query_dispatcher.send_query(user_input)

        # Add the response to the conversation history
        self.user_profile.add_conversation_entry({
            'role': 'assistant',
            'content': response
        })

        # Log the interaction if session logger is available
        if self.session_logger:
            self.session_logger.log_session_interaction(
                SessionEvent(user_input, response)
            )

        return response

    def _handle_ttv_info_response(self, user_input: str) -> str:
        """
        Handle a response to a TTV information request.

        Args:
            user_input: The user's input

        Returns:
            The response to the user
        """
        # Check if the user is declining to provide information
        decline_indicators = ["no", "nope", "don't", "dont", "not interested", "stop", "cancel", "exit"]
        if any(indicator in user_input.lower() for indicator in decline_indicators):
            # Publish a story info received event with is_valid=False
            self.pubsub.publish(Event(
                event_type=EventType.STORY_INFO_RECEIVED,
                data={
                    'info_type': self.current_ttv_info_type,
                    'user_response': user_input,
                    'is_valid': False
                },
                source='conversation',
                target=self.user_id
            ))

            # Reset the state
            self.waiting_for_ttv_info = False
            self.current_ttv_info_type = None

            return "No problem! Let me know if you change your mind and want to create a video later."

        # Check if the response is too short or lacks substance
        if len(user_input.split()) < 3:
            return "I need a bit more information to create a good video. Could you elaborate a bit more?"

        # Publish a story info received event
        self.pubsub.publish(Event(
            event_type=EventType.STORY_INFO_RECEIVED,
            data={
                'info_type': self.current_ttv_info_type,
                'user_response': user_input,
                'is_valid': True
            },
            source='conversation',
            target=self.user_id
        ))

        # Reset the waiting state (new prompt will be set if needed)
        self.waiting_for_ttv_info = False

        # If we're waiting for the next prompt, return a transitional message
        if self.current_ttv_info_type == StoryInfoType.STORY_IDEA:
            return "Great story idea! Now, what artistic style are you thinking for the visual components? What about music styles for the background music and closing credits?"
        elif self.current_ttv_info_type == StoryInfoType.ARTISTIC_STYLE:
            return f"Thanks! I'm going to start creating your video now. This will take about {self.ttv_estimated_duration if hasattr(self, 'ttv_estimated_duration') else 'a few minutes'} to complete. I'll let you know when it's ready. In the meantime, we can continue our conversation. What would you like to talk about?"

        return "Thanks for the information! I'll use that to create your video."

    def _generate_ttv_status_response(self, user_input: str) -> str:
        """
        Generate a response about the TTV process status.

        Args:
            user_input: The user's input

        Returns:
            The response to the user
        """
        # Check if the user is asking about the video status
        status_indicators = ["video", "status", "ready", "done", "finished", "complete"]
        if any(indicator in user_input.lower() for indicator in status_indicators):
            return f"Your video is still being generated. This process takes about {self.ttv_estimated_duration if hasattr(self, 'ttv_estimated_duration') else 'a few minutes'} to complete. I'll let you know as soon as it's ready!"

        # Otherwise, just have a normal conversation
        return self.query_dispatcher.send_query(user_input)

    def user_turn(self, args) -> str:
        """
        Handle the user's turn in the conversation.

        Args:
            args: Command line arguments

        Returns:
            The user's input
        """
        while True:  # Keep asking for input until a non-empty prompt is received
            if self.user_turn_indicator:
                self.user_turn_indicator.input_in()

            got_input = False
            while not got_input:
                try:
                    prompt = self.dictation.getDictatedInput(args.device_index, interruptable=False) if self.dictation else input()

                    # If the input is empty restart the loop
                    if not prompt.strip():
                        continue

                    got_input = True  # Break out of the input loop

                    if self.user_turn_indicator:
                        self.user_turn_indicator.input_out()

                    return prompt
                except KeyboardInterrupt:
                    Logger.print_info("User killed program - exiting gracefully")
                    self.end()
                    exit(0)

            # Print a fun little prompt at the beginning of the user's turn
            Logger.print_info(self.dictation.generate_random_phrase())
            prompt = self.dictation.getDictatedInput(args.device_index, interruptable=False) if self.dictation else input()

    def ai_turn(self, user_input: str, args) -> str:
        """
        Handle the AI's turn in the conversation.

        Args:
            user_input: The user's input
            args: Command line arguments

        Returns:
            The AI's response
        """
        if self.ai_turn_indicator:
            self.ai_turn_indicator.input_in()

        response = self.process_user_input(user_input)

        if self.ai_turn_indicator:
            self.ai_turn_indicator.input_out()

        if self.tts:
            # Generate speech response
            _, file_path = self.tts.convert_text_to_speech(response)
            self.tts.play_speech_response(file_path, response)

        return response

    def should_end(self, user_input: str) -> bool:
        """
        Check if the conversation should end.

        Args:
            user_input: The user's input

        Returns:
            True if the conversation should end, False otherwise
        """
        return user_input and "goodbye" in user_input.strip().lower()

    def end(self):
        """End the conversation."""
        Logger.print_debug("Ending conversation")

        # Finalize the session logger if available
        if self.session_logger:
            self.session_logger.finalize_session()
