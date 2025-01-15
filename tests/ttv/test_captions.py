import os
import tempfile
from utils import get_tempdir
from PIL import Image, ImageFont
from tts import GoogleTTS
from ttv.audio_alignment import create_word_level_captions
from ttv.video_generation import run_ffmpeg_command
from ttv.captions import (
    CaptionEntry, create_dynamic_captions, create_srt_captions,
    create_static_captions, Word, create_caption_windows,
    split_into_words, calculate_word_positions
)
from logger import Logger

def get_default_font():
    """Get the default font path for testing."""
    # Try common system font locations
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "C:\\Windows\\Fonts\\arial.ttf"  # Windows
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    return None

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

def test_static_captions():
    """Test static caption generation"""
    # Create test video
    input_video_path = create_test_video(duration=1)
    assert input_video_path is not None, "Failed to create test video"
    
    # Create test captions
    captions = [
        CaptionEntry("Hello World", 0.0, 0.5),
        CaptionEntry("Testing Captions", 0.5, 1.0)
    ]
    
    # Create output path
    output_path = os.path.join(get_tempdir(), "output_static_test.mp4")
    
    # Test the function
    result = create_static_captions(
        input_video=input_video_path,
        captions=captions,
        output_path=output_path
    )
    
    # Clean up
    os.unlink(input_video_path)
    
    # Verify results
    assert result is not None, "Failed to create video with static captions"
    assert os.path.exists(output_path), f"Output file not created: {output_path}"
    assert os.path.getsize(output_path) > 0, "Output file is empty"

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
                
                # Only check the bottom portion where captions should be
                caption_area_start = int(frame_height * 0.7)  # Check bottom 30% where captions should be
                
                # Get background color from top-left corner
                background_color = rgb_img.getpixel((0, 0))
                
                def colors_match(c1, c2, tolerance=15):  # Increased tolerance for compression artifacts
                    """Check if colors match within a tolerance level"""
                    return all(abs(a - b) <= tolerance for a, b in zip(c1, c2))
                
                # Scan the margins to ensure no text pixels
                for y in range(caption_area_start, frame_height):
                    # Check left margin (check one pixel inside the margin)
                    color = rgb_img.getpixel((margin-1, y))
                    # Check if pixel differs significantly from background
                    assert colors_match(color, background_color), f"Found text in left margin at y={y}"
                    
                    # Check right margin (check one pixel inside the margin)
                    color = rgb_img.getpixel((frame_width-margin+1, y))
                    assert colors_match(color, background_color), f"Found text in right margin at y={y}"
                
                # Check bottom margin (check one pixel inside the margin)
                for x in range(frame_width):
                    color = rgb_img.getpixel((x, frame_height-margin+1))
                    assert colors_match(color, background_color), f"Found text in bottom margin at x={x}"

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

def test_audio_aligned_captions():
    """Test creation of a video with audio-aligned captions"""
    # Create test video
    video_size = (1920, 1080)
    duration = 5
    input_video_path = create_test_video(size=video_size, duration=duration)
    assert input_video_path is not None, "Failed to create test video"

    # Generate test audio with TTS
    tts = GoogleTTS()
    test_text = "This is a test video with synchronized audio and captions. The captions should match the spoken words exactly."
    success, audio_path = tts.convert_text_to_speech(test_text)
    assert success and audio_path is not None, "Failed to generate test audio"

    try:
        # Verify the audio file exists and has content
        assert os.path.exists(audio_path), "Audio file not created"
        assert os.path.getsize(audio_path) > 0, "Audio file is empty"

        # Get word-level captions from audio
        captions = create_word_level_captions(audio_path, test_text)
        assert len(captions) > 0, "No captions generated from audio"

        # Create output path for the final video
        output_path = os.path.join(get_tempdir(), "output_with_audio_captions.mp4")

        # Add dynamic captions
        result_path = create_dynamic_captions(
            input_video=input_video_path,
            captions=captions,
            output_path=output_path,
            min_font_size=32,
            max_font_size=48,
            margin=40,
            max_window_height_ratio=0.3
        )
        assert result_path is not None, "Failed to create video with captions"

        # Add audio to the video with improved FFmpeg command
        final_output = os.path.join(get_tempdir(), "final_output_with_audio.mp4")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", output_path,     # Video with captions
            "-i", audio_path,      # Audio file
            "-map", "0:v:0",       # Map video from first input
            "-map", "1:a:0",       # Map audio from second input
            "-c:v", "copy",        # Copy video stream without re-encoding
            "-c:a", "aac",         # Encode audio as AAC
            "-b:a", "192k",        # Set audio bitrate
            "-shortest",           # Match duration to shortest stream
            final_output
        ]
        result = run_ffmpeg_command(ffmpeg_cmd)
        assert result is not None, "Failed to add audio to video"
        assert os.path.exists(final_output), "Final output file not created"
        assert os.path.getsize(final_output) > 0, "Final output file is empty"

        # Verify audio stream exists in output
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "default=noprint_wrappers=1:nokey=1",
            final_output
        ]
        probe_result = run_ffmpeg_command(probe_cmd)
        assert probe_result is not None and probe_result.stdout, "No audio stream found in output video"

        # Play the video if requested (disabled by default in automated tests)
        if os.environ.get("PLAY_TEST_OUTPUT"):
            play_cmd = ["ffplay", "-autoexit", final_output]
            run_ffmpeg_command(play_cmd)

    finally:
        # Cleanup
        if os.path.exists(input_video_path):
            os.remove(input_video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)

def test_text_wrapping_direction():
    """Test that when text wraps to a new line, it goes downward rather than upward"""
    # Set up dimensions
    video_width = 1920
    margin = 40
    roi_width = video_width - (2 * margin)
    font_size = 32  # Use minimum font size to be conservative
    
    # Create text that will definitely wrap by measuring actual widths
    font = ImageFont.load_default()
    
    # Generate text until we have 3x the ROI width in pixels
    words = []
    total_width = 0
    space_width = font.getlength(" ")
    test_word = "testing"  # Use a consistent word to build up width
    word_width = font.getlength(test_word)
    
    while total_width < roi_width * 3:
        words.append(test_word)
        total_width += word_width + space_width
    
    # Create caption with the generated text
    text = " ".join(words)
    captions = [CaptionEntry(text, 0.0, 2.0)]
    
    # Process caption into words
    words = split_into_words(captions[0])
    
    # Create caption windows
    video_height = 1080  # Standard HD height
    safe_height = int(video_height * 0.3)  # 30% of video height
    
    windows = create_caption_windows(
        words=words,
        min_font_size=32,
        max_font_size=48,
        safe_width=roi_width,
        safe_height=safe_height
    )
    
    assert len(windows) > 0, "No caption windows created"
    window = windows[0]  # We only created one caption
    
    # Get positions for all words
    positions = calculate_word_positions(window, video_height, margin, roi_width)
    
    # Group positions by line number
    line_positions = {}
    for word, (_, y_pos) in zip(window.words, positions):
        if word.line_number not in line_positions:
            line_positions[word.line_number] = []
        line_positions[word.line_number].append(y_pos)
    
    # Verify that each line's y-position is below the previous line
    line_numbers = sorted(line_positions.keys())
    assert len(line_numbers) > 1, "Text did not wrap into multiple lines"
    for i in range(1, len(line_numbers)):
        prev_line = line_numbers[i-1]
        curr_line = line_numbers[i]
        assert min(line_positions[curr_line]) > max(line_positions[prev_line]), \
            f"Line {curr_line} is not below line {prev_line}"

if __name__ == "__main__":
    output_dir = os.path.join(get_tempdir(), "caption_test_outputs")
    os.makedirs(output_dir, exist_ok=True)
    Logger.print_info("Running caption tests and saving outputs...")
    test_static_captions()
    test_caption_text_completeness()
    test_font_size_scaling()
    test_caption_positioning()
    test_create_srt_captions()
    test_audio_aligned_captions()
    test_text_wrapping_direction()
