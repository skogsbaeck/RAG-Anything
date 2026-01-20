"""
Audio processing module for speech-to-text transcription.

This module provides audio transcription capabilities using OpenAI Whisper.
Designed for therapist voice notes (post-session recordings).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Configuration for audio processing."""

    whisper_model: str = "base"  # tiny, base, small, medium, large
    device: str = "cpu"  # or "cuda" if GPU available
    language: str = "de"  # German language
    compute_type: str = "int8"  # faster_whisper compute type


@dataclass
class AudioMetadata:
    """Audio file metadata."""

    duration_seconds: float
    sample_rate: int
    channels: int
    format: str
    file_size_bytes: int


@dataclass
class AudioTranscription:
    """Transcription result from audio processing."""

    text: str
    duration_seconds: float
    language: str
    word_count: int
    confidence: Optional[float] = None

    def __post_init__(self):
        """Calculate word count if not provided."""
        if self.word_count == 0:
            self.word_count = len(self.text.split())


class AudioProcessor:
    """
    Audio transcription processor using OpenAI Whisper.

    Optimized for German language therapy session notes (5-15 minutes).
    Uses faster-whisper for improved performance.
    """

    def __init__(self, config: Optional[AudioConfig] = None):
        """
        Initialize audio processor.

        Args:
            config: Audio processing configuration (uses defaults if None)
        """
        self.config = config or AudioConfig()
        self.model = None

        logger.info(f"AudioProcessor initialized with model: {self.config.whisper_model}")

    def _load_model(self):
        """Lazy load Whisper model on first use."""
        if self.model is not None:
            return

        try:
            from faster_whisper import WhisperModel

            logger.info(f"Loading Whisper model: {self.config.whisper_model}")
            start_time = time.time()

            self.model = WhisperModel(
                self.config.whisper_model,
                device=self.config.device,
                compute_type=self.config.compute_type
            )

            load_time = time.time() - start_time
            logger.info(f"Model loaded in {load_time:.2f}s")

        except ImportError:
            logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
            raise
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def extract_metadata(self, audio_path: Path) -> AudioMetadata:
        """
        Extract metadata from audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            AudioMetadata object with file information
        """
        try:
            import librosa
            import soundfile as sf

            # Get duration and sample rate
            duration = librosa.get_duration(path=str(audio_path))

            # Get detailed info
            info = sf.info(str(audio_path))

            return AudioMetadata(
                duration_seconds=duration,
                sample_rate=info.samplerate,
                channels=info.channels,
                format=info.format,
                file_size_bytes=audio_path.stat().st_size
            )

        except ImportError:
            logger.error("librosa or soundfile not installed. Install with: pip install librosa soundfile")
            raise
        except Exception as e:
            logger.error(f"Failed to extract audio metadata: {e}")
            raise

    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> AudioTranscription:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (.mp3, .wav, .m4a, .ogg)
            language: Language code (uses config default if None)

        Returns:
            AudioTranscription object with transcribed text

        Raises:
            FileNotFoundError: If audio file doesn't exist
            Exception: If transcription fails
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Load model if not already loaded
        self._load_model()

        # Use provided language or config default
        lang = language or self.config.language

        logger.info(f"Transcribing: {audio_path.name} (language: {lang})")
        start_time = time.time()

        try:
            # Get audio metadata
            metadata = self.extract_metadata(audio_path)

            # Transcribe with Whisper
            segments, info = self.model.transcribe(
                str(audio_path),
                language=lang,
                beam_size=5,
                vad_filter=True,  # Voice activity detection
                vad_parameters=dict(
                    min_silence_duration_ms=500  # Skip long pauses
                )
            )

            # Combine all segments into full text
            full_text = " ".join([segment.text.strip() for segment in segments])

            transcription_time = time.time() - start_time
            logger.info(f"Transcription completed in {transcription_time:.2f}s")
            logger.info(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")

            return AudioTranscription(
                text=full_text,
                duration_seconds=metadata.duration_seconds,
                language=info.language,
                word_count=0,  # Will be calculated in __post_init__
                confidence=info.language_probability
            )

        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            raise

    def transcribe_batch(self, audio_paths: list[Path], language: Optional[str] = None) -> Dict[str, AudioTranscription]:
        """
        Transcribe multiple audio files.

        Args:
            audio_paths: List of audio file paths
            language: Language code (uses config default if None)

        Returns:
            Dictionary mapping file path to transcription result
        """
        results = {}

        for audio_path in audio_paths:
            try:
                results[str(audio_path)] = self.transcribe(audio_path, language)
            except Exception as e:
                logger.error(f"Failed to transcribe {audio_path}: {e}")
                results[str(audio_path)] = None

        return results

    def export_to_text(self, transcription: AudioTranscription, output_path: Path) -> Path:
        """
        Export transcription to text file.

        Args:
            transcription: AudioTranscription object
            output_path: Path where text file will be saved

        Returns:
            Path to created text file
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open('w', encoding='utf-8') as f:
                # Write header
                f.write(f"# Transkription\n\n")
                f.write(f"Dauer: {transcription.duration_seconds:.1f}s\n")
                f.write(f"Sprache: {transcription.language}\n")
                f.write(f"Wörter: {transcription.word_count}\n\n")
                f.write("---\n\n")

                # Write transcribed text
                f.write(transcription.text)

            logger.info(f"Transcription exported to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to export transcription: {e}")
            raise


# Utility functions

def get_supported_formats() -> list[str]:
    """
    Get list of supported audio formats.

    Returns:
        List of file extensions (e.g., ['.mp3', '.wav', '.m4a'])
    """
    return ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac']


def is_supported_format(file_path: Path) -> bool:
    """
    Check if audio file format is supported.

    Args:
        file_path: Path to audio file

    Returns:
        True if format is supported, False otherwise
    """
    return file_path.suffix.lower() in get_supported_formats()


def estimate_processing_time(duration_seconds: float, model: str = "base", device: str = "cpu") -> float:
    """
    Estimate transcription processing time.

    Args:
        duration_seconds: Audio duration in seconds
        model: Whisper model size
        device: Processing device ('cpu' or 'cuda')

    Returns:
        Estimated processing time in seconds
    """
    # Empirical ratios (approximate)
    speed_ratios = {
        'cpu': {
            'tiny': 2.0,   # 2x realtime
            'base': 2.0,   # 2x realtime
            'small': 1.0,  # 1x realtime
            'medium': 0.5, # 0.5x realtime (slower than realtime)
        },
        'cuda': {
            'tiny': 10.0,   # 10x realtime
            'base': 8.0,    # 8x realtime
            'small': 5.0,   # 5x realtime
            'medium': 3.0,  # 3x realtime
        }
    }

    ratio = speed_ratios.get(device, {}).get(model, 1.0)
    return duration_seconds / ratio
