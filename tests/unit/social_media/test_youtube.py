"""Unit tests for the YouTube client."""

import os
import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from social_media.youtube_client import YouTubeClient, VideoUploadResult

# Mock data
MOCK_VIDEO_ID = "test_video_123"
MOCK_VIDEO_PATH = "test_video.mp4"
MOCK_VIDEO_TITLE = "Test Video"
MOCK_VIDEO_DESCRIPTION = "Test video description"

@pytest.fixture
def mock_service_account():
    """Mock service account credentials for testing."""
    with patch('google.oauth2.service_account.Credentials') as mock_creds:
        mock_creds.from_service_account_file.return_value = MagicMock()
        yield mock_creds

@pytest.fixture
def mock_youtube_build():
    """Mock YouTube API client build."""
    with patch('social_media.youtube_client.build') as mock_build:
        mock_service = MagicMock()
        # Mock the videos().list() call for permission validation
        mock_list = MagicMock()
        mock_list.execute.return_value = {'items': []}
        mock_service.videos().list.return_value = mock_list
        mock_build.return_value = mock_service
        yield mock_service

@pytest.fixture
def youtube_client(mock_service_account, mock_youtube_build):
    """Create a YouTubeClient instance with mocked dependencies."""
    return YouTubeClient()

def test_upload_video_success(youtube_client, mock_youtube_build):
    """Test successful video upload."""
    # Mock the video insert request
    mock_request = MagicMock()
    mock_request.next_chunk.return_value = (None, {'id': MOCK_VIDEO_ID})
    
    mock_youtube_build.videos().insert.return_value = mock_request
    
    # Create a temporary test video file
    with open(MOCK_VIDEO_PATH, 'wb') as f:
        f.write(b'dummy video content')
    
    try:
        result = youtube_client.upload_video(
            MOCK_VIDEO_PATH,
            MOCK_VIDEO_TITLE,
            description=MOCK_VIDEO_DESCRIPTION,
            privacy_status="public"  # Now defaulting to public
        )
        
        assert result.success is True
        assert result.video_id == MOCK_VIDEO_ID
        assert result.error is None
        
        # Verify API call with public privacy status
        mock_youtube_build.videos().insert.assert_called_once()
        call_args = mock_youtube_build.videos().insert.call_args
        assert call_args[1]['body']['status']['privacyStatus'] == 'public'
        
    finally:
        # Clean up test file
        if os.path.exists(MOCK_VIDEO_PATH):
            os.remove(MOCK_VIDEO_PATH)

def test_upload_video_file_not_found(youtube_client):
    """Test video upload with non-existent file."""
    result = youtube_client.upload_video(
        "nonexistent.mp4",
        MOCK_VIDEO_TITLE
    )
    
    assert result.success is False
    assert "Video file not found" in result.error
    assert result.video_id is None

def test_upload_video_api_error(youtube_client, mock_youtube_build):
    """Test video upload with API error."""
    # Mock API error
    mock_request = MagicMock()
    mock_request.next_chunk.side_effect = Exception("API Error")
    
    mock_youtube_build.videos().insert.return_value = mock_request
    
    # Create a temporary test video file
    with open(MOCK_VIDEO_PATH, 'wb') as f:
        f.write(b'dummy video content')
    
    try:
        result = youtube_client.upload_video(
            MOCK_VIDEO_PATH,
            MOCK_VIDEO_TITLE
        )
        
        assert result.success is False
        assert "API Error" in result.error
        assert result.video_id is None
        
    finally:
        # Clean up test file
        if os.path.exists(MOCK_VIDEO_PATH):
            os.remove(MOCK_VIDEO_PATH)

def test_get_video_status_success(youtube_client, mock_youtube_build):
    """Test successful video status retrieval."""
    mock_response = {
        'items': [{
            'id': MOCK_VIDEO_ID,
            'status': {'privacyStatus': 'public'},  # Now expecting public
            'snippet': {'title': MOCK_VIDEO_TITLE}
        }]
    }
    
    mock_request = MagicMock()
    mock_request.execute.return_value = mock_response
    mock_youtube_build.videos().list.return_value = mock_request
    
    status = youtube_client.get_video_status(MOCK_VIDEO_ID)
    
    assert status['id'] == MOCK_VIDEO_ID
    assert status['status']['privacyStatus'] == 'public'  # Verify it's public
    assert status['snippet']['title'] == MOCK_VIDEO_TITLE
    
    # Verify API call
    mock_youtube_build.videos().list.assert_called_with(
        part="status,snippet",
        id=MOCK_VIDEO_ID
    )

def test_get_video_status_not_found(youtube_client, mock_youtube_build):
    """Test video status retrieval for non-existent video."""
    mock_response = {'items': []}
    
    mock_request = MagicMock()
    mock_request.execute.return_value = mock_response
    mock_youtube_build.videos().list.return_value = mock_request
    
    status = youtube_client.get_video_status(MOCK_VIDEO_ID)
    
    assert status == {} 