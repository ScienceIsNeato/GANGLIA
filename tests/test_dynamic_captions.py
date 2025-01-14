import os
import tempfile
from utils import get_tempdir
from PIL import Image
from ttv.video_generation import run_ffmpeg_command
from ttv.captions import CaptionEntry, create_dynamic_captions, create_srt_captions, Word, create_caption_windows
from logger import Logger

def create_test_video(duration=5, size=(1920, 1080), color=(0, 0, 255)):
    """Create a simple colored background video for testing"""
    # Create a colored image using PIL
    image = Image.new('RGB', size, color)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as img_file:
        image.save(img_file.name)
        # Convert still image to video using ffmpeg
        video_path = img_file.name.replace('.png', '.mp4')
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", img_file.name,
            "-c:v", "libx264", "-t", str(duration),
            "-pix_fmt", "yuv420p", video_path
        ]
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result is None:
            Logger.print_error("Failed to create test video")
            return None
        os.unlink(img_file.name)
        return video_path

def test_caption_text_completeness():
    """Test that all words from the original caption appear in the dynamic captions"""
    original_text = "This is a test caption with multiple words that should all appear in the output"
    # Split into words and verify all words are present
    words = original_text.split()
    # Use standard 720p dimensions for testing
    width, height = 1280, 720
    margin = 40
    max_window_height_ratio = 0.3
    # Calculate safe dimensions
    safe_width = width - (2 * margin)
    safe_height = int(height * max_window_height_ratio)
    windows = create_caption_windows(
        [Word(text=w, start_time=0, end_time=1) for w in words],
        min_font_size=32,
        max_font_size=48,
        safe_width=safe_width,
        safe_height=safe_height
    )
    # Collect all words from all windows
    processed_words = []
    for window in windows:
        processed_words.extend(word.text for word in window.words)
    assert set(words) == set(processed_words), "Not all words from original caption are present in processed output"

def test_font_size_scaling():
    """Test that font sizes are properly scaled based on video dimensions"""
    # Create test video with specific dimensions
    video_size = (1280, 720)  # 720p test video
    input_video_path = create_test_video(size=video_size)
    assert input_video_path is not None, "Failed to create test video"
    # Create output path
    output_path = os.path.join(get_tempdir(), "output_font_test.mp4")
    # Test with various caption lengths
    test_cases = [
        "Short caption",  # Should use larger font
        "This is a much longer caption that should use a smaller font size to fit properly",
        "🎉 Testing with emojis and special characters !@#$%"
    ]
    captions = [CaptionEntry(text, idx * 2.0, (idx + 1) * 2.0) for idx, text in enumerate(test_cases)]
    # Add dynamic captions
    result_path = create_dynamic_captions(
        input_video=input_video_path,
        captions=captions,
        output_path=output_path,
        min_font_size=24,  # Smaller min to test scaling
        max_font_size=72,  # Larger max to test scaling
        margin=40,
        max_window_height_ratio=0.3  # Limit window height to 30% of video height
    )
    # Clean up
    os.unlink(input_video_path)
    assert result_path is not None, "Failed to create video with font size testing"
    assert os.path.exists(output_path), f"Output file not created: {output_path}"
    assert os.path.getsize(output_path) > 0, "Output file is empty"

def test_caption_positioning():
    """Test that captions stay within the safe viewing area"""
    # Create test video with specific dimensions
    video_size = (1920, 1080)
    input_video_path = create_test_video(size=video_size)
    assert input_video_path is not None, "Failed to create test video"
    # Create output path
    output_path = os.path.join(get_tempdir(), "output_position_test.mp4")
    # Test with long captions that might overflow
    test_cases = [
        # Long single line to test horizontal overflow
        "This is a very long caption that should not extend beyond the right margin of the video frame",
        # Multiple short lines to test vertical spacing
        "Line one\nLine two\nLine three",
        # Long words that might cause overflow
        "Supercalifragilisticexpialidocious Pneumonoultramicroscopicsilicovolcanoconiosis",
        # Emojis and special characters
        "🌟 Testing with emojis 🎬 and special characters !@#$% to ensure proper spacing"
    ]
    captions = [
        CaptionEntry(text, idx * 2.0, (idx + 1) * 2.0)
        for idx, text in enumerate(test_cases)
    ]
    # Add dynamic captions with specific margin
    margin = 40
    result_path = create_dynamic_captions(
        input_video=input_video_path,
        captions=captions,
        output_path=output_path,
        margin=margin,
        min_font_size=32,  # Ensure readable text
        max_font_size=48,  # Limit maximum size to avoid overflow
        max_window_height_ratio=0.3  # Limit window height to 30% of video height
    )
    # Clean up
    os.unlink(input_video_path)
    assert result_path is not None, "Failed to create video with position testing"
    assert os.path.exists(output_path), f"Output file not created: {output_path}"
    assert os.path.getsize(output_path) > 0, "Output file is empty"
    # Verify video dimensions and format using ffprobe
    ffprobe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        output_path
    ]
    dimensions = run_ffmpeg_command(ffprobe_cmd)
    assert dimensions is not None, "Failed to get video dimensions"
    # Parse dimensions
    width, height = map(int, dimensions.stdout.decode('utf-8').strip().split(','))
    assert width == video_size[0], "Output video width does not match input"
    assert height == video_size[1], "Output video height does not match input"
    # Create a temporary directory for frame extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract frames where captions should be visible
        frames_cmd = [
            "ffmpeg", "-i", output_path,
            "-vf", "fps=1",  # Extract one frame per second
            "-frame_pts", "1",  # Include presentation timestamp
            os.path.join(temp_dir, "frame_%d.png")
        ]
        result = run_ffmpeg_command(frames_cmd)
        assert result is not None, "Failed to extract frames"
        # Check each frame to ensure text is within bounds
        for frame_file in os.listdir(temp_dir):
            if not frame_file.endswith('.png'):
                continue
            frame_path = os.path.join(temp_dir, frame_file)
            with Image.open(frame_path) as img:
                # Get frame dimensions
                frame_width, frame_height = img.size
                # Convert to RGB for analysis
                rgb_img = img.convert('RGB')
                # Scan the margins to ensure no text pixels
                for y in range(frame_height):
                    # Check left margin
                    color = rgb_img.getpixel((margin-1, y))
                    # Allow for slight color variations due to video encoding
                    assert abs(color[0] - 0) <= 5 and abs(color[1] - 0) <= 5 and abs(color[2] - 255) <= 5, \
                        f"Found text in left margin at y={y}"
                    # Check right margin
                    color = rgb_img.getpixel((frame_width-margin, y))
                    assert abs(color[0] - 0) <= 5 and abs(color[1] - 0) <= 5 and abs(color[2] - 255) <= 5, \
                        f"Found text in right margin at y={y}"
                # Check bottom margin
                for x in range(frame_width):
                    color = rgb_img.getpixel((x, frame_height-margin))
                    assert abs(color[0] - 0) <= 5 and abs(color[1] - 0) <= 5 and abs(color[2] - 255) <= 5, \
                        f"Found text in bottom margin at x={x}"

def test_create_srt_captions():
    """Test SRT caption file generation"""
    captions = [
        CaptionEntry("First caption", 0.0, 2.5),
        CaptionEntry("Second caption", 2.5, 5.0)
    ]
    output_path = os.path.join(get_tempdir(), "test_captions.srt")
    result_path = create_srt_captions(captions, output_path)
    assert result_path is not None, "Failed to create SRT file"
    assert os.path.exists(output_path), f"SRT file not created: {output_path}"
    with open(output_path, 'r') as f:
        content = f.read()
        assert "First caption" in content, "First caption not found in SRT"
        assert "Second caption" in content, "Second caption not found in SRT"
        assert "00:00:00,000" in content, "Start time not formatted correctly"
        assert "00:00:02,500" in content, "End time not formatted correctly"

if __name__ == "__main__":
    output_dir = os.path.join(get_tempdir(), "caption_test_outputs")
    os.makedirs(output_dir, exist_ok=True)
    Logger.print_info("Running caption tests and saving outputs...")
    test_caption_text_completeness()
    test_font_size_scaling()
    test_caption_positioning()
    test_create_srt_captions() 