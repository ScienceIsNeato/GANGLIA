import os
import pytest

# API key availability flags - checked once at module load
OPENAI_API_KEY_AVAILABLE = bool(os.environ.get("OPENAI_API_KEY"))
FOXAI_SUNO_API_KEY_AVAILABLE = bool(os.environ.get("FOXAI_SUNO_API_KEY"))
SUNO_API_ORG_KEY_AVAILABLE = bool(os.environ.get("SUNO_API_ORG_KEY"))
GOOGLE_CREDENTIALS_AVAILABLE = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers",
        "third_party: mark test as a third party integration test"
    )
    config.addinivalue_line(
        "markers",
        "costly: mark test as computationally expensive or time-consuming"
    )
    config.addinivalue_line(
        "markers",
        "smoke: mark test as a smoke test (key functionality with mocks)"
    )
    config.addinivalue_line(
        "markers",
        "requires_openai: mark test as requiring OPENAI_API_KEY"
    )
    config.addinivalue_line(
        "markers",
        "requires_google: mark test as requiring GOOGLE_APPLICATION_CREDENTIALS"
    )
    config.addinivalue_line(
        "markers",
        "requires_suno: mark test as requiring Suno API keys"
    )

    # Log warnings about missing API keys at test session start
    if not OPENAI_API_KEY_AVAILABLE:
        print("\n⚠️  WARNING: OPENAI_API_KEY not set - tests requiring OpenAI will be skipped")
    if not GOOGLE_CREDENTIALS_AVAILABLE:
        print("⚠️  WARNING: GOOGLE_APPLICATION_CREDENTIALS not set - tests requiring Google Cloud will be skipped")
    if not FOXAI_SUNO_API_KEY_AVAILABLE and not SUNO_API_ORG_KEY_AVAILABLE:
        print("⚠️  WARNING: No Suno API keys set - tests requiring music generation will be skipped")


# Fixtures for API key requirements
@pytest.fixture
def requires_openai_key():
    """Skip test if OPENAI_API_KEY is not available."""
    if not OPENAI_API_KEY_AVAILABLE:
        pytest.skip("OPENAI_API_KEY not set")


@pytest.fixture
def requires_google_credentials():
    """Skip test if GOOGLE_APPLICATION_CREDENTIALS is not available."""
    if not GOOGLE_CREDENTIALS_AVAILABLE:
        pytest.skip("GOOGLE_APPLICATION_CREDENTIALS not set")


@pytest.fixture
def requires_suno_key():
    """Skip test if no Suno API keys are available."""
    if not FOXAI_SUNO_API_KEY_AVAILABLE and not SUNO_API_ORG_KEY_AVAILABLE:
        pytest.skip("No Suno API keys (FOXAI_SUNO_API_KEY or SUNO_API_ORG_KEY) set")
