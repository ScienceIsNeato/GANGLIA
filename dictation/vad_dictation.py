"""
Voice Activity Detection (VAD) Dictation Module

This module implements a cost-efficient two-stage dictation system:
1. Local Voice Activity Detection (FREE) - listens for ANY human speech
2. Google Cloud Speech streaming (PAID) - only activates when speech detected

Cost Reduction: ~95% savings ($20/day → $1-2/day)
"""

import pyaudio
import struct
import math
import json
import os
from google.cloud import speech_v1p1beta1 as speech
from logger import Logger
from threading import Timer
import time
from session_logger import SessionEvent

from .dictation import Dictation


class VoiceActivityDictation(Dictation):
    """
    Cost-efficient dictation using Voice Activity Detection.

    Two modes:
    - IDLE: Local audio processing, listening for ANY speech (FREE)
    - ACTIVE: Google Cloud Speech streaming (PAID, only when speech detected)
    """

    # Default configuration (overridden by vad_config.json if present)
    DEFAULT_CONFIG = {
        "energy_threshold": 500,
        "speech_confirmation_chunks": 3,
        "chunk_size": 1024,
        "silence_threshold": 2.5,
        "conversation_timeout": 30,
        "sample_rate": 16000,
        "channels": 1,
        "audio_buffer_seconds": 2.0  # How much audio to keep in buffer for prepending
    }

    # Constants
    FORMAT = pyaudio.paInt16
    MAX_RETRIES = 5
    RETRY_DELAY = 2

    def __init__(self, config_path=None):
        """Initialize the Voice Activity Detection dictation system."""
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

            # Google Speech client (only used when ACTIVE)
            self.client = speech.SpeechClient()

            # Audio stream
            self.audio = pyaudio.PyAudio()
            self.stream = None
            self.vad_stream = None  # Stream used during VAD detection
            self.transition_buffer = []  # Additional buffer for stream transition

            Logger.print_info("Voice Activity Dictation initialized - Cost-efficient mode enabled")
            Logger.print_info(f"VAD Settings: energy_threshold={self.ENERGY_THRESHOLD}, confirmation_chunks={self.SPEECH_CONFIRMATION_CHUNKS}")
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

        # Try to load config file
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)

                # Extract settings from nested structure
                config = {
                    "energy_threshold": file_config.get("detection", {}).get("energy_threshold", self.DEFAULT_CONFIG["energy_threshold"]),
                    "speech_confirmation_chunks": file_config.get("detection", {}).get("speech_confirmation_chunks", self.DEFAULT_CONFIG["speech_confirmation_chunks"]),
                    "chunk_size": file_config.get("detection", {}).get("chunk_size", self.DEFAULT_CONFIG["chunk_size"]),
                    "audio_buffer_seconds": file_config.get("detection", {}).get("audio_buffer_seconds", self.DEFAULT_CONFIG["audio_buffer_seconds"]),
                    "silence_threshold": file_config.get("timing", {}).get("silence_threshold", self.DEFAULT_CONFIG["silence_threshold"]),
                    "conversation_timeout": file_config.get("timing", {}).get("conversation_timeout", self.DEFAULT_CONFIG["conversation_timeout"]),
                    "sample_rate": file_config.get("audio", {}).get("sample_rate", self.DEFAULT_CONFIG["sample_rate"]),
                    "channels": file_config.get("audio", {}).get("channels", self.DEFAULT_CONFIG["channels"])
                }

                Logger.print_info(f"Loaded VAD config from: {config_path}")
                return config

            except Exception as e:
                Logger.print_error(f"Error loading VAD config from {config_path}: {e}")
                Logger.print_info("Using default VAD configuration")
                return self.DEFAULT_CONFIG
        else:
            Logger.print_info(f"VAD config not found at {config_path}, using defaults")
            return self.DEFAULT_CONFIG

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
        """
        Logger.print_info("💤 Idle mode - Listening for speech (cost-free)...")
        Logger.print_info("Start speaking to activate GANGLIA...")

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
                        Logger.print_info("🎤 Speech detected! Activating conversation mode...")
                        Logger.print_debug(f"Prepending {len(self.audio_buffer)} buffered audio chunks")
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
        """Get configuration for streaming recognition."""
        return speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.RATE,
                language_code="en-US",
                enable_automatic_punctuation=True,
                use_enhanced=True
            ),
            interim_results=True,
        )

    def generate_audio_chunks(self, stream):
        """
        Generator that yields audio chunks from the stream.
        Yields: buffered audio → transition audio → live stream
        This ensures no gaps in audio coverage.
        """
        # First, yield buffered audio chunks (captured before activation)
        if self.audio_buffer:
            Logger.print_debug(f"Prepending {len(self.audio_buffer)} buffered chunks to stream")
            for buffered_chunk in self.audio_buffer:
                yield buffered_chunk
            self.audio_buffer = []

        # Second, yield transition buffer (captured during stream setup)
        if self.transition_buffer:
            Logger.print_debug(f"Adding {len(self.transition_buffer)} transition chunks to stream")
            for transition_chunk in self.transition_buffer:
                yield transition_chunk
            self.transition_buffer = []

        # Finally, yield live audio
        while self.listening and self.mode == 'ACTIVE':
            yield stream.read(self.CHUNK_SIZE, exception_on_overflow=False)

    def done_speaking(self):
        """Mark the dictation as complete."""
        self.listening = False

    def transcribe_stream_active_mode(self, device_index, interruptable=False):
        """
        Active conversation mode - full Google Cloud streaming.
        Continues using the VAD stream to avoid gaps during transition.
        """
        Logger.print_info("🎤 Active conversation mode - listening...")

        # Continue buffering audio during stream setup to avoid gaps
        # Collect audio chunks while we set up the Google Speech stream
        if self.vad_stream:
            Logger.print_debug("Collecting transition audio to avoid gaps...")
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
            Logger.print_info("Conversation timeout - returning to idle listening mode")
            self.mode = 'IDLE'
            self.listening = False

        try:
            # Create streaming request
            requests = (
                speech.StreamingRecognizeRequest(audio_content=chunk)
                for chunk in self.generate_audio_chunks(stream)
            )

            responses = self.client.streaming_recognize(
                self.get_streaming_config(),
                requests
            )

            for response in responses:
                if not response.results or self.mode != 'ACTIVE':
                    continue

                result = response.results[0]
                if not result.alternatives:
                    continue

                current_input = result.alternatives[0].transcript.strip()

                # Reset conversation timeout on any speech
                if conversation_timer:
                    conversation_timer.cancel()
                conversation_timer = Timer(self.CONVERSATION_TIMEOUT, return_to_idle)
                conversation_timer.start()

                # Cancel silence timer
                if done_speaking_timer is not None:
                    done_speaking_timer.cancel()

                is_final = result.is_final

                if state == 'START':
                    Logger.print_user_input(f'\033[K{current_input}\r', end='', flush=True)
                    state = 'LISTENING'

                elif is_final:
                    finalized_transcript += f"{current_input} "
                    Logger.print_user_input(f'\033[K{current_input}', flush=True)
                    state = 'START'
                    done_speaking_timer = Timer(self.SILENCE_THRESHOLD, self.done_speaking)
                    done_speaking_timer.start()

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
