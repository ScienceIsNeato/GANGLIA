import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import os
import sys

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hotwords import HotwordManager


class TestHotwordManager(unittest.TestCase):
    """Test cases for the HotwordManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_config = {
            "conversation": {
                "hotwords": {
                    "video": "If you tell me an interesting story, I can try to make a video.",
                    "weather": "I don't have access to real-time weather information.",
                    "joke": "Why don't scientists trust atoms? Because they make up everything!"
                }
            }
        }

        # Create a mock file with our sample config
        self.mock_file = mock_open(read_data=json.dumps(self.sample_config))

        # Patch the open function to return our mock file
        self.patcher = patch('builtins.open', self.mock_file)
        self.patcher.start()

        # Create a HotwordManager instance with our mock config
        self.hotword_manager = HotwordManager("fake_path.json")

    def tearDown(self):
        """Tear down test fixtures."""
        self.patcher.stop()

    def test_load_config(self):
        """Test loading configuration from a file."""
        # Verify the hotwords were loaded correctly
        self.assertEqual(len(self.hotword_manager.hotwords_config), 3)

        # Get the callback function and metadata for the "video" hotword
        video_callback, video_metadata = self.hotword_manager.hotwords_config["video"]

        # Verify the callback returns the expected string
        self.assertEqual(video_callback(), "If you tell me an interesting story, I can try to make a video.")

        # Verify the metadata is None
        self.assertIsNone(video_metadata)

        # Test the other hotwords
        weather_callback, weather_metadata = self.hotword_manager.hotwords_config["weather"]
        self.assertEqual(weather_callback(), "I don't have access to real-time weather information.")
        self.assertIsNone(weather_metadata)

        joke_callback, joke_metadata = self.hotword_manager.hotwords_config["joke"]
        self.assertEqual(joke_callback(), "Why don't scientists trust atoms? Because they make up everything!")
        self.assertIsNone(joke_metadata)

    def test_detect_hotwords_match(self):
        """Test detecting hotwords in user input with a match."""
        # Test with a matching hotword
        detected, response = self.hotword_manager.detect_hotwords("Can you make a video for me?")
        self.assertTrue(detected)
        self.assertEqual(response, "If you tell me an interesting story, I can try to make a video.")

    def test_detect_hotwords_no_match(self):
        """Test detecting hotwords in user input with no match."""
        # Test with no matching hotword
        detected, response = self.hotword_manager.detect_hotwords("Hello, how are you?")
        self.assertFalse(detected)
        self.assertEqual(response, "")

    def test_detect_hotwords_case_insensitive(self):
        """Test that hotword detection is case-insensitive."""
        # Test with different case
        detected, response = self.hotword_manager.detect_hotwords("Tell me a JOKE please")
        self.assertTrue(detected)
        self.assertEqual(response, "Why don't scientists trust atoms? Because they make up everything!")

    def test_callback_initialization(self):
        """Test initializing with callback functions."""
        # Create a sample config with callbacks
        def weather_callback():
            return "It's sunny today!"
        # Create a mock file with our callback config
        mock_file = mock_open(read_data=json.dumps({
            "conversation": {
                "hotwords": {
                    "video": "If you tell me an interesting story, I can try to make a video.",
                    "weather": "I don't have access to real-time weather information.",
                    "joke": "Why don't scientists trust atoms? Because they make up everything!"
                }
            }
        }))

        # Patch the open function to return our mock file
        with patch('builtins.open', mock_file):
            # Create a new HotwordManager instance
            manager = HotwordManager("fake_path.json")

            # Override the hotwords_config with our callback config
            manager.hotwords_config = {
                "video": (lambda context=None: "If you tell me an interesting story, I can try to make a video.", None),
                "weather": (weather_callback, None),
                "joke": (lambda context=None: "Why don't scientists trust atoms? Because they make up everything!", None)
            }

            # Test string response (should be converted to a callback)
            detected, response = manager.detect_hotwords("Can you make a video for me?")
            self.assertTrue(detected)
            self.assertEqual(response, "If you tell me an interesting story, I can try to make a video.")

            # Test function callback
            detected, response = manager.detect_hotwords("What's the weather like?")
            self.assertTrue(detected)
            self.assertEqual(response, "It's sunny today!")

    def test_callback_with_context(self):
        """Test callbacks that receive context."""
        # Create a mock callback that uses context
        def context_callback(context):
            return f"Hello, {context['user_name']}!"

        # Create a sample config with context callback
        callback_config = {
            "conversation": {
                "hotwords": {
                    "hello": (context_callback, None)
                }
            }
        }

        # Mock the load_config method to return our callback config
        with patch.object(HotwordManager, 'load_config', return_value=callback_config["conversation"]["hotwords"]):
            manager = HotwordManager("fake_path.json")

            # Test callback with context
            context = {"user_name": "Alice"}
            detected, response = manager.detect_hotwords("Hello there", context=context)
            self.assertTrue(detected)
            self.assertEqual(response, "Hello, Alice!")

    def test_callback_with_side_effects(self):
        """Test callbacks that have side effects."""
        # Create a class to track state
        class StateTracker:
            def __init__(self):
                self.count = 0

            def increment(self, context=None):
                self.count += 1
                return f"Count incremented to {self.count}"

        # Create a tracker instance
        tracker = StateTracker()

        # Create a sample config with the tracker callback
        callback_config = {
            "counter": (tracker.increment, None)
        }

        # Create a HotwordManager with our callback
        manager = HotwordManager("fake_path.json")
        manager.hotwords_config = callback_config

        # Test the callback multiple times
        detected, response = manager.detect_hotwords("counter")
        self.assertTrue(detected)
        self.assertEqual(response, "Count incremented to 1")
        self.assertEqual(tracker.count, 1)

        detected, response = manager.detect_hotwords("counter")
        self.assertTrue(detected)
        self.assertEqual(response, "Count incremented to 2")
        self.assertEqual(tracker.count, 2)

        # Test with context
        context = {"user": "Alice"}
        detected, response = manager.detect_hotwords("counter", context=context)
        self.assertTrue(detected)
        self.assertEqual(response, "Count incremented to 3")
        self.assertEqual(tracker.count, 3)

    def test_callback_with_metadata(self):
        """Test callbacks that use metadata."""
        # Create a callback that uses metadata
        def metadata_callback(context=None, metadata=None):
            if metadata:
                return f"Using metadata: {metadata}"
            return "No metadata provided"

        # Create a sample config with metadata
        callback_config = {
            "info": (metadata_callback, "This is important information"),
            "help": (metadata_callback, "Help documentation")
        }

        # Create a HotwordManager with our callback
        manager = HotwordManager("fake_path.json")

        # Override the hotwords_config with our callback config
        manager.hotwords_config = callback_config

        # Update the detect_hotwords method to pass metadata to the callback
        original_detect_hotwords = manager.detect_hotwords

        def detect_hotwords_with_metadata(prompt, context=None):
            prompt = prompt.lower()
            hotword_detected = False
            response = ""

            for hotword, value in manager.hotwords_config.items():
                if hotword in prompt:
                    hotword_detected = True
                    callback, metadata = value

                    # Call the callback function with context and metadata
                    try:
                        if context is not None:
                            response = callback(context, metadata)
                        else:
                            response = callback(metadata=metadata)
                    except TypeError:
                        # If the callback doesn't accept metadata, call it without
                        response = callback()
                    break

            return hotword_detected, response

        # Replace the method temporarily
        manager.detect_hotwords = detect_hotwords_with_metadata

        try:
            # Test the callback with metadata
            detected, response = manager.detect_hotwords("info")
            self.assertTrue(detected)
            self.assertEqual(response, "Using metadata: This is important information")

            detected, response = manager.detect_hotwords("help")
            self.assertTrue(detected)
            self.assertEqual(response, "Using metadata: Help documentation")
        finally:
            # Restore the original method
            manager.detect_hotwords = original_detect_hotwords
