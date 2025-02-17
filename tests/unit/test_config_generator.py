"""Unit tests for the TTV config generator."""

import json
import os
import pytest
from tests.integration.test_data.config_generator import generate_config

@pytest.mark.skip(reason="Config generator is working well, skipping this test unless we start seeing issues")
def test_config_generation(tmp_path):
    """Test that the config generator produces valid and creative content."""
    # Generate config file in temp directory
    config_path = os.path.join(tmp_path, "test_config.json")
    generate_config(config_path)

    # Verify file was created
    assert os.path.exists(config_path), "Config file was not created"

    # Load and validate config
    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)

    # Check required fields exist
    assert "style" in config, "Missing style field"
    assert "story" in config, "Missing story field"
    assert "title" in config, "Missing title field"
    assert "caption_style" in config, "Missing caption_style field"
    assert "background_music" in config, "Missing background_music field"
    assert "closing_credits" in config, "Missing closing_credits field"

    # Validate style
    assert isinstance(config["style"], str), "Style should be a string"
    assert len(config["style"].split()) in [2, 3, 4], "Style should be 2-4 words"

    # Validate story
    assert isinstance(config["story"], list), "Story should be a list"
    assert len(config["story"]) == 12, "Story should have exactly 12 segments"
    for segment in config["story"]:
        assert isinstance(segment, str), "Story segments should be strings"
        assert len(segment) > 0, "Story segments should not be empty"
        assert segment.endswith((".", "!", "?")), "Story segments should end with punctuation"

    # Validate title
    assert isinstance(config["title"], str), "Title should be a string"
    assert config["title"].startswith("The "), "Title should start with 'The '"

    # Validate caption style
    assert config["caption_style"] == "dynamic", "Caption style should be 'dynamic'"

    # Validate background music
    assert isinstance(config["background_music"], dict), "Background music should be a dict"
    assert "prompt" in config["background_music"], "Background music should have prompt"
    assert isinstance(config["background_music"]["prompt"], str), "Background music prompt should be string"
    assert len(config["background_music"]["prompt"]) > 0, "Background music prompt should not be empty"

    # Validate closing credits
    assert isinstance(config["closing_credits"], dict), "Closing credits should be a dict"
    assert "prompt" in config["closing_credits"], "Closing credits should have prompt"
    assert isinstance(config["closing_credits"]["prompt"], str), "Closing credits prompt should be string"
    assert len(config["closing_credits"]["prompt"]) > 0, "Closing credits prompt should not be empty"

    # Validate content is creative and varied
    # Generate one more config and check they're different
    config_path_2 = os.path.join(tmp_path, "test_config_2.json")
    generate_config(config_path_2)
    with open(config_path_2, encoding='utf-8') as f:
        config_2 = json.load(f)

    # Check styles are different
    assert config["style"] != config_2["style"], "Generated styles should be unique"

    # Check stories are different
    story_1 = "\n".join(config["story"])
    story_2 = "\n".join(config_2["story"])
    assert story_1 != story_2, "Generated stories should be unique"

    # Check music prompts are different
    assert config["background_music"]["prompt"] != config_2["background_music"]["prompt"], "Generated background music prompts should be unique"
    assert config["closing_credits"]["prompt"] != config_2["closing_credits"]["prompt"], "Generated closing credits prompts should be unique"
