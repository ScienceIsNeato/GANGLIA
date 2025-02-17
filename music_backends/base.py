from abc import ABC, abstractmethod
import time

class MusicBackend(ABC):
    """Base class for music generation backends."""

    @abstractmethod
    def generate_instrumental(self, prompt: str, **kwargs) -> str:
        """Generate instrumental music from a text prompt.

        Args:
            prompt (str): Text description of the desired music.
            **kwargs: Additional backend-specific parameters.

        Returns:
            str: Path to the generated audio file.
        """
        pass

    @abstractmethod
    def generate_with_lyrics(self, prompt: str, story_text: str, **kwargs) -> str:
        """Generate music with lyrics from a text prompt and story.

        Args:
            prompt (str): Text description of the desired music style.
            story_text (str): Story text to generate lyrics from.
            **kwargs: Additional backend-specific parameters.

        Returns:
            str: Path to the generated audio file.
        """
        pass

    @abstractmethod
    def start_generation(self, prompt: str, with_lyrics: bool = False, title: str = None, tags: str = None, **kwargs) -> str:
        """Start the generation process and return a job ID or identifier.

        Args:
            prompt (str): Text description of the desired music.
            with_lyrics (bool): Whether to generate with lyrics.
            title (str, optional): Title for the generated song.
            tags (str, optional): Style tags/descriptors for the song.
            **kwargs: Additional backend-specific parameters including story_text for lyrics.

        Returns:
            str: Job ID or identifier for tracking progress.
        """
        pass

    @abstractmethod
    def check_progress(self, job_id: str) -> tuple[str, float]:
        """Check the progress of a generation job.

        Args:
            job_id (str): Job ID or identifier from start_generation.

        Returns:
            tuple[str, float]: Status message and progress percentage (0-100).
        """
        pass

    @abstractmethod
    def get_result(self, job_id: str) -> str:
        """Get the result of a completed generation job.

        Args:
            job_id (str): Job ID or identifier from start_generation.

        Returns:
            str: Path to the generated audio file.
        """
        pass

    def wait_for_completion(self, job_id: str, timeout: int = 300, interval: int = 5) -> str:
        """Wait for a generation job to complete.

        Args:
            job_id: Job ID from start_generation
            timeout: Maximum time to wait in seconds
            interval: Time between status checks in seconds

        Returns:
            Path to the generated audio file, or None if generation failed/timed out
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            status, progress = self.check_progress(job_id)
            print(f"\nStatus: {status}")
            print(f"Progress: {progress:.1f}%")

            if status == 'complete':
                return self.get_result(job_id)

            time.sleep(interval)

        return None
