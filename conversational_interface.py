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
from logger import Logger
from pubsub import get_pubsub, Event, EventType
from story_generation_driver import StoryGenerationDriver, StoryInfoType, StoryGenerationState
from utils.performance_profiler import ConversationTimer, Timer


# Stub UserProfile until user management is implemented
class UserProfile:
    """Placeholder for future user management functionality."""
    def __init__(self):
        pass
    
    def update_activity(self):
        pass
    
    def add_conversation_entry(self, entry):
        pass


class Conversation:
    """
    Manages the conversation flow between user and AI.

    Handles user input, AI response generation, TTS playback, and integration
    with the TTV (Text-to-Video) system via pubsub events.
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

        # Performance tracking
        self.conversation_timer = ConversationTimer()

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

    def _stream_llm_and_play_audio(self, user_input: str) -> str:
        """
        Stream LLM response and play audio as soon as each sentence is ready.

        This provides the lowest latency by starting audio playback immediately
        when the first sentence's TTS is complete, while continuing to generate
        TTS for subsequent sentences in the background.

        Args:
            user_input: The user's input

        Returns:
            The complete AI response text
        """
        import threading
        import queue

        self.conversation_timer.mark_llm_start()

        # Update user activity and history
        self.user_profile.update_activity()
        self.user_profile.add_conversation_entry({
            'role': 'user',
            'content': user_input
        })

        # Queue for audio files ready to play
        audio_queue = queue.Queue()
        full_response = ""
        sentences = []
        tts_complete = threading.Event()

        def generate_tts_worker():
            """Background thread that generates TTS for each sentence."""
            try:
                for sentence in self.query_dispatcher.send_query_streaming(user_input):
                    sentences.append(sentence)
                    # Don't print here - will print during playback

                    # Generate TTS for this sentence immediately
                    if self.tts:
                        _, audio_file = self.tts.convert_text_to_speech(sentence)
                        # Only queue if TTS conversion succeeded
                        if audio_file is not None:
                            audio_queue.put((sentence, audio_file))
                        else:
                            Logger.print_warning(f"TTS conversion failed for sentence: {sentence[:50]}...")

                # Signal that all TTS generation is complete
                audio_queue.put(None)
                tts_complete.set()
            except Exception as e:
                Logger.print_error(f"Error in TTS worker: {e}")
                audio_queue.put(None)
                tts_complete.set()

        # Start TTS generation in background
        tts_thread = threading.Thread(target=generate_tts_worker, daemon=True)
        tts_thread.start()

        # Mark LLM streaming start (will be updated when first sentence arrives)
        first_sentence = True
        playback_started = False

        if self.ai_turn_indicator:
            self.ai_turn_indicator.input_out()

        # Play audio files as they become available
        while True:
            item = audio_queue.get()

            if item is None:
                # All done
                break

            sentence, audio_file = item
            full_response += sentence + " "

            if first_sentence:
                # Mark timing for first audio playback
                self.conversation_timer.mark_llm_end()
                self.conversation_timer.mark_tts_start()
                self.conversation_timer.mark_tts_end()
                self.conversation_timer.mark_playback_start()
                first_sentence = False
                playback_started = True

            # Print sentence as it's about to be played
            Logger.print_demon_output(sentence)

            # Play this sentence's audio immediately (suppress redundant output)
            if self.tts:
                self.tts.play_speech_response(audio_file, sentence, suppress_text_output=True)

        # Wait for TTS thread to complete
        tts_thread.join(timeout=5.0)

        response = full_response.strip()

        # Add to user profile
        self.user_profile.add_conversation_entry({
            'role': 'assistant',
            'content': response
        })

        # Log the interaction
        if self.session_logger:
            self.session_logger.log_session_interaction(
                SessionEvent(user_input, response)
            )

        return response

    def user_turn(self, args) -> str:
        """
        Handle the user's turn in the conversation.

        Args:
            args: Command line arguments

        Returns:
            The user's input
        """
        # TODO: REFACTOR THIS METHOD - It's become a catchall basket for all the weird things we want to do.
        # Need to break this into smaller, focused methods with clear responsibilities.
        # Consider: separate input handling, validation, and control flow into distinct helper methods.
        # Current complexity makes it hard to understand control flow and adds technical debt.
        
        # Reset conversation timer for new turn
        self.conversation_timer = ConversationTimer()
        self.conversation_timer.mark_user_start()

        while True:  # Keep asking for input until a non-empty prompt is received
            if self.user_turn_indicator:
                self.user_turn_indicator.input_in()

            got_input = False
            while not got_input:
                try:
                    # Print prompt indicator to show we're ready for input
                    print("> ", end="", flush=True)
                    self.conversation_timer.mark_stt_start()
                    prompt = self.dictation.getDictatedInput(args.device_index, interruptable=False) if self.dictation else input()
                    self.conversation_timer.mark_stt_end()
                    self.conversation_timer.mark_user_end()

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

    def ai_turn(self, user_input: str, args) -> str:
        """
        Handle the AI's turn in the conversation.

        Args:
            user_input: The user's input
            args: Command line arguments

        Returns:
            The AI's response
        """
        self.conversation_timer.mark_ai_start()

        if self.ai_turn_indicator:
            self.ai_turn_indicator.input_in()

        # Check for hotwords or special handling that doesn't use LLM streaming
        hotword_detected, _ = self.hotword_manager.detect_hotwords(user_input) if self.hotword_manager else (False, None)
        uses_special_handling = (hotword_detected or
                                 self.waiting_for_ttv_info or
                                 self.ttv_process_running)

        if uses_special_handling:
            # Use traditional non-streaming approach for special cases
            self.conversation_timer.mark_llm_start()
            query_result = self.process_user_input(user_input)
            self.conversation_timer.mark_llm_end()

            # Check if response includes audio
            if isinstance(query_result, tuple):
                response, audio_file = query_result
                # Audio from LLM - skip TTS entirely
                if self.ai_turn_indicator:
                    self.ai_turn_indicator.input_out()

                self.conversation_timer.mark_tts_start()  # Mark as 0 time
                self.conversation_timer.mark_tts_end()
                self.conversation_timer.mark_playback_start()

                if self.tts:
                    self.tts.play_speech_response(audio_file, response)
            else:
                response = query_result
                # Traditional TTS path
                if self.ai_turn_indicator:
                    self.ai_turn_indicator.input_out()

                if self.tts:
                    # Generate speech response
                    self.conversation_timer.mark_tts_start()
                    _, file_path = self.tts.convert_text_to_speech(response)
                    self.conversation_timer.mark_tts_end()

                    self.conversation_timer.mark_playback_start()
                    self.tts.play_speech_response(file_path, response)
        else:
            # Check if we should use audio output from LLM
            if self.query_dispatcher.audio_output:
                # Use LLM with integrated audio output (no streaming, no TTS)
                self.conversation_timer.mark_llm_start()

                # Update user activity and history
                self.user_profile.update_activity()
                self.user_profile.add_conversation_entry({
                    'role': 'user',
                    'content': user_input
                })

                # Get response (may include audio or just text if audio failed)
                query_result = self.query_dispatcher.send_query(user_input)

                # Check if audio was returned (tuple) or just text (fallback)
                if isinstance(query_result, tuple):
                    response, audio_file = query_result
                    has_audio = True
                else:
                    response = query_result
                    has_audio = False

                Logger.print_demon_output(response)

                self.conversation_timer.mark_llm_end()

                # Add to user profile
                self.user_profile.add_conversation_entry({
                    'role': 'assistant',
                    'content': response
                })

                # Log the interaction
                if self.session_logger:
                    self.session_logger.log_session_interaction(
                        SessionEvent(user_input, response)
                    )

                if self.ai_turn_indicator:
                    self.ai_turn_indicator.input_out()

                if has_audio:
                    # Skip TTS - audio came from LLM
                    self.conversation_timer.mark_tts_start()
                    self.conversation_timer.mark_tts_end()

                    # Play the audio directly
                    self.conversation_timer.mark_playback_start()
                    if self.tts:
                        self.tts.play_speech_response(audio_file, response)
                else:
                    # Fallback to TTS since audio wasn't returned
                    if self.tts:
                        self.conversation_timer.mark_tts_start()
                        _, file_path = self.tts.convert_text_to_speech(response)
                        self.conversation_timer.mark_tts_end()

                        self.conversation_timer.mark_playback_start()
                        self.tts.play_speech_response(file_path, response)

            else:
                # Use streaming LLM + streaming TTS with immediate playback
                response = self._stream_llm_and_play_audio(user_input)

        self.conversation_timer.mark_ai_end()

        # Print timing breakdown for this conversation turn
        self.conversation_timer.print_breakdown()

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
