"""Color utilities for video caption generation.

This module provides functionality for:
1. Generating vibrant color palettes
2. Calculating complementary colors
3. Mixing colors
4. Finding optimal text colors for contrast
"""

from colorsys import rgb_to_hsv, hsv_to_rgb
from typing import Tuple, List

import numpy as np

def get_vibrant_palette() -> List[Tuple[int, int, int]]:
    """Get a list of vibrant colors for captions.
    
    Returns:
        List[Tuple[int, int, int]]: List of RGB color tuples
    """
    return [
        (240, 46, 230),   # Hot Pink
        (157, 245, 157),  # Lime Green
        (52, 235, 222),   # Cyan
        (247, 158, 69),   # Bright Orange
        (247, 247, 17),   # Hot Yellow
        (167, 96, 247)    # Royal Purple
    ]

def get_color_complement(color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """
    Calculate the complement of a color using HSV color space for better results.
    
    Args:
        color: RGB color tuple
        
    Returns:
        RGB color tuple of the complement
    """
    # Convert RGB to HSV
    r, g, b = [x/255.0 for x in color]
    h, s, v = rgb_to_hsv(r, g, b)
    
    # Calculate complement by shifting hue by 180 degrees
    h = (h + 0.5) % 1.0
    
    # Convert back to RGB
    r, g, b = hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))

def mix_colors(color1: Tuple[int, int, int], color2: Tuple[int, int, int], ratio: float = 0.8) -> Tuple[int, int, int]:
    """
    Mix two colors with a given ratio.
    
    Args:
        color1: First RGB color tuple (primary color)
        color2: Second RGB color tuple (secondary color)
        ratio: Weight of the first color (0.0 to 1.0)
        
    Returns:
        RGB color tuple of the mixed color
    """
    r = int(color1[0] * ratio + color2[0] * (1 - ratio))
    g = int(color1[1] * ratio + color2[1] * (1 - ratio))
    b = int(color1[2] * ratio + color2[2] * (1 - ratio))
    return (r, g, b)

def get_contrasting_color(frame: np.ndarray, roi: Tuple[int, int, int, int]) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """
    Determine vibrant text color and stroke color based on ROI background.
    Uses a predefined palette of vibrant colors and mixes with background color.
    
    Args:
        frame: Video frame as numpy array
        roi: Tuple of (x, y, width, height) defining the ROI
        
    Returns:
        Tuple of (text_color, stroke_color) as RGB tuples
    """
    x, y, width, height = roi
    roi_region = frame[y:y+height, x:x+width]
    
    # Calculate average color in ROI
    avg_color = tuple(map(int, np.mean(roi_region, axis=(0, 1))))
    
    # Get complement of average color
    complement = get_color_complement(avg_color)
    
    # Find the palette color closest to the complement
    palette = get_vibrant_palette()
    closest_color = min(palette, key=lambda c: sum((a - b) ** 2 for a, b in zip(c, complement)))
    
    # Mix the chosen color with the background
    text_color = mix_colors(closest_color, avg_color, 0.8)
    
    # Create a darker stroke color (30% of text color)
    stroke_color = tuple(int(c * 0.3) for c in text_color)
    
    return text_color, stroke_color
