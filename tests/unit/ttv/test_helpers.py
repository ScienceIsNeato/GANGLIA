"""Helper functions for testing video caption functionality."""

import cv2
import numpy as np
from collections import Counter

def get_vibrant_palette():
    """Get the vibrant color palette.
    
    Returns:
        list: List of (B,G,R) color tuples
    """
    return [
        (240, 46, 230),   # Vibrant pink
        (157, 245, 157),  # Vibrant green
        (52, 235, 222),   # Vibrant cyan
        (247, 158, 69),   # Vibrant orange
        (247, 247, 17),   # Vibrant yellow
        (167, 96, 247)    # Vibrant purple
    ]

def find_closest_palette_color(color):
    """Find the closest color from the vibrant palette.
    
    Args:
        color: (B,G,R) color tuple
        
    Returns:
        tuple: (closest_color, difference)
    """
    palette = get_vibrant_palette()
    color_diffs = [sum(abs(c1 - c2) for c1, c2 in zip(color, palette_color)) 
                  for palette_color in palette]
    min_diff = min(color_diffs)
    closest_color = palette[color_diffs.index(min_diff)]
    return closest_color, min_diff

def get_text_colors_from_frame(frame):
    """Extract text colors from a video frame by finding text character borders and fill.
    
    Args:
        frame: The video frame to analyze
        
    Returns:
        tuple: (text_color, stroke_color) where each color is a tuple of (B,G,R) values
    """
    # Convert to grayscale for edge detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Use Canny edge detection to find text borders
    edges = cv2.Canny(gray, 100, 200)
    
    # Dilate edges to get stroke area
    kernel = np.ones((3,3), np.uint8)
    stroke_area = cv2.dilate(edges, kernel, iterations=1)
    
    # Create a mask for the text fill area (inside the strokes)
    fill_area = cv2.floodFill(stroke_area.copy(), None, (0,0), 255)[1]
    fill_area = cv2.bitwise_not(fill_area)
    fill_area = cv2.erode(fill_area, kernel, iterations=1)
    
    # Get colors from stroke and fill areas
    stroke_colors = frame[stroke_area > 0]
    fill_colors = frame[fill_area > 0]
    
    if len(stroke_colors) == 0 or len(fill_colors) == 0:
        print("No text colors found")
        return None, None
    
    # Get the most common colors
    fill_color_counts = Counter([tuple(int(x) for x in color) for color in fill_colors])
    sorted_fill_colors = sorted(fill_color_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Find the most common color that's close to a palette color
    text_color = None
    min_diff = float('inf')
    for color, _ in sorted_fill_colors:
        closest_color, diff = find_closest_palette_color(color)
        if diff < min_diff:
            text_color = closest_color
            min_diff = diff
            if diff <= 30:  # If we find a close match, use it immediately
                break
    
    if text_color is None:
        print("No colors close to palette found")
        return None, None
    
    # Create stroke color as exactly 1/3 intensity of text color
    stroke_color = tuple(max(1, c // 3) for c in text_color)
    
    print(f"Found text color: {text_color}, stroke color: {stroke_color}")
    return text_color, stroke_color

def get_text_colors_from_video(video_path, frame_idx=0):
    """Extract text colors from a specific frame in a video.
    
    Args:
        video_path: Path to the video file
        frame_idx: Index of the frame to analyze
        
    Returns:
        tuple: (text_color, stroke_color) where each color is a tuple of (B,G,R) values,
               or (None, None) if colors cannot be extracted
    """
    cap = cv2.VideoCapture(video_path)
    
    try:
        # Set frame position
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        
        # Read frame
        ret, frame = cap.read()
        if not ret:
            return None, None
            
        return get_text_colors_from_frame(frame)
        
    finally:
        cap.release() 