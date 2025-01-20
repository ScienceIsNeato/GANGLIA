"""Module for handling dynamic video captions and SRT subtitle generation."""

from typing import List, Tuple, Optional
import tempfile
from dataclasses import dataclass
from logger import Logger
from .caption_roi import find_roi_in_frame, get_contrasting_color
from .ffmpeg_wrapper import run_ffmpeg_command
import subprocess
from PIL import ImageFont, UnidentifiedImageError
import os

def get_default_font() -> str:
    """Get default font name."""
    # Try common font paths
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
        "C:\\Windows\\Fonts\\arial.ttf"  # Windows
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    return font_paths[0]  # Default to first path if none found

@dataclass
class Word:
    """Represents a single word in a caption with timing and display properties."""
    text: str
    start_time: float
    end_time: float
    line_number: int = 0
    font_size: int = 0
    x_position: int = 0
    width: int = 0
    font_name: str = get_default_font()

    @classmethod
    def from_timed_word(cls, text: str, start_time: float, end_time: float, font_name: str = get_default_font()) -> 'Word':
        """Create a Word instance from pre-timed word (e.g. from Whisper alignment)."""
        return cls(text=text, start_time=start_time, end_time=end_time, font_name=font_name)

    @classmethod
    def from_text(cls, text: str, font_name: str = get_default_font()) -> 'Word':
        """Create a Word instance from text only, timing to be calculated later."""
        return cls(text=text, start_time=0.0, end_time=0.0, font_name=font_name)

    def calculate_width(self, font_size):
        """Calculate exact text width using PIL's ImageFont."""
        try:
            font = ImageFont.truetype(self.font_name, font_size)
        except OSError:
            # Fallback to loading system font by name
            font = ImageFont.load_default()
        self.width = font.getlength(self.text)

@dataclass
class CaptionWindow:
    """Groups words into a display window with shared timing and font size."""
    words: List[Word]
    start_time: float
    end_time: float
    font_size: int

class CaptionEntry:
    """Represents a complete caption with text and timing information."""
    def __init__(self, text: str, start_time: float, end_time: float, timed_words: Optional[List[Tuple[str, float, float]]] = None):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time
        self.timed_words = timed_words

def split_into_words(caption: CaptionEntry, words_per_second: float = 2.0, font_name: str = get_default_font()) -> List[Word]:
    """Split caption text into words with timing.
    
    If caption.timed_words is provided, uses those timings.
    Otherwise, calculates timing based on words_per_second.
    """
    if caption.timed_words:
        # Use pre-calculated word timings (e.g. from Whisper)
        return [Word.from_timed_word(text, start, end, font_name) 
                for text, start, end in caption.timed_words]
    
    # Fall back to calculating timing based on words_per_second
    words = caption.text.split()
    total_duration = caption.end_time - caption.start_time
    total_words = len(words)
    min_duration_needed = total_words / words_per_second
    
    if min_duration_needed > total_duration:
        # If we need more time than available, spread words evenly
        word_duration = total_duration / total_words
    else:
        # Otherwise use the requested words_per_second
        word_duration = 1.0 / words_per_second
    
    result = []
    current_time = caption.start_time
    for i, word in enumerate(words):
        # For the last word, ensure it ends exactly at caption.end_time
        if i == len(words) - 1:
            end_time = caption.end_time
        else:
            end_time = min(current_time + word_duration, caption.end_time)
        result.append(Word(text=word, start_time=current_time, end_time=end_time, font_name=font_name))
        current_time = end_time
    return result

def calculate_word_position(
    word: Word,
    cursor_x: int,
    cursor_y: int,
    line_height: int,
    roi_width: int,
    roi_height: int,
    font_size: int,
    max_font_size: int,
    previous_word: Optional[Word] = None
) -> Tuple[int, int, int, int, bool]:
    """
    Calculate the position for a word based on current cursor and ROI constraints.
    Returns (new_cursor_x, new_cursor_y, word_x, word_y, needs_new_window).
    All pixel values are returned as integers.
    """
    # Get space width for current font
    try:
        font = ImageFont.truetype(word.font_name, font_size)
    except OSError:
        font = ImageFont.load_default()
    space_width = int(font.getlength(" "))
    
    # Calculate word width at current font size
    word.calculate_width(font_size)
    word.font_size = font_size
    word.width = int(word.width)
    
    # Add space width if not at start of line
    total_width = word.width
    if cursor_x > 0:
        total_width += space_width
    
    # Use 80% of ROI width to force wrapping
    effective_width = int(roi_width * 0.8)
    
    # Check if word fits on current line
    if cursor_x + total_width <= effective_width:
        # Word fits - place it at cursor
        word_x = int(cursor_x + (space_width if cursor_x > 0 else 0))
        word_y = int(cursor_y)
        new_cursor_x = int(word_x + word.width)
        new_cursor_y = int(cursor_y)
        return new_cursor_x, new_cursor_y, word_x, word_y, False
        
    # Word doesn't fit - check if we have room for a new line
    if cursor_y + (2 * line_height) <= roi_height:
        # Try increasing previous word's size if it's the last on its line
        if previous_word and previous_word.font_size == font_size:
            test_size = font_size
            prev_x = int(previous_word.x_position)
            while test_size < max_font_size:
                test_size += 1
                previous_word.calculate_width(test_size)
                previous_word.width = int(previous_word.width)
                if prev_x + previous_word.width > effective_width:
                    test_size -= 1
                    previous_word.calculate_width(test_size)
                    previous_word.width = int(previous_word.width)
                    break
            previous_word.font_size = test_size
        
        # Start new line
        word_x = 0
        word_y = int(cursor_y + line_height)
        new_cursor_x = int(word.width)
        new_cursor_y = word_y
        return new_cursor_x, new_cursor_y, word_x, word_y, False
        
    # No room for new line - need new window
    return 0, 0, 0, 0, True

def create_caption_windows(
    words: List[Word],
    min_font_size: int,
    max_font_size: int,
    safe_width: int,
    safe_height: int,
    pause_between_windows: float = 0.5
) -> List[CaptionWindow]:
    """Group words into caption windows with appropriate font sizes and line breaks."""
    windows = []
    current_window_words = []
    current_font_size = max_font_size
    cursor_x = 0
    cursor_y = 0
    line_number = 0
    
    i = 0
    while i < len(words):
        # Try current font size
        while current_font_size >= min_font_size:
            # Reset window state
            current_window_words = []
            cursor_x = 0
            cursor_y = 0
            line_number = 0
            j = i
            
            window_complete = False
            while j < len(words) and not window_complete:
                word = words[j]
                previous_word = current_window_words[-1] if current_window_words else None
                
                new_cursor_x, new_cursor_y, word_x, word_y, needs_new_window = calculate_word_position(
                    word=word,
                    cursor_x=int(cursor_x),
                    cursor_y=int(cursor_y),
                    line_height=int(current_font_size * 1.2),
                    roi_width=int(safe_width),
                    roi_height=int(safe_height),
                    font_size=current_font_size,
                    max_font_size=max_font_size,
                    previous_word=previous_word
                )
                
                if needs_new_window:
                    window_complete = True
                else:
                    # Update word position and line number
                    word.x_position = word_x
                    word.line_number = int(word_y / (current_font_size * 1.2))
                    current_window_words.append(word)
                    cursor_x = new_cursor_x
                    cursor_y = new_cursor_y
                    if cursor_y > line_number * (current_font_size * 1.2):
                        line_number += 1
                    j += 1
            
            if current_window_words:
                # Window fits with current font size
                window = CaptionWindow(
                    words=current_window_words,
                    start_time=current_window_words[0].start_time,
                    end_time=current_window_words[-1].end_time + pause_between_windows,
                    font_size=current_font_size
                )
                windows.append(window)
                i = j
                break
            else:
                # Try smaller font size
                current_font_size = int(current_font_size * 0.9)
        
        # If we couldn't fit any words with minimum font size, force at least one word
        if current_font_size < min_font_size:
            word = words[i]
            word.font_size = min_font_size
            word.calculate_width(min_font_size)
            word.x_position = 0
            word.line_number = 0
            window = CaptionWindow(
                words=[word],
                start_time=word.start_time,
                end_time=word.end_time + pause_between_windows,
                font_size=min_font_size
            )
            windows.append(window)
            i += 1
            current_font_size = max_font_size
    
    return windows

def calculate_word_positions(
    window: CaptionWindow,
    video_height: int,
    margin: int,
    safe_width: int
) -> List[Tuple[float, float]]:
    """
    Calculate the (x, y) positions for each word in a caption window.
    Returns a list of (x, y) coordinates in the same order as window.words.
    """
    positions = []
    line_height = int(window.font_size * 1.2)  # Add some spacing between lines
    total_lines = max(w.line_number for w in window.words) + 1
    window_height = total_lines * line_height
    window_top = video_height - margin - window_height  # Start position of window
    
    # Calculate positions for each word
    for word in window.words:
        # Calculate y position
        y_position = window_top + (word.line_number * line_height)  # Lines flow downward
        
        # Adjust y position for larger font sizes to align baselines
        if word.font_size > window.font_size:
            baseline_offset = (word.font_size - window.font_size)
            y_position -= baseline_offset
        
        # X position is already calculated in try_fit_words and stored in word.x_position
        # Just add the left margin
        x_position = margin + word.x_position
        
        positions.append((x_position, y_position))
    
    return positions

def create_dynamic_captions(
    input_video: str,
    captions: List[CaptionEntry],
    output_path: str,
    min_font_size: int = 32,
    max_font_size: int = 48,
    font_name: str = get_default_font(),
 # Margin from screen edges in pixels
    words_per_second: float = 2.0,
) -> Optional[str]:
    """
    Add Instagram-style dynamic captions to a video using MoviePy.
    """
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.video.VideoClip import TextClip
        from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

        # Load the video
        video = VideoFileClip(input_video)
        
        # Get first frame for ROI detection
        first_frame = video.get_frame(0)
        roi = find_roi_in_frame(first_frame)
        if roi is None:
            Logger.print_error("Failed to find ROI for captions")
            return None
            
        # Extract ROI dimensions and determine text color
        roi_x, roi_y, roi_width, roi_height = roi
        text_color, stroke_color = get_contrasting_color(first_frame, roi)
        Logger.print_info(f"Using {(text_color, stroke_color)} text for optimal contrast in ROI")

        # Process all captions into words
        all_words = []
        for caption in captions:
            words = split_into_words(caption, words_per_second, font_name)
            if words:
                all_words.extend(words)

        if not all_words:
            Logger.print_error("No words to display in captions")
            return None

        # Create caption windows using ROI dimensions
        windows = create_caption_windows(
            words=all_words,
            min_font_size=min_font_size,
            max_font_size=max_font_size,
            safe_width=roi_width,
            safe_height=roi_height
        )

        # Create text clips for each word
        text_clips = []
        for window in windows:
            cursor_x = 0
            cursor_y = 0
            previous_word = None
            
            for word in window.words:
                # Calculate position using cursor-based approach
                new_cursor_x, new_cursor_y, x_position, y_position, _ = calculate_word_position(
                    word=word,
                    cursor_x=int(cursor_x),
                    cursor_y=int(cursor_y),
                    line_height=int(window.font_size * 1.2),
                    roi_width=int(roi_width),
                    roi_height=int(roi_height),
                    font_size=window.font_size,
                    max_font_size=max_font_size,
                    previous_word=previous_word
                )
                
                # Create text clip with contrasting color
                txt_clip = TextClip(
                    text=word.text,
                    font=word.font_name,
                    method='caption',
                    color=text_color,
                    stroke_color=stroke_color,
                    stroke_width=1,
                    font_size=word.font_size,
                    size=(word.width, int(word.font_size * 1.5)), # allow enough room for vertical alignment
                    margin=(0,0,0,int(word.font_size * 1.5),), # prevents bottom of text from being cut off
                    text_align='left',
                    duration=window.end_time - word.start_time  # Word persists until end of window
                )

                # Set position and start time - ensure integer positions and adjust y for baseline
                baseline_offset = int((word.font_size - window.font_size) * 0.2)  # Adjust baseline for larger fonts
                txt_clip = txt_clip.with_position((int(roi_x + x_position), int(roi_y + y_position - baseline_offset)))
                txt_clip = txt_clip.with_start(word.start_time)
                
                text_clips.append(txt_clip)
                
                # Update cursor and previous word for next iteration
                cursor_x = new_cursor_x
                cursor_y = new_cursor_y
                previous_word = word

        # Combine video with text overlays
        final_video = CompositeVideoClip([video] + text_clips)

        # Write output
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            # Performance optimizations:
            preset='ultrafast',  # Faster encoding, slightly larger file size
            threads=4  # Use multiple CPU cores
        )

        # Clean up
        video.close()
        final_video.close()
        for clip in text_clips:
            clip.close()

        return output_path

    except Exception as e:
        Logger.print_error(f"Error adding dynamic captions: {str(e)}")
        import traceback
        Logger.print_error(f"Traceback: {traceback.format_exc()}")
        return None

def create_srt_captions(
    captions: List[CaptionEntry],
    output_path: Optional[str] = None
) -> Optional[str]:
    """Create an SRT subtitle file from caption entries."""
    try:
        if output_path is None:
            with tempfile.NamedTemporaryFile(suffix='.srt', mode='w', delete=False) as srt_file:
                output_path = srt_file.name
        def format_time(seconds: float) -> str:
            """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace('.', ',')
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, caption in enumerate(captions, 1):
                f.write(f"{i}\n")
                f.write(f"{format_time(caption.start_time)} --> {format_time(caption.end_time)}\n")
                f.write(f"{caption.text}\n\n")
        return output_path
    except (OSError, IOError) as e:
        Logger.print_error(f"Error creating SRT file: {e}")
        return None 

def create_static_captions(
    input_video: str,
    captions: List[CaptionEntry],
    output_path: str,
    font_size: int = 40,
    font_name: str = get_default_font(),
    box_color: str = "black@0.5",  # Semi-transparent background
    position: str = "bottom",
    margin: int = 40
) -> Optional[str]:
    """
    Add simple static captions to a video.
    
    Args:
        input_video: Path to input video file
        captions: List of CaptionEntry objects
        output_path: Path where the output video will be saved
        font_size: Font size for captions
        font_name: Name of the font to use
        box_color: Color and opacity of the background box
        position: Vertical position of captions ('bottom' or 'center')
        margin: Margin from screen edges in pixels
    """
    try:
        # Get video dimensions
        ffprobe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            input_video
        ]
        dimensions = run_ffmpeg_command(ffprobe_cmd)
        if not dimensions:
            raise ValueError("Could not determine video dimensions")
        
        width, height = map(int, dimensions.stdout.decode('utf-8').strip().split(','))
        
        # Build drawtext filters for each caption
        drawtext_filters = []
        for caption in captions:
            # Calculate y position
            if position == "bottom":
                y_position = f"h-{margin}-th"  # Position from bottom with margin
            else:
                y_position = f"(h-th)/2"  # Center vertically
                
            # Escape special characters in text
            escaped_text = caption.text.replace("'", "\\'")
            
            filter_text = (
                f"drawtext=text='{escaped_text}'"
                f":font={font_name}"
                f":fontsize={font_size}"
                f":fontcolor=white"
                f":x=(w-text_w)/2"  # Center horizontally
                f":y={y_position}"
                f":enable=between(t\\,{caption.start_time}\\,{caption.end_time})"
                f":box=1"
                f":boxcolor={box_color}"
            )
            drawtext_filters.append(filter_text)
            
        # Combine all filters
        complete_filter = ",".join(drawtext_filters)
        
        # Run FFmpeg command
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-vf", complete_filter,
            "-c:a", "copy",
            output_path
        ]
        
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result:
            Logger.print_info(f"Successfully added static captions to video: {output_path}")
            return output_path
        else:
            Logger.print_error("Failed to add static captions to video")
            return None
            
    except (ValueError, OSError, subprocess.CalledProcessError) as e:
        Logger.print_error(f"Error adding static captions: {e}")
        return None 

    # TODO: Fix bug where long static captions overflow the screen width.
    #       Need to implement text wrapping for static captions similar to dynamic captions
    #       to ensure text stays within safe viewing area. 