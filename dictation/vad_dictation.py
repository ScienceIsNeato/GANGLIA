"""
Voice Activity Detection (VAD) Dictation Module

This module implements a cost-efficient two-stage dictation system:
1. Local Voice Activity Detection (FREE) - listens for ANY human speech
2. STT streaming (PAID) - only activates when speech detected
"""

import pyaudio
import struct
import math
import json
import os
from logger import Logger
from threading import Timer
import time
from session_logger import SessionEvent
from utils.performance_profiler import is_timing_enabled

from .dictation import Dictation
from .stt_provider import STTProvider, GoogleSTTProvider

# Default VAD configuration (overridden by vad_config.json if present)
DEFAULT_VAD_CONFIG = {
    "energy_threshold": 500,
    "speech_confirmation_chunks": 3,
    "chunk_size": 1024,
    "silence_threshold": 2.5,
    "conversation_timeout": 30,
    "sample_rate": 16000,
    "channels": 1,
    "audio_buffer_seconds": 2.0  # How much audio to keep in buffer for prepending
}


class VoiceActivityDictation(Dictation):
    """
    Cost-efficient dictation using Voice Activity Detection.

    Two modes:
    - IDLE: Local audio processing, listening for ANY speech (FREE)
    - ACTIVE: STT streaming (PAID, only when speech detected)
    
    The STT provider is abstracted, allowing use of different services
    (Google, AWS, Azure, etc.) via the STTProvider interface.
    """

    # Constants
    FORMAT = pyaudio.paInt16
    MAX_RETRIES = 5
    RETRY_DELAY = 2

    def __init__(self, config_path=None, stt_provider: STTProvider = None):
        """
        Initialize the Voice Activity Detection dictation system.
        
        Args:
            config_path: Path to VAD configuration JSON file (optional)
            stt_provider: STT provider implementation (defaults to GoogleSTTProvider)
        """
        try:
            self.session_logger = None
            self.mode = 'IDLE'  # IDLE or ACTIVE
            self.listening = True

            # Load configuration
            self.config = self._load_config(config_path)

            # Apply configuration
            self.ENERGY_THRESHOLD = self.config["energy_threshold"]
            self.SPEECH_CONFIRMATION_CHUNKS = self.config["speech_confirmation_chunks"]
            self.CHUNK_SIZE = self.config["chunk_size"]
            self.SILENCE_THRESHOLD = self.config["silence_threshold"]
            self.CONVERSATION_TIMEOUT = self.config["conversation_timeout"]
            self.RATE = self.config["sample_rate"]
            self.CHANNELS = self.config["channels"]
            self.AUDIO_BUFFER_SECONDS = self.config.get("audio_buffer_seconds", 2.0)

            # Calculate buffer size (how many chunks to keep)
            self.buffer_max_chunks = int((self.AUDIO_BUFFER_SECONDS * self.RATE) / self.CHUNK_SIZE)

            # Audio buffer for prepending (stores recent chunks before activation)
            self.audio_buffer = []

            # STT provider (abstracted - can be Google, AWS, Azure, etc.)
            self.stt_provider = stt_provider or GoogleSTTProvider()
            self.stt_provider.initialize()

            # Audio stream
            self.audio = pyaudio.PyAudio()
            self.stream = None
            self.vad_stream = None  # Stream used during VAD detection
            self.transition_buffer = []  # Additional buffer for stream transition

            Logger.print_info("Voice Activity Dictation initialized - Cost-efficient mode enabled")
            Logger.print_info("💤 Listening for ANY human speech to activate...")

        except Exception as e:
            Logger.print_error(f"Error initializing VoiceActivityDictation: {e}")
            raise

    def _load_config(self, config_path=None):
        """Load VAD configuration from file or use defaults."""
        # Default config path
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'config',
                'vad_config.json'
            )

        # Copy template if config doesn't exist
        if not os.path.exists(config_path):
            template_path = config_path + '.template'
            if os.path.exists(template_path):
                Logger.print_info(f"No VAD config found - copying template to {config_path}")
                import shutil
                shutil.copy(template_path, config_path)

        # Try to load config file
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)

                # Extract settings from nested structure
                config = {
                    "energy_threshold": file_config.get("detection", {}).get("energy_threshold", DEFAULT_VAD_CONFIG["energy_threshold"]),
                    "speech_confirmation_chunks": file_config.get("detection", {}).get("speech_confirmation_chunks", DEFAULT_VAD_CONFIG["speech_confirmation_chunks"]),
                    "chunk_size": file_config.get("detection", {}).get("chunk_size", DEFAULT_VAD_CONFIG["chunk_size"]),
                    "audio_buffer_seconds": file_config.get("detection", {}).get("audio_buffer_seconds", DEFAULT_VAD_CONFIG["audio_buffer_seconds"]),
                    "silence_threshold": file_config.get("timing", {}).get("silence_threshold", DEFAULT_VAD_CONFIG["silence_threshold"]),
                    "conversation_timeout": file_config.get("timing", {}).get("conversation_timeout", DEFAULT_VAD_CONFIG["conversation_timeout"]),
                    "sample_rate": file_config.get("audio", {}).get("sample_rate", DEFAULT_VAD_CONFIG["sample_rate"]),
                    "channels": file_config.get("audio", {}).get("channels", DEFAULT_VAD_CONFIG["channels"])
                }

                Logger.print_info(f"Loaded VAD config from: {config_path}")
                return config

            except Exception as e:
                Logger.print_error(f"Error loading VAD config from {config_path}: {e}")
                Logger.print_info("Using default VAD configuration")
                return DEFAULT_VAD_CONFIG
        else:
            Logger.print_info(f"VAD config not found at {config_path}, using defaults")
            return DEFAULT_VAD_CONFIG

    def calculate_energy(self, audio_chunk):
        """
        Calculate the energy (volume) of an audio chunk.
        Used for basic voice activity detection.
        """
        try:
            # Convert bytes to integers
            audio_data = struct.unpack(f'{len(audio_chunk)//2}h', audio_chunk)
            # Calculate RMS energy
            energy = math.sqrt(sum(x**2 for x in audio_data) / len(audio_data))
            return energy
        except Exception:
            return 0

    def listen_for_speech(self, device_index):
        """
        Listen for ANY human speech using local Voice Activity Detection.

        Strategy:
        1. Monitor audio energy locally (FREE)
        2. When speech energy detected, confirm it's sustained
        3. Immediately enter ACTIVE mode and start Google streaming
        4. Keep collecting audio during transition to avoid gaps

        This is simpler and more natural than wake word detection.
        
        TODO: Implement auto-adaptive VAD threshold (Issue #62)
        Background energy fluctuates daily (wind, traffic, etc.). A background
        thread should dynamically adjust energy_threshold to optimize for both
        sensitivity and cost (fewer false alarms = less STT API usage).
        """

        # Open audio stream
        self.vad_stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.CHUNK_SIZE
        )

        high_energy_chunks = 0

        try:
            while self.mode == 'IDLE':
                # Read audio chunk
                chunk = self.vad_stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                energy = self.calculate_energy(chunk)

                # Add to rolling buffer (keep last N seconds of audio)
                self.audio_buffer.append(chunk)
                if len(self.audio_buffer) > self.buffer_max_chunks:
                    self.audio_buffer.pop(0)  # Remove oldest chunk

                # Simple Voice Activity Detection
                if energy > self.ENERGY_THRESHOLD:
                    high_energy_chunks += 1

                    # Confirm sustained speech (not just a noise spike)
                    if high_energy_chunks >= self.SPEECH_CONFIRMATION_CHUNKS:
                        print("🎤", flush=True)
                        self.mode = 'ACTIVE'
                        # DON'T close stream yet - keep it for transition buffer
                        return True
                else:
                    # Reset counter if energy drops
                    high_energy_chunks = 0

        except KeyboardInterrupt:
            Logger.print_info("Voice detection interrupted")
            if self.vad_stream:
                self.vad_stream.close()
                self.vad_stream = None
            return False
        except Exception as e:
            Logger.print_error(f"Error in voice detection: {e}")
            if self.vad_stream:
                self.vad_stream.close()
                self.vad_stream = None
            return False

        if self.vad_stream:
            self.vad_stream.close()
            self.vad_stream = None
        return False


    def get_streaming_config(self):
        """Get configuration for streaming recognition from the STT provider."""
        return self.stt_provider.get_streaming_config(sample_rate=self.RATE)

    def generate_audio_chunks(self, stream):
        """
        Generator that yields audio chunks from the stream.
        Yields: buffered audio → transition audio → live stream
        This ensures no gaps in audio coverage.

        CRITICAL: Must check self.listening/self.mode frequently to avoid
        hitting Google's 305-second streaming limit.
        """
        # First, yield buffered audio chunks (captured before activation)
        if self.audio_buffer:
            for buffered_chunk in self.audio_buffer:
                if not self.listening or self.mode != 'ACTIVE':
                    return  # Stop immediately if timeout occurs
                yield buffered_chunk
            self.audio_buffer = []

        # Second, yield transition buffer (captured during stream setup)
        if self.transition_buffer:
            for transition_chunk in self.transition_buffer:
                if not self.listening or self.mode != 'ACTIVE':
                    return  # Stop immediately if timeout occurs
                yield transition_chunk
            self.transition_buffer = []

        # Finally, yield live audio
        # Check flags before EACH read to ensure prompt timeout handling
        while self.listening and self.mode == 'ACTIVE':
            try:
                # Use a shorter timeout on the read so we can check flags frequently
                chunk = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)

                # Double-check flags after potentially blocking read
                if not self.listening or self.mode != 'ACTIVE':
                    return  # Stop immediately

                yield chunk
            except Exception as e:
                Logger.print_error(f"Error reading audio chunk: {e}")
                return  # Stop on any error

    def done_speaking(self):
        """Mark the dictation as complete."""
        if is_timing_enabled():
            Logger.print_perf(f"⏱️  [STT] Silence detected! User finished speaking.")
        self.listening = False

    def transcribe_stream_active_mode(self, device_index, interruptable=False):
        """
        Active conversation mode - full Google Cloud streaming.
        Continues using the VAD stream to avoid gaps during transition.
        """
        # Continue buffering audio during stream setup to avoid gaps
        # Collect audio chunks while we set up the Google Speech stream
        if self.vad_stream:
            for _ in range(5):  # Collect ~5 chunks during setup (~300ms)
                try:
                    chunk = self.vad_stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                    self.transition_buffer.append(chunk)
                except Exception:
                    break

        # Now we can close the VAD stream and use the main stream
        stream = self.vad_stream  # Reuse the existing stream
        self.vad_stream = None  # Clear reference

        done_speaking_timer = None
        conversation_timer = None
        state = 'START'
        finalized_transcript = ''

        self.listening = True

        def return_to_idle():
            """Return to idle listening mode after timeout."""
            print("💤", flush=True)
            self.mode = 'IDLE'
            self.listening = False

        try:
            # Start conversation timeout immediately when entering ACTIVE mode
            # If no actual speech detected within timeout, return to IDLE
            conversation_timer = Timer(self.CONVERSATION_TIMEOUT, return_to_idle)
            conversation_timer.start()

            # Stream audio to STT provider
            responses = self.stt_provider.stream_recognize(
                self.get_streaming_config(),
                self.generate_audio_chunks(stream)
            )

            for response in responses:
                # CRITICAL: Check timeout flags on EVERY iteration
                # Generator stopping isn't enough - must actively break from response loop
                if not self.listening or self.mode != 'ACTIVE':
                    Logger.print_info("🌬️  Thought I heard something - must have been the wind")
                    break

                # Extract transcript from provider-specific response
                transcript, is_final = self.stt_provider.extract_transcript(response)
                if not transcript:
                    continue

                current_input = transcript.strip()

                # Reset conversation timeout ONLY on actual speech (not ambient noise)
                # This prevents ambient noise from keeping the Google stream alive indefinitely
                if current_input:  # Only if there's actual transcript content
                    if conversation_timer:
                        conversation_timer.cancel()
                    conversation_timer = Timer(self.CONVERSATION_TIMEOUT, return_to_idle)
                    conversation_timer.start()

                # Cancel silence timer
                if done_speaking_timer is not None:
                    done_speaking_timer.cancel()

                # Handle final transcripts (complete utterances)
                if is_final:
                    finalized_transcript += f"{current_input} "
                    Logger.print_user_input(f'\033[K{current_input}', flush=True)
                    state = 'START'

                    # Mark when we start waiting for silence
                    if is_timing_enabled():
                        Logger.print_perf(f"⏱️  [STT] Final transcript received, waiting {self.SILENCE_THRESHOLD}s for silence...")

                    done_speaking_timer = Timer(self.SILENCE_THRESHOLD, self.done_speaking)
                    done_speaking_timer.start()

                # Handle interim transcripts (partial results)
                elif state == 'START':
                    Logger.print_user_input(f'\033[K{current_input}\r', end='', flush=True)
                    state = 'LISTENING'

                elif state == 'LISTENING':
                    Logger.print_user_input(f'\033[K{current_input}', end='\r', flush=True)

            # Clean up timers
            if done_speaking_timer:
                done_speaking_timer.cancel()
            if conversation_timer:
                conversation_timer.cancel()

        except Exception as e:
            Logger.print_error(f"Error in active mode: {e}")
            if conversation_timer:
                conversation_timer.cancel()
        finally:
            stream.close()

        return finalized_transcript

    def getDictatedInput(self, device_index, interruptable=False):
        """
        Main entry point for dictation.

        Two-stage process:
        1. If IDLE: Listen for ANY speech using local VAD (free)
        2. If ACTIVE: Stream to Google (paid, but only when talking)
        """
        # Stage 1: Voice Activity Detection (if in IDLE mode)
        if self.mode == 'IDLE':
            speech_detected = self.listen_for_speech(device_index)
            if not speech_detected:
                return ""  # User interrupted or error

        # Stage 2: Active conversation (Google Cloud streaming)
        if self.mode == 'ACTIVE':
            transcript = self.transcribe_stream_active_mode(device_index, interruptable)

            # After conversation, return to idle mode
            self.mode = 'IDLE'

            return transcript

        return ""

    def set_session_logger(self, session_logger):
        """Set the session logger."""
        self.session_logger = session_logger

    def generate_random_phrase(self):
        """Generate a random listening prompt phrase."""
        import random
        phrases = [
            "Speak, mortal...",
            "I'm listening...",
            "Continue...",
            "Go on...",
            "Yes?",
        ]
        return random.choice(phrases)
