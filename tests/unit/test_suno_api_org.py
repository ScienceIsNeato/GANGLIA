"""Unit tests for the SunoApi.org backend implementation."""

import os
import json
from unittest.mock import patch, MagicMock, mock_open
import pytest
from music_backends.suno_api_org import SunoApiOrgBackend

@pytest.fixture
def mock_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv('SUNO_API_ORG_KEY', 'test_api_key')

@pytest.fixture
def backend(mock_env, tmp_path):
    """Create a SunoApiOrgBackend instance with mocked environment."""
    with patch('music_backends.suno_api_org.get_tempdir', return_value=str(tmp_path)):
        return SunoApiOrgBackend()

def test_init_missing_api_key():
    """Test initialization fails without API key."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(EnvironmentError, match="Environment variable 'SUNO_API_ORG_KEY' is not set"):
            SunoApiOrgBackend()

def test_start_generation_instrumental(backend):
    """Test starting instrumental generation."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": "test_job_id",
            "status": "PENDING"
        }
    }

    with patch('requests.request', return_value=mock_response) as mock_request:
        job_id = backend.start_generation(
            prompt="test prompt",
            with_lyrics=False,
            title="Test Song",
            tags="rock electronic",
            duration=45
        )

        assert job_id == "test_job_id"
        mock_request.assert_called_once()

        # Verify request data
        call_args = mock_request.call_args
        assert call_args[0][0] == "post"  # First arg is method
        assert call_args[0][1] == "https://apibox.erweima.ai/api/v1/generate"  # Second arg is endpoint
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_api_key"

        sent_data = json.loads(json.dumps(call_args[1]["json"]))
        assert "Create a 45-second test prompt" in sent_data["prompt"]
        assert sent_data["instrumental"] is True
        assert sent_data["customMode"] is True

def test_start_generation_with_lyrics(backend):
    """Test starting generation with lyrics."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": "test_job_id",
            "status": "PENDING"
        }
    }

    with patch('requests.request', return_value=mock_response) as mock_request:
        job_id = backend.start_generation(
            prompt="test prompt",
            with_lyrics=True,
            title="Test Song",
            tags="pop vocal",
            story_text="Test story for lyrics",
            duration=60
        )

        assert job_id == "test_job_id"
        mock_request.assert_called_once()

        # Verify request data
        call_args = mock_request.call_args
        assert call_args[0][0] == "post"  # First arg is method
        assert call_args[0][1] == "https://apibox.erweima.ai/api/v1/generate"  # Second arg is endpoint
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_api_key"

        sent_data = json.loads(json.dumps(call_args[1]["json"]))
        assert "Create a 60-second test prompt" in sent_data["prompt"]
        assert sent_data["instrumental"] is False
        assert sent_data["customMode"] is True
        assert sent_data["lyrics"] == "Test story for lyrics"

def test_check_progress(backend):
    """Test checking generation progress."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": "test_job_id",
            "status": "TEXT_SUCCESS",
            "param": '{"title": "Test Song"}',
            "response": {
                "taskId": "test_job_id",
                "sunoData": [{
                    "id": "test_song_id",
                    "streamAudioUrl": "https://example.com/test.mp3",
                    "title": "Test Song",
                    "duration": 45
                }]
            }
        }
    }

    with patch('requests.request', return_value=mock_response) as mock_request:
        with patch('time.time', return_value=1000):  # Mock current time
            with patch.object(backend, '_get_start_time', return_value=980):  # Mock start time 20s ago
                status, progress = backend.check_progress("test_job_id")

                assert "Test Song" in status
                assert "Processing lyrics" in status
                assert progress > 0
                mock_request.assert_called_once()

def test_get_result(backend):
    """Test getting generation result."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": "test_job_id",
            "status": "FIRST_SUCCESS",
            "response": {
                "taskId": "test_job_id",
                "sunoData": [{
                    "id": "test_song_id",
                    "streamAudioUrl": "https://example.com/test.mp3",
                    "title": "Test Song",
                    "duration": 45
                }]
            }
        }
    }

    mock_download_response = MagicMock()
    mock_download_response.status_code = 200
    mock_download_response.headers = {"content-length": "1000"}
    mock_download_response.iter_content.return_value = [b"test audio data"]
    mock_download_response.ok = True

    with patch('requests.request', side_effect=[mock_response, mock_download_response]) as mock_request:
        with patch('builtins.open', mock_open()) as mock_file:
            result = backend.get_result("test_job_id")

            assert result is not None
            assert mock_request.call_count == 2
            mock_file.assert_called_once()

def test_generate_instrumental_success(backend):
    """Test successful instrumental generation flow."""
    # Mock the API responses for the full generation flow
    mock_start_response = MagicMock()
    mock_start_response.status_code = 200
    mock_start_response.json.return_value = {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": "test_job_id",
            "status": "PENDING"
        }
    }

    mock_check_response = MagicMock()
    mock_check_response.status_code = 200
    mock_check_response.json.return_value = {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": "test_job_id",
            "status": "FIRST_SUCCESS",
            "param": '{"title": "Test Instrumental"}',
            "response": {
                "taskId": "test_job_id",
                "sunoData": [{
                    "id": "test_song_id",
                    "streamAudioUrl": "https://example.com/test.mp3",
                    "title": "Test Instrumental",
                    "duration": 45
                }]
            }
        }
    }

    mock_result_response = MagicMock()
    mock_result_response.status_code = 200
    mock_result_response.json.return_value = {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": "test_job_id",
            "status": "FIRST_SUCCESS",
            "response": {
                "taskId": "test_job_id",
                "sunoData": [{
                    "id": "test_song_id",
                    "streamAudioUrl": "https://example.com/test.mp3",
                    "title": "Test Instrumental",
                    "duration": 45
                }]
            }
        }
    }

    mock_download_response = MagicMock()
    mock_download_response.status_code = 200
    mock_download_response.headers = {"content-length": "1000"}
    mock_download_response.iter_content.return_value = [b"test audio data"]
    mock_download_response.ok = True

    with patch('requests.request', side_effect=[mock_start_response, mock_check_response, mock_result_response, mock_download_response]) as mock_request:
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('time.sleep'):  # Mock sleep to speed up test
                with patch.object(backend, '_get_start_time', return_value=980):  # Mock start time
                    result = backend.generate_instrumental(
                        prompt="test instrumental",
                        title="Test Instrumental",
                        tags="electronic"
                    )

                    assert result is not None
                    assert mock_request.call_count == 4
                    mock_file.assert_called()

def test_generate_with_lyrics_success(backend):
    """Test successful generation with lyrics flow."""
    # Mock the API responses for the full generation flow
    mock_start_response = MagicMock()
    mock_start_response.status_code = 200
    mock_start_response.json.return_value = {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": "test_job_id",
            "status": "PENDING"
        }
    }

    mock_check_response = MagicMock()
    mock_check_response.status_code = 200
    mock_check_response.json.return_value = {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": "test_job_id",
            "status": "FIRST_SUCCESS",
            "param": '{"title": "Test Song"}',
            "response": {
                "taskId": "test_job_id",
                "sunoData": [{
                    "id": "test_song_id",
                    "streamAudioUrl": "https://example.com/test.mp3",
                    "title": "Test Song",
                    "duration": 45,
                    "lyrics": "Test lyrics"
                }]
            }
        }
    }

    mock_result_response = MagicMock()
    mock_result_response.status_code = 200
    mock_result_response.json.return_value = {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": "test_job_id",
            "status": "FIRST_SUCCESS",
            "response": {
                "taskId": "test_job_id",
                "sunoData": [{
                    "id": "test_song_id",
                    "streamAudioUrl": "https://example.com/test.mp3",
                    "title": "Test Song",
                    "duration": 45,
                    "lyrics": "Test lyrics"
                }]
            }
        }
    }

    mock_download_response = MagicMock()
    mock_download_response.status_code = 200
    mock_download_response.headers = {"content-length": "1000"}
    mock_download_response.iter_content.return_value = [b"test audio data"]
    mock_download_response.ok = True

    with patch('requests.request', side_effect=[mock_start_response, mock_check_response, mock_result_response, mock_download_response]) as mock_request:
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('time.sleep'):  # Mock sleep to speed up test
                with patch.object(backend, '_get_start_time', return_value=980):  # Mock start time
                    result, lyrics = backend.generate_with_lyrics(
                        prompt="test song",
                        story_text="Test story for lyrics",
                        title="Test Song",
                        tags="pop"
                    )

                    assert result is not None
                    assert lyrics == "Test story for lyrics"  # Story text is returned as lyrics
                    assert mock_request.call_count == 4
                    mock_file.assert_called()
