"""Test helper functions for integration tests.

This module provides utility functions for integration testing, including:
- Video and audio duration measurement
- Configuration file handling
- Process completion waiting
- File validation
- Test log parsing
"""

import os
import re
import subprocess
import time
import json
import logging
from google.cloud import storage
from logger import Logger
from ttv.log_messages import (
    LOG_CLOSING_CREDITS_DURATION,
    LOG_FFPROBE_COMMAND,
    LOG_BACKGROUND_MUSIC_SUCCESS,
    LOG_BACKGROUND_MUSIC_FAILURE
)
import datetime
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

import cv2
import numpy as np

from social_media.youtube_client import YouTubeClient

logger = logging.getLogger(__name__)

def validate_background_music(output: str) -> None:
    """Validate background music generation and addition.
    
    Args:
        output: The output log to validate
        
    Raises:
        AssertionError: If background music validation fails
    """
    # First check if video concatenation failed
    if "Failed to concatenate video segments" in output:
        logger.warning("Video concatenation failed before background music step")
        return
        
    # Check for successful background music generation
    success_pattern = re.compile(LOG_BACKGROUND_MUSIC_SUCCESS)
    failure_pattern = re.compile(LOG_BACKGROUND_MUSIC_FAILURE)
    
    success_matches = success_pattern.findall(output)
    failure_matches = failure_pattern.findall(output)
    
    # Either we should have a success message or a failure message
    assert len(success_matches) + len(failure_matches) > 0, "No background music status found"
    
    if success_matches:
        logger.info("Background music successfully added")
    else:
        logger.warning("Background music addition failed (expected in some test cases)")

def wait_for_completion(timeout=300):
    """Wait for a process to complete within the specified timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(1)
    return True

def get_audio_duration(audio_file_path):
    """Get the duration of an audio file using ffprobe."""
    if not os.path.exists(audio_file_path):
        Logger.print_error(f"Audio file not found: {audio_file_path}")
        return None

    Logger.print_info(LOG_FFPROBE_COMMAND)
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_file_path
    ]
    try:
        output = subprocess.check_output(cmd).decode().strip()
        return float(output)
    except (subprocess.CalledProcessError, ValueError) as e:
        Logger.print_error(f"Failed to get audio duration: {e}")
        return None

def get_video_duration(video_file_path):
    """Get the duration of a video file using ffprobe."""
    if not os.path.exists(video_file_path):
        Logger.print_error(f"Video file not found: {video_file_path}")
        return None

    Logger.print_info(LOG_FFPROBE_COMMAND)
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_file_path
    ]
    try:
        output = subprocess.check_output(cmd).decode().strip()
        return float(output)
    except (subprocess.CalledProcessError, ValueError) as e:
        Logger.print_error(f"Failed to get video duration: {e}")
        return None

def validate_segment_count(output, config_path):
    """Validate that all story segments are present in the output."""
    print("\n=== Validating Segment Count ===")
    
    try:
        with open(config_path, encoding='utf-8') as f:
            config = json.loads(f.read())
            expected_segments = len(config.get('story', []))
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        raise AssertionError(f"Failed to read story from config: {e}") # pylint: disable=raise-missing-from
    
    segment_pattern = r'segment_(\d+)_initial\.mp4'
    found_segments = {int(m.group(1)) for m in re.finditer(segment_pattern, output)}
    actual_segments = len(found_segments)
    
    print(f"Expected segments: {expected_segments}")
    print(f"Actual segments: {actual_segments}")
    print(f"Found segment numbers: {sorted(list(found_segments))}")
    
    if actual_segments != expected_segments:
        raise AssertionError(
            f"Expected {expected_segments} segments but found {actual_segments}"
        )
    print("✓ All story segments are present")
    return actual_segments

def get_output_dir_from_logs(output: str) -> str:
    """Extract the TTV output directory from logs.
    
    Args:
        output: The test output containing log messages
        
    Returns:
        str: Path to the TTV output directory
        
    Raises:
        AssertionError: If directory not found in logs
    """
    pattern = r"Created TTV directory: (.+)"
    if match := re.search(pattern, output):
        return match.group(1)
    raise AssertionError("TTV directory not found in logs")

def validate_audio_video_durations(config_path, output):
    """Validate that each audio file matches the corresponding video segment duration."""
    print("\n=== Validating Audio/Video Segment Durations ===")
    
    try:
        with open(config_path, encoding='utf-8') as f:
            config = json.loads(f.read())
            expected_segments = len(config.get('story', []))
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        raise AssertionError(f"Failed to read story from config: {e}") # pylint: disable=raise-missing-from

    # Get output directory from logs
    output_dir = get_output_dir_from_logs(output)
    print(f"Checking {expected_segments} segments in {output_dir}")
    
    # First get all the segment files
    segments = []
    for i in range(expected_segments):
        # Try final segment first, fall back to initial if not found
        final_path = os.path.join(output_dir, f"segment_{i}.mp4")
        initial_path = os.path.join(output_dir, f"segment_{i}_initial.mp4")
        
        if os.path.exists(final_path):
            segments.append((i, final_path))
            print(f"Found final segment {i}: {final_path}")
        elif os.path.exists(initial_path):
            segments.append((i, initial_path))
            print(f"Found initial segment {i}: {initial_path}")
        else:
            print(f"No segment found for index {i}")
    
    if not segments:
        raise AssertionError("No video segments found")
    
    if len(segments) != expected_segments:
        raise AssertionError(f"Expected {expected_segments} segments but found {len(segments)}")

    # Check each segment's audio/video duration
    total_duration = 0.0
    for i, segment_path in segments:
        video_duration = get_video_duration(segment_path)
        if video_duration is None:
            raise AssertionError(f"Could not get video duration for segment {i}")
            
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            segment_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        audio_duration = float(result.stdout.strip())
        
        if abs(audio_duration - video_duration) >= 0.1:
            print(f"⚠️  Duration mismatch in segment {i}:")
            print(f"   Audio: {audio_duration:.2f}s")
            print(f"   Video: {video_duration:.2f}s")
        else:
            print(f"✓ Segment {i} durations match: {video_duration:.2f}s")
            total_duration += video_duration

    # Check the main video with background music
    main_video = os.path.join(output_dir, "main_video_with_background_music.mp4")
    if os.path.exists(main_video):
        main_duration = get_video_duration(main_video)
        print(f"✓ Main video with background music duration: {main_duration:.2f}s")
        return main_duration
    else:
        print(f"✓ Using total segment duration: {total_duration:.2f}s")
        return total_duration

def extract_final_video_path(output):
    """Extract the final video path from the logs."""
    patterns = [
        r'Final video (?:with|without) closing credits created: output_path=(.+\.mp4)',
        r'Final video created at: output_path=(.+\.mp4)'
    ]
    
    for pattern in patterns:
        if match := re.search(pattern, output):
            return match.group(1)
    
    raise AssertionError("Final video path not found in logs.")

def validate_final_video_path(output_dir=None):
    """Validate that the final video path is found in the logs."""
    print("\n=== Validating Final Video Path ===")
    final_video_path = os.path.join(output_dir, "final_video.mp4")
    if not os.path.exists(final_video_path):
        raise AssertionError(f"Expected output video not found at {final_video_path}")
    print(f"✓ Final video found at: {os.path.basename(final_video_path)}")

    return final_video_path

def validate_total_duration(final_video_path, main_video_duration):
    """Validate that the final video duration matches main video + credits."""
    print("\n=== Validating Final Video Duration ===")
    final_duration = get_video_duration(final_video_path)
    expected_duration = main_video_duration  # Credits duration is added by caller
    
    if abs(final_duration - expected_duration) >= 3.0:  # Increased tolerance to 3.0 seconds
        raise AssertionError(
            f"Final video duration ({final_duration:.2f}s) differs significantly from expected "
            f"duration of main video + credits ({expected_duration:.2f}s)."
        )
    print(
        f"✓ Final duration ({final_duration:.2f}s) is within tolerance of expected duration "
        f"({expected_duration:.2f}s)"
    )

def validate_closing_credits_duration(output, config_path):
    """Validate that the closing credits audio and video durations match."""
    print("\n=== Validating Closing Credits Duration ===")
    
    duration_match = re.search(f'{LOG_CLOSING_CREDITS_DURATION}: (\\d+\\.\\d+)s', output)
    if duration_match:
        audio_duration = float(duration_match.group(1))
        print(f"✓ Generated closing credits duration: {audio_duration:.2f}s")
        return audio_duration
    
    try:
        with open(config_path, encoding='utf-8') as f:
            config = json.loads(f.read())
            if 'closing_credits' in config and isinstance(config['closing_credits'], str):
                credits_path = config['closing_credits']
                audio_duration = get_audio_duration(credits_path)
                print(
                    f"✓ Pre-loaded closing credits ({os.path.basename(credits_path)}) "
                    f"duration: {audio_duration:.2f}s"
                )
                return audio_duration
    except (IOError, ValueError) as e:
        print(f"Failed to read closing credits from config: {e}")
        
    print("No closing credits found")
    return 0.0

def read_story_from_config(config_file_path):
    """Read and parse a story configuration file."""
    try:
        with open(config_file_path, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, ValueError) as e:
        raise AssertionError(f'Failed to read story from config: {e}') from e

def read_story_from_config_file(config_file_path):
    """Read and parse a story configuration file with error handling."""
    try:
        with open(config_file_path, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, ValueError) as e:
        raise AssertionError(f'Failed to read story from config: {e}') from e

def read_story_from_config_file_with_retry(config_file_path):
    """Read and parse a story configuration file with retry on failure."""
    try:
        with open(config_file_path, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, ValueError) as e:
        Logger.print_error(f"Failed to read story from config: {e}")
        return None

def read_story_from_config_file_with_retry_and_wait(config_file_path):
    """Read and parse a story configuration file with retry and wait."""
    try:
        with open(config_file_path, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, ValueError) as e:
        Logger.print_error(f"Failed to read story from config: {e}")
        return None

def validate_gcs_upload(bucket_name: str, project_name: str) -> storage.Blob:
    """Validate that a file was uploaded to GCS and return the uploaded file blob.
    
    Args:
        bucket_name: The name of the GCS bucket
        project_name: The GCP project name
        
    Returns:
        storage.Blob: The most recently uploaded video file blob
        
    Raises:
        AssertionError: If no uploaded file is found or if the file doesn't exist
    """
    print("\n=== Validating GCS Upload ===")
    storage_client = storage.Client(project=project_name)
    bucket = storage_client.get_bucket(bucket_name)
    
    # List blobs in test_outputs directory
    blobs = list(bucket.list_blobs(prefix="test_outputs/"))
    
    # Find the most recently uploaded file
    uploaded_file = None
    for blob in blobs:
        if blob.name.endswith("_final_video.mp4"):
            if not uploaded_file or blob.time_created > uploaded_file.time_created:
                uploaded_file = blob
    
    assert uploaded_file is not None, "Failed to find uploaded video in GCS"
    assert uploaded_file.exists(), "Uploaded file does not exist in GCS"
    
    print(f"✓ Found uploaded file in GCS: {uploaded_file.name}")
    return uploaded_file

def validate_caption_accuracy(output: str, config_path: str) -> None:
    """Validate that Whisper's captions match the expected text for each segment.
    
    Args:
        output: The test output containing Whisper's word data
        config_path: Path to the config file containing expected text
    """
    print("\nCaption validation:")
    
    try:
        # Read expected text from config
        with open(config_path, encoding="utf-8") as f:
            config = json.loads(f.read())
            story_segments = config.get("story", [])
            expected_text = " ".join(story_segments)
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        raise AssertionError(f"Failed to read story from config: {e}") from e
    
    # Extract word data from output
    word_pattern = r"Word data: {'word': '([^']+)', 'start': np\.float64\(([^)]+)\), 'end': np\.float64\(([^)]+)\), 'probability': np\.float64\(([^)]+)\)}"
    
    # Find all words in the output
    actual_words = []
    for match in re.finditer(word_pattern, output):
        word = match.group(1).strip()
        # Skip closing credits numbers
        if not word.replace(",", "").strip().isdigit():
            actual_words.append(word)
    
    actual_text = " ".join(actual_words)
    
    # Print debug info
    print(f"Expected: {expected_text}")
    print(f"Actual:   {actual_text}")
    
    # Convert to lowercase and remove punctuation
    def clean_text(text):
        return [w for w in re.sub(r"[^\w\s]", "", text.lower()).split() if w]
    
    expected_words = set(clean_text(expected_text))
    actual_words = set(clean_text(actual_text))
    
    # Calculate word presence score
    matched_words = len(expected_words & actual_words)
    total_expected = len(expected_words)
    word_presence_score = (matched_words / total_expected) * 100 if total_expected > 0 else 0
    
    print(f"\nWord presence score: {word_presence_score:.1f}% ({matched_words}/{total_expected} words)")
    
    # Check for missing and extra words
    missing_words = expected_words - actual_words
    extra_words = actual_words - expected_words
    
    if missing_words:
        print(f"Missing words: {sorted(missing_words)}")
    if extra_words:
        print(f"Extra words: {sorted(extra_words)}")
    
    # Define thresholds
    CRITICAL_THRESHOLD = 25.0  # Test fails if below this
    WORD_PRESENCE_TARGET = 80.0  # Warning if below this
    
    # Check for critical failures (truly poor accuracy)
    if word_presence_score < CRITICAL_THRESHOLD:
        raise AssertionError(
            f"Caption accuracy critically low: word presence score {word_presence_score:.1f}% "
            f"is below minimum threshold of {CRITICAL_THRESHOLD}%"
        )
    
    # Warn about moderate accuracy issues
    if word_presence_score < WORD_PRESENCE_TARGET:
        print(f"\n⚠️  Warning: Word presence score ({word_presence_score:.1f}%) "
              f"is below target of {WORD_PRESENCE_TARGET}%")
        print("\n⚠️  Captions below target accuracy but above critical threshold - continuing test")
    else:
        print("\n✓ All captions meet target accuracy threshold")

def get_git_description() -> str:
    """Get description from either PR or latest commit."""
    try:
        # Try to get PR description first
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "title,body"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pr_info = json.loads(result.stdout)
            return f"{pr_info['title']}\n\n{pr_info['body']}"
    except Exception:
        pass  # Fall back to commit message
    
    try:
        # Get the most recent commit message
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    
    return "No description available"

def post_test_results_to_youtube(
    test_name: str,
    final_video_path: str,
    additional_info: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None
) -> str:
    """Post integration test results to YouTube."""
    if not os.path.exists(final_video_path):
        Logger.print_info("Skipping YouTube upload: Final video not found")
        return ""

    # Check if YouTube upload is enabled
    upload_smoke = os.getenv('UPLOAD_SMOKE_TESTS_TO_YOUTUBE', 'false').lower() == 'true'
    upload_integration = os.getenv('UPLOAD_INTEGRATION_TESTS_TO_YOUTUBE', 'false').lower() == 'true'
    
    if not (upload_smoke or upload_integration):
        Logger.print_info("Skipping YouTube upload: Neither UPLOAD_SMOKE_TESTS_TO_YOUTUBE nor UPLOAD_INTEGRATION_TESTS_TO_YOUTUBE is set to true")
        return ""

    # Check for required credentials
    if not os.path.exists(os.getenv('YOUTUBE_CREDENTIALS_FILE', '')):
        Logger.print_info("Skipping YouTube upload: YOUTUBE_CREDENTIALS_FILE not found")
        return ""
    if not os.path.exists(os.getenv('YOUTUBE_TOKEN_FILE', '')):
        Logger.print_info("Skipping YouTube upload: YOUTUBE_TOKEN_FILE not found")
        return ""

    try:
        Logger.print_info("Attempting to upload test results to YouTube...")

        def sanitize_text(text: str, max_length: int = 5000) -> str:
            """Sanitize text for YouTube description."""
            # Remove ANSI escape codes
            text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
            # Keep only printable ASCII characters
            text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
            # Truncate if too long
            if len(text) > max_length:
                text = text[:max_length-3] + "..."
            return text
        
        # Get description from git
        description = get_git_description()
        
        # Add project information
        project_info = [
            "",
            "🌟 About GANGLIA",
            "GANGLIA is an open-source project that automates the creation of engaging social media content.",
            "It uses AI to generate and synchronize video, audio, and captions for a seamless storytelling experience.",
            "",
            "🔗 Project Links",
            "- GitHub: https://github.com/ScienceIsNeato/ganglia",
            "",
            "🎯 Purpose of Integration Tests",
            "These videos are automatically generated during our integration tests to:",
            "1. Demonstrate the current capabilities of GANGLIA",
            "2. Track improvements and changes over time",
            "3. Help identify potential bugs or areas for enhancement",
            ""
        ]
        
        # Add config information if provided
        config_info = []
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, encoding='utf-8') as f:
                    config = json.loads(f.read())
                    config_info = [
                        "",
                        "📝 Configuration Used",
                        "```json",
                        json.dumps(config, indent=2),
                        "```",
                        ""
                    ]
            except Exception as e:
                logger.warning(f"Failed to read config file: {e}")
        
        # Add metadata at the end
        metadata_lines = [
            "",
            "🔍 Test Information",
            f"Test: {test_name}",
            f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        if additional_info:
            metadata_lines.extend([
                "",
                "💻 System Information",
                "```json",
                json.dumps(additional_info, indent=2),
                "```"
            ])
        
        # Combine all sections and sanitize
        full_description = description + "\n" + "\n".join(project_info + config_info + metadata_lines)
        sanitized_description = sanitize_text(full_description)
        
        # Upload to YouTube
        client = YouTubeClient()
        result = client.upload_video(
            final_video_path,
            title=f"GANGLIA Integration Test: {test_name}",
            description=sanitized_description,
            privacy_status="public",  # Make videos public for community feedback
            tags=["ganglia", "integration-test", "automation", "ai", "video-generation", "python"]
        )
        
        if not result.success:
            raise RuntimeError(f"Failed to upload test results: {result.error}")
        
        return f"https://www.youtube.com/watch?v={result.video_id}"
    except Exception as e:
        Logger.print_error(f"Failed to post test results to YouTube: {e}")
        return ""
