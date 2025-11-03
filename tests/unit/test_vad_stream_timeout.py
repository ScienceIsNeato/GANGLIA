"""
Test that VAD properly closes Google Speech streams before the 305-second limit.

Bug: Stream stays open for 305 seconds (Google's limit) instead of closing
after conversation_timeout (5 seconds of silence).

Cost impact: Wastes ~$0.006/minute = ~$1.80 for 305 seconds per idle stream.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from dictation.vad_dictation import VoiceActivityDictation
import time


class TestVADStreamTimeout(unittest.TestCase):
    """Test that streams close promptly after conversation timeout."""

    @patch('dictation.stt_provider.speech')
    @patch('dictation.vad_dictation.pyaudio.PyAudio')
    def test_stream_closes_after_conversation_timeout(self, mock_pyaudio, mock_speech):
        """
        CRITICAL: Stream must close after conversation_timeout seconds of silence.

        This test verifies that:
        1. When no speech is detected for conversation_timeout seconds
        2. The Google Speech streaming connection is properly closed
        3. We don't hit the 305-second limit
        """
        # Setup
        vad = VoiceActivityDictation()
        vad.CONVERSATION_TIMEOUT = 5  # 5 seconds

        # Mock PyAudio stream
        mock_stream = Mock()
        mock_stream.read = Mock(return_value=b'\x00' * 2048)  # Silent audio
        mock_stream.close = Mock()

        # Set the vad_stream (normally created in listen_for_speech)
        vad.vad_stream = mock_stream

        mock_audio_instance = Mock()
        mock_audio_instance.open = Mock(return_value=mock_stream)
        mock_pyaudio.return_value = mock_audio_instance

        # Mock Google Speech client
        mock_client = Mock()

        # Simulate streaming responses that should stop after timeout
        start_time = [time.time()]
        request_count = [0]

        def mock_streaming_recognize(config, requests):
            """Simulate Google STT responses, should stop when generator stops."""
            start_time[0] = time.time()

            for _ in requests:  # Process requests from generator
                request_count[0] += 1
                elapsed = time.time() - start_time[0]

                # Safety check: If test runs too long, fail it
                if elapsed > 15:
                    raise Exception(f"Stream stayed open for {elapsed}s, should close after conversation_timeout!")

                # Simulate a response with no speech
                mock_response = Mock()
                mock_response.results = []
                yield mock_response

                # Small delay to simulate network/processing
                time.sleep(0.05)

        mock_client.streaming_recognize = mock_streaming_recognize
        vad.client = mock_client

        # Set VAD to ACTIVE mode (skip the initial speech detection)
        vad.mode = 'ACTIVE'

        # Execute: Try to transcribe with no speech
        start_time = time.time()
        result = vad.transcribe_stream_active_mode(device_index=0)
        elapsed = time.time() - start_time

        # Verify: Stream should close within conversation_timeout + buffer for timer/processing
        # Should NOT take 305 seconds!
        max_expected_time = vad.CONVERSATION_TIMEOUT + 2  # +2s buffer for timer delays
        self.assertLess(elapsed, max_expected_time,
                       f"Stream took {elapsed:.2f}s to close, should be <{max_expected_time}s "
                       f"(conversation_timeout={vad.CONVERSATION_TIMEOUT}s + 2s buffer)")

        # Verify stream was properly closed
        mock_stream.close.assert_called_once()

        # Verify generator stopped sending requests after timeout
        # At 50ms per chunk, 5s timeout = ~100 requests, add buffer
        self.assertLess(request_count[0], 200,
                       f"Processed {request_count[0]} requests, generator should stop after timeout")


    @patch('dictation.stt_provider.speech')
    @patch('dictation.vad_dictation.pyaudio.PyAudio')
    def test_stream_closes_after_final_transcript(self, mock_pyaudio, mock_speech):
        """
        Test that stream closes promptly after final transcript + silence_threshold.

        Scenario:
        1. User speaks: "Hello GANGLIA"
        2. Google returns final transcript
        3. After silence_threshold, stream should close and return transcript
        """
        # Setup
        vad = VoiceActivityDictation()
        vad.SILENCE_THRESHOLD = 0.75

        # Mock PyAudio stream
        mock_stream = Mock()
        mock_stream.read = Mock(return_value=b'\x00' * 2048)
        mock_stream.close = Mock()

        # Set the vad_stream (normally created in listen_for_speech)
        vad.vad_stream = mock_stream

        mock_audio_instance = Mock()
        mock_audio_instance.open = Mock(return_value=mock_stream)
        mock_pyaudio.return_value = mock_audio_instance

        # Mock Google Speech client
        mock_client = Mock()

        # Simulate: One final transcript, then generator stops (simulating silence timeout)
        def mock_streaming_recognize(config, requests):
            # Send one final transcript
            mock_result = Mock()
            mock_result.alternatives = [Mock(transcript="Hello GANGLIA")]
            mock_result.is_final = True

            mock_response = Mock()
            mock_response.results = [mock_result]
            yield mock_response

            # Then a few empty responses to simulate the silence period
            for _ in range(20):  # About 1 second of audio chunks
                # Check if done_speaking timer has fired
                if not vad.listening:
                    break

                mock_response = Mock()
                mock_response.results = []
                yield mock_response
                time.sleep(0.05)

        mock_client.streaming_recognize = mock_streaming_recognize
        vad.client = mock_client

        vad.mode = 'ACTIVE'

        # Execute
        start_time = time.time()
        result = vad.transcribe_stream_active_mode(device_index=0)
        elapsed = time.time() - start_time

        # Verify transcript was captured
        self.assertEqual(result.strip(), "Hello GANGLIA",
                        "Should return the finalized transcript")

        # Verify stream closed within reasonable time
        # silence_threshold (0.75s) + small buffer for processing
        max_time = vad.SILENCE_THRESHOLD + 1.5
        self.assertLess(elapsed, max_time,
                       f"Stream took {elapsed:.2f}s, should close within ~{max_time}s")

        # Verify stream was properly closed
        mock_stream.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
