#!/usr/bin/env python3
"""
Working OpenAI Realtime API test with proper audio playback.
"""

import asyncio
import json
import math
import os
import signal
import subprocess
import sys
import websockets
import base64
import pyaudio
import queue
import time
import threading
from typing import Optional

# Import GANGLIA libraries
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from logger import Logger

class WorkingRealtimeTest:
    """Working version with proper audio playback."""

    def play_startup_beep(self):
        """Play a friendly startup beep to indicate GANGLIA is alive."""
        try:
            Logger.print_info("🔔 Playing startup beep...")

            # Generate a pleasant two-tone beep
            duration = 0.3  # seconds
            sample_rate = 24000

            # First tone (higher pitch)
            freq1 = 800  # Hz
            samples1 = int(sample_rate * duration)
            t1 = [i / sample_rate for i in range(samples1)]
            wave1 = [int(16383 * math.sin(2 * math.pi * freq1 * t)) for t in t1]

            # Second tone (lower pitch)
            freq2 = 600  # Hz
            samples2 = int(sample_rate * duration)
            t2 = [i / sample_rate for i in range(samples2)]
            wave2 = [int(16383 * math.sin(2 * math.pi * freq2 * t)) for t in t2]

            # Convert to bytes
            beep1 = b''.join([wave1[i].to_bytes(2, byteorder='little', signed=True) for i in range(samples1)])
            beep2 = b''.join([wave2[i].to_bytes(2, byteorder='little', signed=True) for i in range(samples2)])

            # Create a temporary blocking stream for the beep
            if self.audio:
                Logger.print_info("🎵 BEEP!")
                temp_stream = self.audio.open(
                    format=self.audio_format,
                    channels=self.channels,
                    rate=sample_rate,
                    output=True,
                    frames_per_buffer=1024
                )

                temp_stream.write(beep1)
                time.sleep(0.1)  # Short pause
                Logger.print_info("🎵 BOOP!")
                temp_stream.write(beep2)

                temp_stream.stop_stream()
                temp_stream.close()
                Logger.print_info("✅ Startup beep complete!")
            else:
                Logger.print_warning("⚠️ Audio not ready for startup beep")

        except Exception as e:
            Logger.print_error(f"Failed to play startup beep: {e}")

    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        # Audio configuration
        self.sample_rate = 24000
        self.chunk_size = 1024
        self.audio_format = pyaudio.paInt16
        self.channels = 1

        # Queues for thread-safe communication
        self.audio_queue = queue.Queue(maxsize=100)
        self.output_queue = queue.Queue(maxsize=500)  # Larger for audio output

        # PyAudio setup
        self.audio = pyaudio.PyAudio()
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None

        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.running = False
        self.connected = False

        # Audio playback thread
        self.playback_thread = None

        # Debug: Save audio responses
        self.response_counter = 0
        self.current_response_audio = b""
        self.current_response_text = ""

        # Real-time streaming audio playback with proper buffering
        self.streaming_audio_queue = queue.Queue()
        self.audio_output_stream = None
        self.is_streaming_audio = False

        # Audio buffer for smooth playback at correct speed
        self.audio_playback_buffer = b""
        self.buffer_lock = threading.Lock()

        # Track subprocess processes for cleanup
        self.active_processes = []

        # Audio playback lock to prevent overlapping
        self.playback_lock = threading.Lock()

        # Audio feedback prevention with enhanced VAD
        self.is_playing_audio = False
        self.audio_feedback_lock = threading.Lock()
        self.playback_end_time = 0  # Track when playback ends
        self.vad_cooldown_ms = 500  # Wait 500ms after playback before accepting input

        Logger.print_info("WorkingRealtimeTest initialized")

    def audio_input_callback(self, in_data, frame_count, time_info, status):
        """Audio input callback with enhanced feedback prevention."""
        if self.running and self.connected:
            current_time = time.time() * 1000  # Convert to milliseconds

            # Enhanced feedback prevention with cooldown period
            with self.audio_feedback_lock:
                # Check if we're currently playing OR in cooldown period after playback
                time_since_playback = current_time - self.playback_end_time
                in_cooldown = time_since_playback < self.vad_cooldown_ms

                if not self.is_streaming_audio and not in_cooldown:
                    try:
                        self.audio_queue.put_nowait(in_data)
                    except queue.Full:
                        pass  # Drop audio if queue is full
        return (in_data, pyaudio.paContinue)

    def audio_output_callback(self, in_data, frame_count, time_info, status):
        """Real-time streaming audio output callback with proper timing."""
        bytes_needed = frame_count * 2  # 2 bytes per sample for 16-bit audio

        with self.buffer_lock:
            # Add new chunks to buffer
            chunks_added = 0
            try:
                while not self.streaming_audio_queue.empty():
                    chunk = self.streaming_audio_queue.get_nowait()
                    self.audio_playback_buffer += chunk
                    chunks_added += 1
            except queue.Empty:
                pass

            if chunks_added > 0:
                Logger.print_debug(f"🔊 Added {chunks_added} chunks to buffer (total: {len(self.audio_playback_buffer)} bytes)")

            # Extract exactly what we need for this callback
            if len(self.audio_playback_buffer) >= bytes_needed:
                # We have enough data - play at normal speed
                audio_data = self.audio_playback_buffer[:bytes_needed]
                self.audio_playback_buffer = self.audio_playback_buffer[bytes_needed:]
                Logger.print_debug(f"🎵 Playing {len(audio_data)} bytes (buffer remaining: {len(self.audio_playback_buffer)})")
                return (audio_data, pyaudio.paContinue)
            else:
                # Not enough data - play what we have and pad with silence
                if self.audio_playback_buffer:
                    audio_data = self.audio_playback_buffer + b'\x00' * (bytes_needed - len(self.audio_playback_buffer))
                    Logger.print_debug(f"🔇 Playing {len(self.audio_playback_buffer)} bytes + {bytes_needed - len(self.audio_playback_buffer)} silence")
                    self.audio_playback_buffer = b""
                else:
                    audio_data = b'\x00' * bytes_needed  # Pure silence

                    # CRITICAL FIX: Reset streaming flag when buffer is empty (playing pure silence)
                    if self.is_streaming_audio:
                        Logger.print_info("🔊 Audio buffer empty - ending stream and starting cooldown")
                        # Use the same lock as audio input callback to prevent race condition
                        with self.audio_feedback_lock:
                            self.is_streaming_audio = False
                            self.playback_end_time = time.time() * 1000

                    # Only log silence occasionally to avoid spam
                    if hasattr(self, '_silence_count'):
                        self._silence_count += 1
                        if self._silence_count % 100 == 0:  # Log every 100th silence callback
                            Logger.print_debug(f"🔇 Playing silence (callback #{self._silence_count})")
                    else:
                        self._silence_count = 1
                        Logger.print_debug("🔇 Playing silence (no buffer data)")

                return (audio_data, pyaudio.paContinue)

    def audio_playback_worker(self):
        """Separate thread for audio playback using ffplay."""
        Logger.print_debug("🎵 Audio playback worker started")
        while self.running:
            try:
                # Get audio data from queue with timeout
                Logger.print_debug("🎧 Waiting for audio data...")
                audio_data = self.output_queue.get(timeout=0.1)
                Logger.print_debug(f"🎧 Got audio data: {len(audio_data)} bytes")

                # Play audio using ffplay (much simpler and we know it works)
                if audio_data:
                    Logger.print_debug("🎵 Calling play_audio_with_ffplay...")
                    with self.playback_lock:  # Ensure sequential playback
                        Logger.print_debug("🔒 Acquired playback lock")

                        # Set feedback prevention flag
                        with self.audio_feedback_lock:
                            self.is_playing_audio = True
                            Logger.print_debug("🔇 Audio input muted during playback")

                        try:
                            self.play_audio_with_ffplay(audio_data)
                        finally:
                            # Clear feedback prevention flag and set cooldown timer
                            with self.audio_feedback_lock:
                                self.is_playing_audio = False
                                self.playback_end_time = time.time() * 1000  # Set end time for cooldown
                                Logger.print_debug(f"🎤 Audio input resumed (cooldown: {self.vad_cooldown_ms}ms)")

                        Logger.print_debug("🔓 Released playback lock")
                    Logger.print_debug("🎵 play_audio_with_ffplay completed")
                else:
                    Logger.print_warning("⚠️ Empty audio data received")

            except queue.Empty:
                # This is normal - just means no audio to play right now
                pass
            except Exception as e:
                Logger.print_error(f"Playback error: {e}")
                import traceback
                Logger.print_error(f"Full traceback: {traceback.format_exc()}")
        Logger.print_debug("🎵 Audio playback worker stopped")

    def play_audio_with_ffplay(self, audio_data: bytes):
        """Play audio using ffplay."""
        try:
            import tempfile
            import subprocess
            import wave
            import os

            Logger.print_debug(f"🎵 Starting audio playback - {len(audio_data)} bytes")

            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
                Logger.print_debug(f"📁 Creating temp file: {temp_filename}")

            # Write WAV file completely before playing
            with wave.open(temp_filename, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data)
            # File is now completely written and closed

            Logger.print_debug(f"💾 WAV file created: {os.path.getsize(temp_filename)} bytes")

            # Play using ffplay with verbose output for debugging
            Logger.print_info(f"🔊 Playing audio with ffplay: {temp_filename}")

            # Run ffplay and capture output for debugging
            process = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', temp_filename],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, preexec_fn=os.setsid)
            self.active_processes.append(process)

            # Wait for completion and get result
            stdout, stderr = process.communicate()
            result_code = process.returncode

            # Remove from active processes
            if process in self.active_processes:
                self.active_processes.remove(process)

            Logger.print_debug(f"🎬 ffplay return code: {result_code}")
            if stdout:
                Logger.print_debug(f"🎬 ffplay stdout: {stdout}")
            if stderr:
                Logger.print_debug(f"🎬 ffplay stderr: {stderr}")

            if result_code == 0:
                Logger.print_info("✅ Audio played successfully")
            else:
                Logger.print_error(f"❌ ffplay failed with code {result_code}")

            # Clean up
            Logger.print_debug(f"🗑️ Cleaning up temp file: {temp_filename}")
            os.unlink(temp_filename)

        except Exception as e:
            Logger.print_error(f"ffplay audio playback failed: {e}")
            import traceback
            Logger.print_error(f"Full traceback: {traceback.format_exc()}")

    def save_audio_response(self, audio_data: bytes, filename: str):
        """Save audio response to WAV file for debugging."""
        try:
            import wave

            # Create WAV file
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit audio = 2 bytes
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data)

            Logger.print_debug(f"Saved {len(audio_data)} bytes to {filename}")

        except Exception as e:
            Logger.print_error(f"Failed to save audio: {e}")

    async def connect_and_configure(self):
        """Connect with proper configuration."""
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

        try:
            Logger.print_info("Connecting to OpenAI Realtime API...")
            self.websocket = await websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            self.connected = True
            Logger.print_info("✅ Connected!")

            # Wait for connection to stabilize
            await asyncio.sleep(0.5)

            # Configure session
            config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": """You are GANGLIA, the Fallen King of Halloween.
                    You live in a coffin and are the embodiment of Halloween.
                    Keep responses very short - just 1-2 sentences max.
                    Be creepy and unsettling but helpful.""",
                    "voice": "alloy",  # Using alloy voice
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 800
                    },
                    "tools": [],
                    "tool_choice": "auto",
                    "temperature": 0.8,
                    "max_response_output_tokens": 4096
                }
            }

            Logger.print_info("Configuring GANGLIA...")
            await self.websocket.send(json.dumps(config))
            Logger.print_info("🎃 GANGLIA configured")

        except Exception as e:
            Logger.print_error(f"Connection failed: {e}")
            self.connected = False
            raise

    def setup_audio(self):
        """Set up both input and output audio streams."""
        Logger.print_info("Setting up audio streams...")

        try:
            # Find the best output device
            output_device_index = None
            for i in range(self.audio.get_device_count()):
                info = self.audio.get_device_info_by_index(i)
                if info['maxOutputChannels'] > 0:
                    Logger.print_debug(f"Output device {i}: {info['name']} - {info['maxOutputChannels']} channels")
                    if "MacBook Pro Speakers" in info['name'] or output_device_index is None:
                        output_device_index = i

            if output_device_index is not None:
                Logger.print_info(f"🔊 Using output device: {self.audio.get_device_info_by_index(output_device_index)['name']}")

            # Input stream (microphone)
            self.input_stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self.audio_input_callback
            )

            # Real-time streaming output stream (replaces ffplay for better streaming)
            self.audio_output_stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self.audio_output_callback,
                output_device_index=output_device_index
            )

            Logger.print_info("🎧 Audio streams ready")

            # Play startup beep to confirm audio is working
            self.play_startup_beep()

        except Exception as e:
            Logger.print_error(f"Audio setup failed: {e}")
            raise

    async def send_audio_loop(self):
        """Send audio to API."""
        while self.running and self.connected:
            try:
                # Get audio data
                try:
                    audio_data = self.audio_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue

                # Encode and send
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                event = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                }

                await self.websocket.send(json.dumps(event))

            except websockets.exceptions.ConnectionClosed:
                Logger.print_error("Connection closed during audio send")
                self.connected = False
                break
            except Exception as e:
                Logger.print_error(f"Error sending audio: {e}")
                break

    async def handle_responses(self):
        """Handle API responses with proper audio playback."""
        try:
            async for message in self.websocket:
                if not self.running:
                    break

                try:
                    event = json.loads(message)
                    event_type = event.get("type")

                    if event_type == "session.created":
                        Logger.print_info("🎃 GANGLIA awakened!")

                    elif event_type == "session.updated":
                        Logger.print_info("⚙️ GANGLIA configured!")

                    elif event_type == "input_audio_buffer.speech_started":
                        Logger.print_info("👂 GANGLIA hears you...")

                    elif event_type == "input_audio_buffer.speech_stopped":
                        Logger.print_info("🤔 GANGLIA is thinking...")

                    elif event_type == "response.created":
                        Logger.print_info("💭 GANGLIA is responding...")
                        # Start real-time streaming playback
                        self.current_response_audio = b""
                        self.current_response_text = ""

                        with self.audio_feedback_lock:
                            self.is_streaming_audio = True
                            Logger.print_info("🎵 Started real-time audio streaming")

                    elif event_type == "response.audio.delta":
                        # CRITICAL: Stream audio in real-time as it arrives
                        audio_data = base64.b64decode(event["delta"])
                        self.current_response_audio += audio_data  # For debugging

                        # Stream audio immediately for real-time playback
                        Logger.print_debug(f"🎵 Streaming audio chunk: {len(audio_data)} bytes")

                        # Queue audio data for immediate streaming playback
                        try:
                            self.streaming_audio_queue.put_nowait(audio_data)
                        except queue.Full:
                            Logger.print_warning("⚠️ Streaming audio queue full, dropping chunk")

                    elif event_type == "response.audio.done":
                        Logger.print_info("🔊 Audio streaming complete")

                        # Stop streaming and set cooldown
                        with self.audio_feedback_lock:
                            self.is_streaming_audio = False
                            self.playback_end_time = time.time() * 1000
                            Logger.print_info(f"🎤 Audio input cooldown: {self.vad_cooldown_ms}ms")

                        # Save audio file for debugging
                        if self.current_response_audio:
                            self.response_counter += 1
                            filename = f"ganglia_response_{self.response_counter}.wav"
                            self.save_audio_response(self.current_response_audio, filename)
                            Logger.print_info(f"💾 Audio saved to: {filename}")

                    elif event_type == "response.text.delta":
                        # Show text transcript and accumulate
                        text = event.get("delta", "")
                        self.current_response_text += text
                        print(f"\033[36m{text}\033[0m", end="", flush=True)  # Cyan text

                    elif event_type == "response.done":
                        Logger.print_info("✅ GANGLIA has spoken")
                        # Print full response for debugging
                        if self.current_response_text:
                            Logger.print_info(f"📝 Full response: '{self.current_response_text.strip()}'")
                        else:
                            Logger.print_warning("⚠️ No text response received!")
                        print()  # New line

                    elif event_type == "error":
                        Logger.print_error(f"API Error: {event}")

                except json.JSONDecodeError as e:
                    Logger.print_error(f"JSON decode error: {e}")

        except websockets.exceptions.ConnectionClosed:
            Logger.print_info("Connection closed")
            self.connected = False
        except Exception as e:
            Logger.print_error(f"Error handling responses: {e}")
            self.connected = False

    async def run(self):
        """Main run loop."""
        try:
            # Connect and configure
            await self.connect_and_configure()

            # Setup audio
            self.setup_audio()

            # Set running flag BEFORE starting threads
            self.running = True

            # NOTE: No longer using separate playback thread
            # Real-time streaming happens via audio_output_callback
            Logger.print_info("🎵 Real-time streaming audio enabled")

            # Start audio input
            self.input_stream.start_stream()
            Logger.print_debug("🎤 Input stream started")

            Logger.print_info("🎃 GANGLIA is ALIVE!")
            Logger.print_info("👻 Speak to the Fallen King of Halloween...")
            Logger.print_info("🎭 Listen for his ghastly response!")
            Logger.print_info("💀 Press Ctrl+C to return him to the grave")

            # Run main loops
            await asyncio.gather(
                self.send_audio_loop(),
                self.handle_responses(),
                return_exceptions=True
            )

        except KeyboardInterrupt:
            Logger.print_info("Returning GANGLIA to his coffin...")
        except Exception as e:
            Logger.print_error(f"Runtime error: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up all resources properly."""
        Logger.print_info("Cleaning up...")
        self.running = False
        self.connected = False

        # Aggressively stop audio streams
        if self.input_stream:
            try:
                Logger.print_debug("🎤 Force stopping input stream...")
                self.input_stream.stop_stream()
                self.input_stream.close()
                Logger.print_debug("🎤 Input stream closed")
            except Exception as e:
                Logger.print_warning(f"Force closing input stream: {e}")

        if self.audio_output_stream:
            try:
                Logger.print_debug("🔊 Force stopping output stream...")
                self.audio_output_stream.stop_stream()
                self.audio_output_stream.close()
                Logger.print_debug("🔊 Output stream closed")
            except Exception as e:
                Logger.print_warning(f"Force closing output stream: {e}")

        # Terminate PyAudio completely
        if self.audio:
            try:
                Logger.print_debug("🎵 Terminating PyAudio...")
                self.audio.terminate()
                Logger.print_debug("🎵 PyAudio terminated")
            except Exception as e:
                Logger.print_warning(f"Error terminating PyAudio: {e}")

        # Note: No output_stream to close since we're using ffplay

        # Kill any active ffplay processes
        if self.active_processes:
            Logger.print_debug(f"🔫 Killing {len(self.active_processes)} active ffplay processes...")
            for process in self.active_processes[:]:  # Copy list to avoid modification during iteration
                try:
                    import signal
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    Logger.print_debug(f"🔫 Killed process {process.pid}")
                except Exception as e:
                    Logger.print_error(f"Error killing process: {e}")
            self.active_processes.clear()

        # Wait for playback thread to finish
        if self.playback_thread and self.playback_thread.is_alive():
            Logger.print_debug("🎵 Waiting for playback thread to finish...")
            self.playback_thread.join(timeout=2.0)
            if self.playback_thread.is_alive():
                Logger.print_warning("⚠️ Playback thread did not finish cleanly")
            else:
                Logger.print_debug("🎵 Playback thread finished")

        # Terminate audio
        if self.audio:
            try:
                Logger.print_debug("🎵 Terminating PyAudio...")
                self.audio.terminate()
                Logger.print_debug("🎵 PyAudio terminated")
            except Exception as e:
                Logger.print_error(f"Error terminating PyAudio: {e}")

        # Close WebSocket
        if self.websocket and not self.websocket.closed:
            try:
                Logger.print_debug("🌐 Closing WebSocket...")
                await self.websocket.close()
                Logger.print_debug("🌐 WebSocket closed")
            except Exception as e:
                Logger.print_error(f"Error closing WebSocket: {e}")

        # Wait for playback thread
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1)

        Logger.print_info("💀 GANGLIA has returned to the underworld")

async def main():
    """Main entry point."""
    Logger.print_info("🎃 GANGLIA Realtime API - Working Version")
    Logger.print_info("The Fallen King of Halloween awaits...")

    # NUCLEAR STARTUP: Kill any existing instances BEFORE we start
    try:
        import subprocess
        import os
        our_pid = os.getpid()
        Logger.print_info(f"🎯 Our PID: {our_pid}")

        # Kill ALL other instances of this script
        Logger.print_info("💀 Killing any existing GANGLIA processes...")
        result = subprocess.run(['pkill', '-f', 'realtime_api_working.py'], capture_output=True, text=True)
        if result.returncode == 0:
            Logger.print_info("🔪 Existing processes terminated")
        else:
            Logger.print_info("ℹ️ No existing processes found")

        # Wait a moment for cleanup
        import time
        time.sleep(0.5)

    except Exception as e:
        Logger.print_warning(f"⚠️ Startup cleanup failed: {e}")

    test = None

    def emergency_exit():
        """NUCLEAR EXIT - Kill everything including ourselves."""
        Logger.print_info("💀 NUCLEAR EXIT - Killing all audio streams and processes")

        # Get our own PID first
        import os
        our_pid = os.getpid()
        Logger.print_info(f"🎯 Our PID: {our_pid}")

        if test:
            # Stop everything immediately
            test.running = False
            test.connected = False

            # AGGRESSIVE: Kill PyAudio streams with extreme prejudice
            try:
                if hasattr(test, 'input_stream') and test.input_stream:
                    test.input_stream.stop_stream()
                    test.input_stream.close()
                    Logger.print_info("🔪 Input stream terminated")
            except Exception as e:
                Logger.print_info(f"⚠️ Input stream kill failed: {e}")

            try:
                if hasattr(test, 'audio_output_stream') and test.audio_output_stream:
                    test.audio_output_stream.stop_stream()
                    test.audio_output_stream.close()
                    Logger.print_info("🔪 Output stream terminated")
            except Exception as e:
                Logger.print_info(f"⚠️ Output stream kill failed: {e}")

            try:
                if hasattr(test, 'audio') and test.audio:
                    test.audio.terminate()
                    Logger.print_info("🔪 PyAudio terminated")
            except Exception as e:
                Logger.print_info(f"⚠️ PyAudio termination failed: {e}")

            # Kill any subprocess we spawned
            for process in test.active_processes:
                try:
                    process.kill()
                    Logger.print_info(f"🔪 Subprocess {process.pid} killed")
                except: pass

        # NUCLEAR OPTION 1: Kill all Python processes with our script name
        try:
            import subprocess
            Logger.print_info("💣 Killing all realtime_api_working.py processes...")
            subprocess.run(['pkill', '-f', 'realtime_api_working.py'], check=False)
        except Exception as e:
            Logger.print_info(f"⚠️ pkill failed: {e}")

        # NUCLEAR OPTION 2: Kill ourselves specifically
        try:
            Logger.print_info(f"💣 Self-terminating PID {our_pid}...")
            subprocess.run(['kill', '-9', str(our_pid)], check=False)
        except Exception as e:
            Logger.print_info(f"⚠️ Self-kill failed: {e}")

        # NUCLEAR OPTION 3: Force exit if we're still alive somehow
        Logger.print_info("💀 FINAL EXIT ATTEMPT")
        os._exit(1)

    def signal_handler(signum, frame):
        """Handle Ctrl+C with IMMEDIATE exit."""
        Logger.print_info(f"\n💀 Received signal {signum}, IMMEDIATE EXIT")
        emergency_exit()

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Set up exit handler for ANY exit scenario
    import atexit
    atexit.register(emergency_exit)

    try:
        test = WorkingRealtimeTest()
        await test.run()
    except KeyboardInterrupt:
        Logger.print_info("💀 GANGLIA banished by user")
        if test:
            await test.cleanup()
        return 0
    except Exception as e:
        Logger.print_error(f"Failed to summon GANGLIA: {e}")
        return 1
    finally:
        if test:
            await test.cleanup()

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
