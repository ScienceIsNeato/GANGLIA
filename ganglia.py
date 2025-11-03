"""
GANGLIA - A conversational agent with text-to-video capabilities.

This module serves as the main entry point for the GANGLIA system, initializing
the necessary components and managing the conversation loop.
"""

import time
import sys
import os
import signal
import warnings
from logger import Logger
from parse_inputs import load_config, parse_tts_interface, parse_dictation_type
from query_dispatch import ChatGPTQueryDispatcher
from session_logger import CLISessionLogger, SessionEvent
from audio_turn_indicator import UserTurnIndicator, AiTurnIndicator
from conversational_interface import Conversation
from hotwords import HotwordManager
from conversation_context import ContextManager
from utils import get_tempdir
from ttv.ttv import text_to_video
from fetch_and_display_logs import display_logs
from pubsub import get_pubsub
from utils.performance_profiler import enable_timing_analysis

# Suppress gRPC fork warnings
os.environ['GRPC_ENABLE_FORK_SUPPORT'] = '0'
warnings.filterwarnings('ignore', message='.*fork_posix.*')


def get_config_path():
    """Get the path to the config directory relative to the project root."""
    return os.path.join(os.path.dirname(__file__), 'config', 'ganglia_config.json')


def initialize_components(args):
    """
    Initialize all components needed for the GANGLIA system.

    Args:
        args: Command line arguments

    Returns:
        Tuple of initialized components
    """
    config_path = get_config_path()

    # Initialize session logger
    session_logger = None
    if not args.suppress_session_logging:
        try:
            session_logger = CLISessionLogger(options=args)
            Logger.print_debug("CLISessionLogger initialized successfully.")
        except Exception as e:
            Logger.print_error(f"Failed to initialize CLISessionLogger: {e}")

    # Initialize turn indicators
    user_turn_indicator = None
    ai_turn_indicator = None
    if args.enable_turn_indicators:
        try:
            user_turn_indicator = UserTurnIndicator()
            ai_turn_indicator = AiTurnIndicator()
            Logger.print_debug("Turn indicators initialized successfully.")
        except Exception as e:
            Logger.print_error(f"Failed to initialize turn indicators: {e}")

    # Initialize TTS
    tts = None
    try:
        tts = parse_tts_interface(args.tts_interface, apply_effects=args.audio_effects)
        # The GoogleTTS class doesn't have a set_voice_id method
        # It accepts voice_id directly in the convert_text_to_speech method
        # We'll pass the voice_id when calling convert_text_to_speech
        if args.audio_effects:
            Logger.print_info("🎸 Audio effects enabled (pitch down, reverb, bass boost)")
        Logger.print_debug("TTS initialized successfully.")
    except Exception as e:
        Logger.print_error(f"Failed to initialize TTS: {e}")

    # Initialize dictation
    dictation = None
    try:
        dictation = parse_dictation_type(args.dictation_type)
        Logger.print_debug("Dictation initialized successfully.")
    except Exception as e:
        Logger.print_error(f"Failed to initialize dictation: {e}")

    # Initialize query dispatcher
    query_dispatcher = None
    try:
        query_dispatcher = ChatGPTQueryDispatcher(
            config_file_path=config_path,
            audio_output=args.audio_output,
            audio_voice=args.audio_voice
        )
        if args.audio_output:
            Logger.print_info(f"🎵 Audio output enabled (gpt-4o-audio-preview with voice: {args.audio_voice})")
        Logger.print_debug("ChatGPTQueryDispatcher initialized successfully.")
    except Exception as e:
        Logger.print_error(f"Failed to initialize ChatGPTQueryDispatcher: {e}")

    # Initialize hotword manager
    try:
        hotword_manager = HotwordManager(config_path)
        Logger.print_debug("HotwordManager initialized successfully.")
    except Exception as e:
        Logger.print_error(f"Failed to initialize HotwordManager: {e}")
        hotword_manager = None

    # ContextManager setup
    context_manager = None
    try:
        context_manager = ContextManager(config_path)
        Logger.print_debug("ContextManager initialized successfully.")

        # Feed the context into the query dispatcher
        query_dispatcher.add_system_context(context_manager.context)

    except Exception as e:
        Logger.print_error(f"Failed to initialize ContextManager: {e}")

    # Initialize pubsub system
    pubsub = get_pubsub()
    pubsub.start()
    Logger.print_debug("PubSub system initialized successfully.")

    return (
        user_turn_indicator,
        ai_turn_indicator,
        session_logger,
        tts,
        dictation,
        query_dispatcher,
        hotword_manager
    )


def signal_handler(sig, frame):
    """Handle signal interrupts."""
    Logger.print_info("User killed program - exiting gracefully")
    sys.exit(0)


def main():
    """Main entry point for the GANGLIA system."""
    # Load command line arguments
    args = load_config()

    # Enable debug logging if requested
    if args.debug:
        Logger.enable_debug()
        Logger.print_debug("Debug logging enabled")

    # Enable timing analysis if requested
    if args.timing_analysis:
        enable_timing_analysis()
        Logger.enable_timestamps()  # Enable timestamps for timing analysis
        Logger.print_perf("=" * 60)
        Logger.print_perf("TIMING ANALYSIS ENABLED")
        Logger.print_perf("Detailed conversation pipeline timing will be logged")
        Logger.print_perf("Timestamps enabled")
        Logger.print_perf("=" * 60)

    # Create temp directory if it doesn't exist
    get_tempdir()

    # Display logs if requested and exit
    if args.display_log_hours:
        display_logs(args.display_log_hours)
        return

    # Initialize components
    initialization_failed = True
    while initialization_failed:
        try:
            components = initialize_components(args)
            user_turn_indicator, ai_turn_indicator, session_logger, tts, dictation, \
                query_dispatcher, hotword_manager = components

            if dictation:
                dictation.set_session_logger(session_logger)

            initialization_failed = False
        except Exception as e:
            Logger.print_error(f"Error initializing components: {e}")
            time.sleep(20)

    # Handle TTV-only mode
    if args.ttv_config:
        # Process text-to-video generation without conversation
        Logger.print_info("Processing text-to-video generation...")
        tts_client = parse_tts_interface(args.tts_interface, apply_effects=args.audio_effects)
        text_to_video(
            config_path=args.ttv_config,
            skip_generation=args.skip_image_generation,
            tts=tts_client,
            query_dispatcher=query_dispatcher
        )
        sys.exit(0)

    # Initialize conversation
    conversation = Conversation(
        query_dispatcher=query_dispatcher,
        tts=tts,
        dictation=dictation,
        session_logger=session_logger,
        user_turn_indicator=user_turn_indicator,
        ai_turn_indicator=ai_turn_indicator,
        hotword_manager=hotword_manager
    )

    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Display legend
    Logger.print_legend()
    Logger.print_info("Starting session with GANGLIA. To stop, simply say \"Goodbye\"")

    # Main conversation loop
    while True:
        try:
            # User's turn
            user_input = conversation.user_turn(args)

            # Check if conversation should end
            if conversation.should_end(user_input):
                Logger.print_info("User ended conversation")
                # One final AI turn to say goodbye
                conversation.ai_turn(user_input, args)
                conversation.end()
                break

            # AI's turn
            conversation.ai_turn(user_input, args)

        except Exception as e:
            # Handle expected exceptions
            if 'Exceeded maximum allowed stream duration' in str(e) or 'Long duration elapsed without audio' in str(e):
                continue
            else:
                # Log unexpected exceptions
                Logger.print_error(f"Error in conversation loop: {e}")
                if session_logger:
                    session_logger.log_session_interaction(
                        SessionEvent(
                            user_input="SYSTEM ERROR",
                            response_output=f"Exception occurred: {str(e)}"
                        )
                    )

    Logger.print_info("Thanks for chatting! Have a great day!")


if __name__ == "__main__":
    main()
