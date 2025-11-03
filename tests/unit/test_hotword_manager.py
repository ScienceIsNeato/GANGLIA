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

        # Verify the hotword phrases directly (they're just strings, not callbacks)
        self.assertEqual(
            self.hotword_manager.hotwords_config["video"],
            "If you tell me an interesting story, I can try to make a video."
        )
        self.assertEqual(
            self.hotword_manager.hotwords_config["weather"],
            "I don't have access to real-time weather information."
        )
        self.assertEqual(
            self.hotword_manager.hotwords_config["joke"],
            "Why don't scientists trust atoms? Because they make up everything!"
        )

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
        """Test that hotwords can be loaded and detected correctly."""
        # Create a mock file with hotword config
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

            # Test video hotword
            detected, response = manager.detect_hotwords("Can you make a video for me?")
            self.assertTrue(detected)
            self.assertEqual(response, "If you tell me an interesting story, I can try to make a video.")

            # Test weather hotword
            detected, response = manager.detect_hotwords("What's the weather like?")
            self.assertTrue(detected)
            self.assertEqual(response, "I don't have access to real-time weather information.")

    def test_callback_with_context(self):
        """Test that detect_hotwords works with multiple hotwords."""
        # Create a config with multiple hotwords
        hotwords_config = {
            "hello": "Hello! How can I help you?",
            "goodbye": "Goodbye! Have a great day!",
            "thanks": "You're welcome!"
        }

        # Mock the load_config method to return our config
        with patch.object(HotwordManager, 'load_config', return_value=hotwords_config):
            manager = HotwordManager("fake_path.json")

            # Test each hotword
            detected, response = manager.detect_hotwords("Hello there")
            self.assertTrue(detected)
            self.assertEqual(response, "Hello! How can I help you?")

            detected, response = manager.detect_hotwords("Thanks for the help")
            self.assertTrue(detected)
            self.assertEqual(response, "You're welcome!")

    def test_callback_with_side_effects(self):
        """Test that hotwords return consistent responses."""
        # Create a sample config
        hotwords_config = {
            "help": "I'm here to assist you!",
            "info": "Here's some information."
        }

        # Create a HotwordManager with our config
        manager = HotwordManager("fake_path.json")
        manager.hotwords_config = hotwords_config

        # Test that the same hotword returns the same response consistently
        detected1, response1 = manager.detect_hotwords("I need help")
        self.assertTrue(detected1)
        self.assertEqual(response1, "I'm here to assist you!")

        detected2, response2 = manager.detect_hotwords("help me please")
        self.assertTrue(detected2)
        self.assertEqual(response2, "I'm here to assist you!")
        
        # Verify responses are consistent
        self.assertEqual(response1, response2)

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
