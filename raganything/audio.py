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
        if not self.word_count:
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
        if self.model is not None:
            return

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
            raise

        logger.info(f"Loading Whisper model: {self.config.whisper_model}")
        start_time = time.time()

        self.model = WhisperModel(
            self.config.whisper_model,
            device=self.config.device,
            compute_type=self.config.compute_type
        )

        logger.info(f"Model loaded in {time.time() - start_time:.2f}s")

    def extract_metadata(self, audio_path: Path) -> AudioMetadata:
        try:
            import librosa
            import soundfile as sf
        except ImportError:
            logger.error("librosa or soundfile not installed. Install with: pip install librosa soundfile")
            raise

        duration = librosa.get_duration(path=str(audio_path))
        info = sf.info(str(audio_path))

        return AudioMetadata(
            duration_seconds=duration,
            sample_rate=info.samplerate,
            channels=info.channels,
            format=info.format,
            file_size_bytes=audio_path.stat().st_size
        )

    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> AudioTranscription:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._load_model()
        lang = language or self.config.language

        logger.info(f"Transcribing: {audio_path.name} (language: {lang})")
        start_time = time.time()

        metadata = self.extract_metadata(audio_path)

        segments, info = self.model.transcribe(
            str(audio_path),
            language=lang,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        full_text = " ".join([segment.text.strip() for segment in segments])

        logger.info(f"Transcription completed in {time.time() - start_time:.2f}s")
        logger.info(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")

        return AudioTranscription(
            text=full_text,
            duration_seconds=metadata.duration_seconds,
            language=info.language,
            word_count=0,
            confidence=info.language_probability
        )

    def transcribe_batch(self, audio_paths: list[Path], language: Optional[str] = None) -> Dict[str, AudioTranscription]:
        results = {}
        for audio_path in audio_paths:
            try:
                results[str(audio_path)] = self.transcribe(audio_path, language)
            except Exception as e:
                logger.error(f"Failed to transcribe {audio_path}: {e}")
                results[str(audio_path)] = None
        return results

    def export_to_text(self, transcription: AudioTranscription, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open('w', encoding='utf-8') as f:
            f.write(f"# Transkription\n\n")
            f.write(f"Dauer: {transcription.duration_seconds:.1f}s\n")
            f.write(f"Sprache: {transcription.language}\n")
            f.write(f"Wörter: {transcription.word_count}\n\n")
            f.write("---\n\n")
            f.write(transcription.text)

        logger.info(f"Transcription exported to: {output_path}")
        return output_path


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
    speed_ratios = {
        'cpu': {'tiny': 2.0, 'base': 2.0, 'small': 1.0, 'medium': 0.5},
        'cuda': {'tiny': 10.0, 'base': 8.0, 'small': 5.0, 'medium': 3.0}
    }
    ratio = speed_ratios.get(device, {}).get(model, 1.0)
    return duration_seconds / ratio
