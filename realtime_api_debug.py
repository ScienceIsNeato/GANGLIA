#!/usr/bin/env python3
"""
Debug version of OpenAI Realtime API test with better error handling.
"""

import asyncio
import json
import os
import sys
import websockets
import base64
import pyaudio
import queue
import time
from typing import Optional

# Import GANGLIA libraries
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from logger import Logger

class DebugRealtimeTest:
    """Debug version with detailed logging."""

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
        self.audio_queue = queue.Queue(maxsize=100)  # Limit queue size
        self.output_queue = queue.Queue(maxsize=100)

        # PyAudio setup
        self.audio = pyaudio.PyAudio()
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None

        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.running = False
        self.connected = False

        # Debug counters
        self.audio_chunks_sent = 0
        self.responses_received = 0

        Logger.print_info("DebugRealtimeTest initialized")

    def list_audio_devices(self):
        """List available audio devices for debugging."""
        Logger.print_info("Available audio devices:")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            Logger.print_info(f"  {i}: {info['name']} (inputs: {info['maxInputChannels']})")

    def audio_input_callback(self, in_data, frame_count, time_info, status):
        """Audio input callback with debug info."""
        if self.running and self.connected:
            try:
                self.audio_queue.put_nowait(in_data)
                self.audio_chunks_sent += 1
                if self.audio_chunks_sent % 100 == 0:  # Log every 100 chunks
                    Logger.print_debug(f"Audio chunks sent: {self.audio_chunks_sent}")
            except queue.Full:
                Logger.print_warning("Audio queue full, dropping audio data")

        return (in_data, pyaudio.paContinue)

    async def connect_and_configure(self):
        """Connect with better error handling."""
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
                ping_interval=20,  # Send ping every 20 seconds
                ping_timeout=10,   # Wait 10 seconds for pong
                close_timeout=10   # Wait 10 seconds for close
            )
            self.connected = True
            Logger.print_info("✅ Connected!")

            # Wait a moment before configuring
            await asyncio.sleep(0.5)

            # Configure session with simpler settings
            config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": "You are GANGLIA. Keep responses very short - 1 sentence max.",
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 1000  # Longer silence before processing
                    }
                }
            }

            Logger.print_info("Sending session configuration...")
            await self.websocket.send(json.dumps(config))
            Logger.print_info("🎃 Configuration sent")

        except Exception as e:
            Logger.print_error(f"Connection failed: {e}")
            self.connected = False
            raise

    def setup_audio(self):
        """Set up audio with device selection."""
        Logger.print_info("Setting up audio...")
        self.list_audio_devices()

        try:
            # Input stream (microphone) - use default device
            self.input_stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=None,  # Use default
                frames_per_buffer=self.chunk_size,
                stream_callback=self.audio_input_callback
            )

            Logger.print_info("🎧 Audio input ready")

        except Exception as e:
            Logger.print_error(f"Audio setup failed: {e}")
            raise

    async def send_audio_loop(self):
        """Send audio with rate limiting and error handling."""
        last_send_time = 0
        send_interval = 0.02  # 50ms between sends (20 FPS)

        while self.running and self.connected:
            try:
                current_time = time.time()

                # Rate limiting
                if current_time - last_send_time < send_interval:
                    await asyncio.sleep(0.01)
                    continue

                # Get audio data from queue
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
                last_send_time = current_time

            except websockets.exceptions.ConnectionClosed:
                Logger.print_error("WebSocket connection closed during audio send")
                self.connected = False
                break
            except Exception as e:
                Logger.print_error(f"Error sending audio: {e}")
                await asyncio.sleep(1)  # Wait before retrying

    async def handle_responses(self):
        """Handle responses with detailed logging."""
        try:
            async for message in self.websocket:
                if not self.running:
                    break

                try:
                    event = json.loads(message)
                    event_type = event.get("type")
                    self.responses_received += 1

                    Logger.print_debug(f"Received: {event_type} (#{self.responses_received})")

                    if event_type == "session.created":
                        Logger.print_info("🎃 Session created!")

                    elif event_type == "session.updated":
                        Logger.print_info("⚙️ Session configured!")

                    elif event_type == "input_audio_buffer.speech_started":
                        Logger.print_info("👂 Speech detected!")

                    elif event_type == "input_audio_buffer.speech_stopped":
                        Logger.print_info("🤔 Processing speech...")

                    elif event_type == "response.created":
                        Logger.print_info("💭 Response started")

                    elif event_type == "response.audio.delta":
                        # Audio response received
                        audio_data = base64.b64decode(event["delta"])
                        Logger.print_debug(f"Audio delta: {len(audio_data)} bytes")

                    elif event_type == "response.text.delta":
                        # Text response
                        text = event.get("delta", "")
                        print(text, end="", flush=True)

                    elif event_type == "response.done":
                        Logger.print_info("✅ Response complete")
                        print()

                    elif event_type == "error":
                        Logger.print_error(f"API Error: {event}")

                    else:
                        Logger.print_debug(f"Unknown event: {event_type}")

                except json.JSONDecodeError as e:
                    Logger.print_error(f"JSON decode error: {e}")

        except websockets.exceptions.ConnectionClosed:
            Logger.print_info("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            Logger.print_error(f"Error handling responses: {e}")
            self.connected = False

    async def run(self):
        """Main run loop with better error handling."""
        try:
            # Connect and configure
            await self.connect_and_configure()

            # Setup audio
            self.setup_audio()

            # Start audio stream
            self.input_stream.start_stream()
            self.running = True

            Logger.print_info("🎃 GANGLIA Debug Test Active!")
            Logger.print_info("Speak clearly into your microphone...")
            Logger.print_info("Press Ctrl+C to exit")

            # Run loops concurrently
            await asyncio.gather(
                self.send_audio_loop(),
                self.handle_responses(),
                return_exceptions=True
            )

        except KeyboardInterrupt:
            Logger.print_info("Shutting down...")
        except Exception as e:
            Logger.print_error(f"Runtime error: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources."""
        Logger.print_info("Cleaning up...")
        self.running = False
        self.connected = False

        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
            except:
                pass

        if self.audio:
            try:
                self.audio.terminate()
            except:
                pass

        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.close()
            except:
                pass

        Logger.print_info(f"📊 Stats: {self.audio_chunks_sent} audio chunks sent, {self.responses_received} responses received")
        Logger.print_info("💀 GANGLIA debug session ended")

async def main():
    """Main entry point."""
    Logger.print_info("🎃 GANGLIA Realtime API Debug Test")

    try:
        test = DebugRealtimeTest()
        await test.run()
    except Exception as e:
        Logger.print_error(f"Failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
