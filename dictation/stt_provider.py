"""
Speech-to-Text (STT) provider abstraction.

This module provides an abstract base class for STT providers, allowing
VAD dictation to work with different STT services (Google, AWS, Azure, etc.).
"""

from abc import ABC, abstractmethod
from typing import Generator, Any, Tuple
from google.cloud import speech_v1p1beta1 as speech


class STTProvider(ABC):
    """Abstract base class for Speech-to-Text providers."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the STT provider (create client, load credentials, etc.)."""
        pass

    @abstractmethod
    def get_streaming_config(self, sample_rate: int = 16000) -> Any:
        """
        Get the streaming configuration for this STT provider.

        Args:
            sample_rate: Audio sample rate in Hz

        Returns:
            Provider-specific streaming configuration object
        """
        pass

    @abstractmethod
    def stream_recognize(self, config: Any, audio_generator: Generator) -> Generator:
        """
        Stream audio to the STT provider and get back transcription results.

        Args:
            config: Provider-specific streaming configuration
            audio_generator: Generator yielding audio chunks

        Returns:
            Generator yielding transcription responses
        """
        pass

    @abstractmethod
    def extract_transcript(self, response: Any) -> Tuple[str, bool]:
        """
        Extract transcript from a provider-specific response.

        Args:
            response: Provider-specific response object

        Returns:
            Tuple of (transcript_text, is_final)
        """
        pass


class GoogleSTTProvider(STTProvider):
    """Google Cloud Speech-to-Text provider implementation."""

    def __init__(self):
        """Initialize Google STT provider."""
        self.client = None

    def initialize(self) -> None:
        """Initialize Google Speech client."""
        self.client = speech.SpeechClient()

    def get_streaming_config(self, sample_rate: int = 16000) -> speech.StreamingRecognitionConfig:
        """
        Get Google Cloud Speech streaming configuration.

        Args:
            sample_rate: Audio sample rate in Hz (default: 16000)

        Returns:
            Google StreamingRecognitionConfig object
        """
        return speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code="en-US",
                enable_automatic_punctuation=True,
                use_enhanced=True,
                model="command_and_search"
            ),
            interim_results=True,
            single_utterance=False
        )

    def stream_recognize(self, config: speech.StreamingRecognitionConfig, 
                        audio_generator: Generator) -> Generator:
        """
        Stream audio to Google Cloud Speech and get transcription results.

        Args:
            config: Google StreamingRecognitionConfig
            audio_generator: Generator yielding audio chunks

        Returns:
            Generator yielding Google speech recognition responses
        """
        if self.client is None:
            raise RuntimeError("STT provider not initialized. Call initialize() first.")

        # Convert raw audio generator to Google-format requests
        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )

        return self.client.streaming_recognize(config, requests)

    def extract_transcript(self, response: Any) -> Tuple[str, bool]:
        """
        Extract transcript from Google Speech response.

        Args:
            response: Google StreamingRecognizeResponse

        Returns:
            Tuple of (transcript_text, is_final)
        """
        if not response.results:
            return ("", False)

        result = response.results[0]
        if not result.alternatives:
            return ("", False)

        transcript = result.alternatives[0].transcript
        is_final = result.is_final

        return (transcript, is_final)

