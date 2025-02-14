"""Suno API implementation using gcui-art/suno-api."""

import os
import time
from datetime import datetime
import requests
from logger import Logger
from music_backends.base import MusicBackend
from music_backends.suno_interface import SunoInterface
from utils import get_tempdir

class GcuiSunoBackend(MusicBackend, SunoInterface):
    """gcui-art/suno-api implementation for music generation."""
    
    def __init__(self):
        """Initialize the backend with configuration."""
        self.api_base_url = os.getenv('SUNO_API_URL', None)
        self.audio_directory = get_tempdir() + "/music"
        os.makedirs(self.audio_directory, exist_ok=True)
        
        # Test connection and get quota info only if URL is configured
        if self.api_base_url:
            try:
                response = requests.get(f"{self.api_base_url}/api/get_limit", timeout=10)
                if response.status_code != 200:
                    raise ConnectionError(f"Failed to connect to Suno API: {response.status_code}")
                quota_info = response.json()
                Logger.print_info(f"Connected to Suno API. Credits remaining: {quota_info.get('credits_left', 'unknown')}")
            except Exception as e:
                Logger.print_error(f"Failed to initialize Suno API connection: {str(e)}")
                # Don't raise here - let start_generation handle errors
    
    def start_generation(self, prompt: str, with_lyrics: bool = False, title: str = None, tags: str = None, **kwargs) -> str:
        """Start the generation process via API.
        
        Args:
            prompt: Text description of the desired music
            with_lyrics: Whether to generate with lyrics
            title: Title for the generated song (optional)
            tags: Style tags/descriptors for the song (optional)
            **kwargs: Additional parameters including story_text for lyrics
            
        Returns:
            str: Job ID for tracking progress, or None if generation fails
        """
        if not self.api_base_url:
            Logger.print_error("SUNO_API_URL environment variable is not set")
            return None
            
        try:
            if with_lyrics and 'story_text' in kwargs:
                # First generate lyrics if needed
                lyrics_response = requests.post(
                    f"{self.api_base_url}/api/generate_lyrics",
                    json={"prompt": kwargs['story_text']},
                    timeout=30
                )
                if lyrics_response.status_code != 200:
                    Logger.print_error(f"Failed to generate lyrics: {lyrics_response.text}")
                    return None
                lyrics_data = lyrics_response.json()
                
                # Use custom_generate for more control over lyrics and style
                data = {
                    "prompt": prompt,  # Use the music style prompt
                    "lyrics": lyrics_data.get('text', ''),  # Get generated lyrics
                    "tags": tags or kwargs.get('tags', 'folk acoustic'),  # Use provided tags or default
                    "title": title or kwargs.get('title', 'Generated Song'),  # Use provided title or default
                    "make_instrumental": False,
                    "wait_audio": kwargs.get('wait_audio', False)
                }
                endpoint = f"{self.api_base_url}/api/custom_generate"
            else:
                # Use standard generate for instrumental
                data = {
                    "prompt": prompt,
                    "tags": tags or kwargs.get('tags', 'instrumental'),  # Use provided tags or default
                    "title": title or kwargs.get('title', 'Generated Instrumental'),  # Use provided title or default
                    "make_instrumental": True,
                    "wait_audio": kwargs.get('wait_audio', False)
                }
                endpoint = f"{self.api_base_url}/api/generate"
            
            Logger.print_info(f"Request data: {data}")
            Logger.print_info(f"Endpoint: {endpoint}")
            
            response = requests.post(endpoint, json=data, timeout=30)
            Logger.print_info(f"Response status: {response.status_code}")
            Logger.print_info(f"Response text: {response.text}")
            
            if response.status_code != 200:
                Logger.print_error(f"Failed to start generation: {response.text}")
                return None
            
            response_data = response.json()
            if isinstance(response_data, list) and len(response_data) > 0:
                # Store all job IDs for tracking
                job_ids = []
                for song in response_data:
                    job_id = song.get('id')
                    if job_id:
                        self._save_start_time(job_id)
                        job_ids.append(job_id)
                
                if job_ids:
                    # Return the first job ID - we'll track both using the same ID prefix
                    return job_ids[0]
            
            Logger.print_error(f"Invalid response format: {response_data}")
            return None
            
        except Exception as e:
            Logger.print_error(f"Failed to start generation: {str(e)}")
            return None
    
    def check_progress(self, job_id: str) -> tuple[str, float]:
        """Check the progress of a generation job via API."""
        try:
            response = requests.get(f"{self.api_base_url}/api/get?ids={job_id}", timeout=10)
            if response.status_code != 200:
                return f"Error: HTTP {response.status_code}", 0
            
            response_data = response.json()
            if not isinstance(response_data, list) or not response_data:
                return "Error: Invalid response format", 0
            
            song_data = response_data[0]
            status = song_data.get('status', '')
            
            # Return 100% for completed songs
            if status == 'complete':
                return status, 100.0

            if status == 'error':
                return f"Error: {song_data.get('error', 'Unknown error')}", 0.0
            
            # For in-progress songs, estimate based on time
            # Typical generation takes about 2 minutes
            TYPICAL_DURATION = 120  # seconds
            
            start_time = self._get_start_time(job_id)
            elapsed_time = time.time() - start_time
            
            # Calculate progress as a percentage of typical duration
            # Cap at 95% to avoid showing 100% before actually complete
            progress = min(95.0, (elapsed_time / TYPICAL_DURATION) * 100)
            
            return status, progress
                
        except Exception as e:
            return f"Error: {str(e)}", 0.0
    
    def get_result(self, job_id: str) -> str:
        """Get the result of a completed generation job."""
        try:
            response = requests.get(f"{self.api_base_url}/api/get?ids={job_id}", timeout=10)
            Logger.print_info(f"Get result response status: {response.status_code}")
            Logger.print_info(f"Get result response text: {response.text}")
            
            if response.status_code != 200:
                return None
            
            response_data = response.json()
            if not isinstance(response_data, list) or not response_data:
                return None
            
            song_data = response_data[0]
            if song_data.get('status') != 'complete':
                return None
            
            audio_url = song_data.get('audio_url')
            Logger.print_info(f"Audio URL: {audio_url}")
            if not audio_url:
                return None
            
            return self._download_audio(audio_url, job_id)
            
        except Exception as e:
            Logger.print_error(f"Failed to get result: {str(e)}")
            return None
    
    def _download_audio(self, audio_url: str, job_id: str) -> str:
        """Download the generated audio file."""
        try:
            Logger.print_info(f"Downloading audio from: {audio_url}")
            response = requests.get(audio_url, stream=True, timeout=30)
            Logger.print_info(f"Download response status: {response.status_code}")
            
            if response.status_code != 200:
                Logger.print_error(f"Failed to download audio: {response.text}")
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audio_path = os.path.join(self.audio_directory, f"suno_{job_id}_{timestamp}.mp3")
            
            with open(audio_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            Logger.print_info(f"Successfully downloaded audio to: {audio_path}")
            return audio_path
            
        except Exception as e:
            Logger.print_error(f"Failed to download audio: {str(e)}")
            return None
    
    def _save_start_time(self, job_id: str):
        """Save the start time of a job for progress estimation."""
        path = os.path.join(self.audio_directory, f"{job_id}_start_time")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(str(time.time()))
    
    def _get_start_time(self, job_id: str) -> float:
        """Get the start time of a job for progress estimation."""
        try:
            path = os.path.join(self.audio_directory, f"{job_id}_start_time")
            with open(path, 'r', encoding='utf-8') as f:
                return float(f.read().strip())
        except (IOError, ValueError) as e:
            Logger.print_error(f"Failed to get start time for job {job_id}: {e}")
            return time.time()
    
    def generate_instrumental(self, prompt: str, **kwargs) -> str:
        """Generate instrumental music (blocking)."""
        job_id = self.start_generation(prompt, with_lyrics=False, **kwargs)
        if not job_id:
            return None
            
        while True:
            _, progress = self.check_progress(job_id)
            if progress >= 100:
                return self.get_result(job_id)
            time.sleep(5)
    
    def generate_with_lyrics(self, prompt: str, story_text: str, **kwargs) -> str:
        """Generate music with lyrics (blocking)."""
        kwargs['story_text'] = story_text
        job_id = self.start_generation(prompt, with_lyrics=True, **kwargs)
        if not job_id:
            return None
            
        while True:
            _, progress = self.check_progress(job_id)
            if progress >= 100:
                return self.get_result(job_id)
            time.sleep(5)
