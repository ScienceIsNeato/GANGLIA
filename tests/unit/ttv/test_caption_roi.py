"""Tests for caption ROI detection functionality."""

import numpy as np
from ttv.caption_roi import find_roi_in_frame
from ttv.color_utils import get_contrasting_color


def test_roi_dimensions():
    """Test that ROI dimensions are correctly calculated and proportioned."""
    # Create a test frame with known dimensions
    frame = np.zeros((1080, 1920, 3))  # Standard 1080p frame

    roi = find_roi_in_frame(frame)
    assert roi is not None, "ROI detection failed"

    x, y, width, height = roi

    # Calculate 10% border size
    border_x = int(1920 * 0.1)
    border_y = int(1080 * 0.1)

    # Test ROI is within frame bounds, considering the border
    assert x >= border_x and x + width <= 1920 - border_x, "ROI x-coordinates out of bounds"
    assert y >= border_y and y + height <= 1080 - border_y, "ROI y-coordinates out of bounds"

    # Test ROI has portrait orientation (taller than wide)
    assert height > width, "ROI should be taller than wide"

    # Test ROI size is reasonable (around 1/7th of frame area)
    frame_area = (1080 - 2 * border_y) * (1920 - 2 * border_x)
    roi_area = width * height
    ratio = roi_area / frame_area
    assert 0.1 <= ratio <= 0.2, f"ROI area ratio {ratio} outside expected range"


def test_contrasting_color_dark_background():
    """Test color selection for dark backgrounds."""
    # Test different dark backgrounds
    test_cases = [
        (np.zeros((100, 100, 3)), (255, 255, 255), (85, 85, 85)),  # Black -> White
        (np.ones((100, 100, 3)) * [50, 0, 0], (231, 255, 255), (77, 85, 85)),  # Dark red -> Light cyan
        (np.ones((100, 100, 3)) * [0, 50, 0], (255, 205, 255), (85, 68, 85)),  # Dark green -> Light magenta
    ]

    roi = (25, 25, 50, 50)  # Center ROI
    for frame, expected_color, expected_stroke in test_cases:
        text_color, stroke_color = get_contrasting_color(frame, roi)
        # Allow for small differences in RGB values
        for actual, expected in zip(text_color, expected_color):
            assert abs(actual - expected) <= 2, f"Color value {actual} too far from expected {expected}"
        for actual, expected in zip(stroke_color, expected_stroke):
            assert abs(actual - expected) <= 2, f"Stroke value {actual} too far from expected {expected}"


def test_contrasting_color_light_background():
    """Test color selection for light backgrounds."""
    # Test different light backgrounds
    test_cases = [
        (np.ones((100, 100, 3)) * 255, (0, 0, 0), (255, 255, 255)),  # White -> Black with white stroke
        (np.ones((100, 100, 3)) * [200, 150, 150], (231, 255, 255), (77, 85, 85)),  # Light red -> Light cyan
        (np.ones((100, 100, 3)) * [150, 200, 150], (255, 205, 255), (85, 68, 85)),  # Light green -> Light magenta
    ]

    roi = (25, 25, 50, 50)  # Center ROI
    for frame, expected_color, expected_stroke in test_cases:
        text_color, stroke_color = get_contrasting_color(frame, roi)
        # Allow for small differences in RGB values
        for actual, expected in zip(text_color, expected_color):
            assert abs(actual - expected) <= 2, f"Color value {actual} too far from expected {expected}"
        for actual, expected in zip(stroke_color, expected_stroke):
            assert abs(actual - expected) <= 2, f"Stroke value {actual} too far from expected {expected}"


def test_contrasting_color_gradient():
    """Test color selection across a color gradient."""
    # Create a gradient frame from black to colored
    frame = np.zeros((100, 100, 3))
    for i in range(100):
        # Create a gradient that transitions from black to red
        frame[:, i] = [i * 2.55, 0, 0]

    # Test ROIs in different regions
    dark_roi = (0, 0, 20, 20)  # Dark region
    light_roi = (80, 0, 20, 20)  # Light/red region

    # Dark region should get light cyan for dark red
    text_color, stroke_color = get_contrasting_color(frame, dark_roi)
    # For gradient test, use relative tolerance since we're doing color calculations
    for actual, expected in zip(text_color, (231, 255, 255)):
        rel_diff = abs(actual - expected) / max(expected, 1) * 100
        assert rel_diff <= 2, f"Color value {actual} differs from expected {expected} by {rel_diff}%"
    for actual, expected in zip(stroke_color, (77, 85, 85)):
        rel_diff = abs(actual - expected) / max(expected, 1) * 100
        assert rel_diff <= 2, f"Stroke value {actual} differs from expected {expected} by {rel_diff}%"

    # Light red region should get light cyan
    text_color, stroke_color = get_contrasting_color(frame, light_roi)
    for actual, expected in zip(text_color, (205, 255, 255)):
        rel_diff = abs(actual - expected) / max(expected, 1) * 100
        assert rel_diff <= 2, f"Color value {actual} differs from expected {expected} by {rel_diff}%"
    for actual, expected in zip(stroke_color, (68, 85, 85)):
        rel_diff = abs(actual - expected) / max(expected, 1) * 100
        assert rel_diff <= 2, f"Stroke value {actual} differs from expected {expected} by {rel_diff}%"


def test_roi_activity_detection():
    """Test that ROI prefers low-activity regions."""
    # Create a frame with a high-activity region (random noise)
    frame = np.zeros((500, 500, 3))
    # Add noise to the top half
    frame[:250, :] = np.random.rand(250, 500, 3) * 255

    roi = find_roi_in_frame(frame)
    assert roi is not None, "ROI detection failed"

    _, y, _, height = roi
    # ROI should prefer the quiet bottom half
    assert y + height > 250, "ROI should prefer low-activity region"
