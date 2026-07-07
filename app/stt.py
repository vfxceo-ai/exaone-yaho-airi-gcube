from pathlib import Path
from threading import Lock
from typing import Any

from .config import Settings


class FasterWhisperBackend:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = Lock()
        self._model: Any | None = None

    @property
    def ready(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            self._settings.stt_model_id,
            device="cuda",
            compute_type=self._settings.stt_compute_type,
        )

    def transcribe(self, path: Path, language: str) -> str:
        if self._model is None:
            raise RuntimeError("STT model is not ready")

        with self._lock:
            segments, _ = self._model.transcribe(
                str(path),
                language=language,
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            return "".join(segment.text for segment in segments).strip()
