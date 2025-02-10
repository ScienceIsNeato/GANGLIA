"""Live integration tests for YouTube client.

These tests require a valid Google Cloud service account with YouTube Data API access.
The service account credentials should be set in GOOGLE_APPLICATION_CREDENTIALS environment variable.

The tests will upload actual videos to your YouTube channel as public content.
Please be aware that public videos will be visible to everyone.
"""

import os
import pytest
import tempfile
from pathlib import Path

from social_media.youtube_client import YouTubeClient
from utils.video_utils import create_moving_rectangle_video

# Skip all tests if service account credentials are not set
pytestmark = pytest.mark.skipif(
    not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
    reason="Google Cloud service account credentials not set in environment variables"
)

@pytest.fixture
def test_video():
    """Create a test video file."""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        video_path = f.name
    
    # Create a simple test video
    create_moving_rectangle_video(video_path)
    
    yield video_path
    
    # Cleanup
    if os.path.exists(video_path):
        os.remove(video_path)

@pytest.fixture
def youtube_client():
    """Create a YouTubeClient instance."""
    return YouTubeClient()

def test_upload_video(youtube_client, test_video):
    """Test uploading a video to YouTube."""
    title = "GANGLIA Test Video"
    description = "This is a test video uploaded by GANGLIA's test suite. It demonstrates video upload capabilities with a simple animation."
    tags = ["test", "ganglia", "automation", "python", "api"]
    
    result = youtube_client.upload_video(
        test_video,
        title,
        description=description,
        privacy_status="public",  # Make the video public
        tags=tags
    )
    
    assert result.success is True, f"Upload failed: {result.error}"
    assert result.video_id is not None
    assert result.error is None
    
    # Verify video status
    status = youtube_client.get_video_status(result.video_id)
    assert status['snippet']['title'] == title
    assert status['snippet']['description'] == description
    assert status['status']['privacyStatus'] == "public"  # Verify it's public
    assert all(tag in status['snippet']['tags'] for tag in tags)
    
    # Print the video URL for easy access
    video_url = f"https://www.youtube.com/watch?v={result.video_id}"
    print(f"\nVideo uploaded successfully! You can view it at: {video_url}") 