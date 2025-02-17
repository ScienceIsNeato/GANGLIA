import pytest
from unittest.mock import Mock, patch
from music_lib import MusicGenerator, _exponential_backoff
from music_backends.gcui_suno import GcuiSunoBackend
from music_backends import MetaMusicBackend
from ttv.config_loader import TTVConfig

class MockSunoBackend(GcuiSunoBackend):
    def __init__(self, should_fail=False, fail_count=None):
        self.should_fail = should_fail
        self.fail_count = fail_count  # Number of times to fail before succeeding
        self.attempts = 0
        self.start_generation_called = False
        self.check_progress_called = False
        self.get_result_called = False

    def start_generation(self, prompt: str, **kwargs) -> str:
        self.start_generation_called = True
        self.attempts += 1

        if self.fail_count is not None:
            # Succeed after fail_count failures
            if self.attempts <= self.fail_count:
                return None
            return "mock_job_id"

        if self.should_fail:
            return None
        return "mock_job_id"

    def check_progress(self, job_id: str) -> tuple[str, float]:
        self.check_progress_called = True
        if self.should_fail:
            return "Failed", 0
        return "Complete", 100

    def get_result(self, job_id: str) -> str:
        self.get_result_called = True
        if self.should_fail:
            return None
        return "/mock/path/to/audio.mp3"

class MockMetaBackend(MetaMusicBackend):
    def __init__(self):
        self.start_generation_called = False
        self.check_progress_called = False
        self.get_result_called = False

    def start_generation(self, prompt: str, **kwargs) -> str:
        self.start_generation_called = True
        return "mock_meta_job_id"

    def check_progress(self, job_id: str) -> tuple[str, float]:
        self.check_progress_called = True
        return "Complete", 100

    def get_result(self, job_id: str) -> str:
        self.get_result_called = True
        return "/mock/path/to/meta_audio.wav"


def test_instrumental_generation_no_fallback_needed():
    """Test that Meta fallback is not used when Suno succeeds."""
    suno_backend = MockSunoBackend(should_fail=False)
    meta_backend = MockMetaBackend()

    generator = MusicGenerator()
    generator.backend = suno_backend
    generator.fallback_backend = meta_backend

    result = generator.generate_instrumental("test prompt")

    # Verify Suno was called
    assert suno_backend.start_generation_called
    assert suno_backend.check_progress_called
    assert suno_backend.get_result_called

    # Verify Meta was not called
    assert not meta_backend.start_generation_called
    assert not meta_backend.check_progress_called
    assert not meta_backend.get_result_called

    assert result == "/mock/path/to/audio.mp3"


@pytest.mark.costly
def test_instrumental_generation_with_retries_then_success():
    """Test instrumental generation with retries that eventually succeeds."""
    # Fail 3 times then succeed
    suno_backend = MockSunoBackend(fail_count=3)
    meta_backend = MockMetaBackend()

    generator = MusicGenerator()
    generator.backend = suno_backend
    generator.fallback_backend = meta_backend

    with patch('time.sleep'):  # Mock sleep to speed up test
        result = generator.generate_instrumental("test prompt")

    # Verify Suno was called multiple times
    assert suno_backend.attempts == 4  # 3 failures + 1 success
    assert suno_backend.check_progress_called
    assert suno_backend.get_result_called

    # Verify Meta was not called (since Suno eventually succeeded)
    assert not meta_backend.start_generation_called
    assert not meta_backend.check_progress_called
    assert not meta_backend.get_result_called

    assert result == "/mock/path/to/audio.mp3"


@pytest.mark.costly
def test_instrumental_generation_with_retries_then_fallback():
    """Test instrumental generation with retries that falls back to secondary backend."""
    suno_backend = MockSunoBackend(should_fail=True)
    meta_backend = MockMetaBackend()

    generator = MusicGenerator()
    generator.backend = suno_backend
    generator.fallback_backend = meta_backend

    with patch('time.sleep'):  # Mock sleep to speed up test
        result = generator.generate_instrumental("test prompt")

    # Verify Suno was attempted MAX_RETRIES times
    assert suno_backend.attempts == generator.MAX_RETRIES

    # Verify Meta was called as fallback
    assert meta_backend.start_generation_called
    assert meta_backend.check_progress_called
    assert meta_backend.get_result_called

    assert result == "/mock/path/to/meta_audio.wav"


def test_lyrics_generation_no_fallback():
    """Test that Meta fallback is not used for lyrics generation, even if Suno fails."""
    suno_backend = MockSunoBackend(should_fail=True)
    meta_backend = MockMetaBackend()

    generator = MusicGenerator()
    generator.backend = suno_backend
    generator.fallback_backend = meta_backend

    result = generator.generate_with_lyrics("test prompt", "test story")

    # Verify Suno was attempted
    assert suno_backend.start_generation_called

    # Verify Meta was not called
    assert not meta_backend.start_generation_called
    assert not meta_backend.check_progress_called
    assert not meta_backend.get_result_called

    assert result is None  # Should fail without fallback


@pytest.mark.costly
def test_instrumental_generation_no_fallback_configured():
    """Test instrumental generation with no fallback configured."""
    suno_backend = MockSunoBackend(should_fail=True)

    generator = MusicGenerator()
    generator.backend = suno_backend
    generator.fallback_backend = None

    with patch('time.sleep'):  # Mock sleep to speed up test
        result = generator.generate_instrumental("test prompt")

    # Verify Suno was attempted MAX_RETRIES times
    assert suno_backend.attempts == generator.MAX_RETRIES

    assert result is None  # Should fail with no fallback


def test_exponential_backoff():
    """Test that exponential backoff generates reasonable delays."""
    # Test a few attempts
    max_delay = 5  # Updated to match the actual max delay
    delays = [_exponential_backoff(i, max_delay=max_delay) for i in range(5)]

    # Verify delays increase exponentially until max delay
    for i in range(1, len(delays)):
        if delays[i-1] < max_delay:  # Only check increase if previous delay was below max
            assert delays[i] > delays[i-1], "Delays should increase exponentially until max"
        else:
            # Once we hit max delay, subsequent delays should be at max (with jitter)
            assert abs(delays[i] - max_delay) <= max_delay * 0.1, \
                f"Delay {i} should be close to max_delay (got {delays[i]})"

    # Verify max delay is respected
    large_attempt_delay = _exponential_backoff(10, max_delay=max_delay)
    assert large_attempt_delay <= max_delay * 1.1  # Allow for 10% jitter

    # Verify actual delay sequence is reasonable
    expected_base_delays = [1, 2, 4, 5, 5]  # Last two are capped at max_delay
    for i, delay in enumerate(delays):
        # Allow for 10% jitter in either direction
        assert abs(delay - expected_base_delays[i]) <= expected_base_delays[i] * 0.1, \
            f"Delay {i} should be close to {expected_base_delays[i]} (got {delay})"
