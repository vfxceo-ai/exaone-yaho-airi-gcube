from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import subprocess
from threading import Lock
from typing import Any

from .config import Settings


@dataclass(frozen=True)
class SynthesizedAudio:
    data: bytes
    media_type: str


class VoiceNotReadyError(RuntimeError):
    pass


class QwenTtsBackend:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = Lock()
        self._custom_model: Any | None = None
        self._clone_model: Any | None = None
        self._clone_prompt: Any | None = None

    @property
    def ready(self) -> bool:
        return self._custom_model is not None

    @property
    def clone_ready(self) -> bool:
        return self._clone_model is not None and self._clone_prompt is not None

    def load(self) -> None:
        with self._lock:
            self._custom_model = self._load_qwen_model(
                self._settings.tts_custom_model_id
            )
            if self._settings.tts_reference_audio.is_file():
                self._refresh_clone_prompt_locked()

    def synthesize(
        self,
        text: str,
        voice: str,
        response_format: str,
        speed: float,
    ) -> SynthesizedAudio:
        normalized_voice = voice.strip().lower()

        with self._lock:
            if self._custom_model is None:
                raise VoiceNotReadyError("TTS model is not ready")

            if normalized_voice == self._settings.tts_default_voice.lower():
                wavs, sample_rate = self._custom_model.generate_custom_voice(
                    text=text,
                    language=self._settings.tts_language,
                    speaker="Sohee",
                )
            elif normalized_voice == self._settings.tts_clone_voice.lower():
                if not self.clone_ready:
                    raise VoiceNotReadyError(
                        "The yaho clone voice needs a reference sample"
                    )
                wavs, sample_rate = self._clone_model.generate_voice_clone(
                    text=text,
                    language=self._settings.tts_language,
                    voice_clone_prompt=self._clone_prompt,
                )
            else:
                raise ValueError("voice must be sohee or yaho")

            return self._encode_audio(
                wavs[0],
                sample_rate,
                response_format,
                speed,
            )

    def install_voice(self, audio: bytes, transcript: str | None) -> None:
        normalized_audio = self._normalize_reference_audio(audio)
        reference_audio = self._settings.tts_reference_audio
        reference_text = self._settings.tts_reference_text
        reference_audio.parent.mkdir(parents=True, exist_ok=True)

        temporary_audio = reference_audio.with_name(
            f".{reference_audio.name}.upload"
        )
        temporary_audio.write_bytes(normalized_audio)
        temporary_audio.replace(reference_audio)

        normalized_transcript = (transcript or "").strip()
        if normalized_transcript:
            temporary_text = reference_text.with_name(
                f".{reference_text.name}.upload"
            )
            temporary_text.write_text(normalized_transcript, encoding="utf-8")
            temporary_text.replace(reference_text)
        else:
            reference_text.unlink(missing_ok=True)

        with self._lock:
            self._refresh_clone_prompt_locked()

    def _load_qwen_model(self, model_id: str) -> Any:
        import torch
        from qwen_tts import Qwen3TTSModel

        dtype_by_name = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }
        try:
            dtype = dtype_by_name[self._settings.tts_dtype.lower()]
        except KeyError as exc:
            raise RuntimeError(
                "TTS_DTYPE must be bfloat16, float16, or float32"
            ) from exc

        torch.set_float32_matmul_precision("high")
        return Qwen3TTSModel.from_pretrained(
            model_id,
            device_map=self._settings.tts_device,
            dtype=dtype,
            attn_implementation=self._settings.tts_attention,
        )

    def _refresh_clone_prompt_locked(self) -> None:
        reference_audio = self._settings.tts_reference_audio
        if not reference_audio.is_file():
            self._clone_prompt = None
            return

        if self._clone_model is None:
            self._clone_model = self._load_qwen_model(
                self._settings.tts_clone_model_id
            )

        transcript = ""
        if self._settings.tts_reference_text.is_file():
            transcript = self._settings.tts_reference_text.read_text(
                encoding="utf-8"
            ).strip()

        self._clone_prompt = self._clone_model.create_voice_clone_prompt(
            ref_audio=str(reference_audio),
            ref_text=transcript or None,
            x_vector_only_mode=not bool(transcript),
        )

    def _normalize_reference_audio(self, audio: bytes) -> bytes:
        if not audio:
            raise ValueError("voice sample is empty")

        command = [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "24000",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            "pipe:1",
        ]
        completed = subprocess.run(
            command,
            input=audio,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0 or not completed.stdout.startswith(b"RIFF"):
            error = completed.stderr.decode("utf-8", errors="replace").strip()
            raise ValueError(f"invalid voice sample: {error or 'ffmpeg failed'}")
        return completed.stdout

    def _encode_audio(
        self,
        waveform: Any,
        sample_rate: int,
        response_format: str,
        speed: float,
    ) -> SynthesizedAudio:
        import librosa
        import numpy as np
        import soundfile as sf

        samples = np.asarray(waveform, dtype=np.float32).squeeze()
        if samples.ndim != 1:
            raise RuntimeError("TTS generated a non-mono waveform")
        if abs(speed - 1.0) > 0.001:
            samples = librosa.effects.time_stretch(samples, rate=speed)

        wav_buffer = BytesIO()
        sf.write(
            wav_buffer,
            samples,
            sample_rate,
            format="WAV",
            subtype="PCM_16",
        )
        wav_data = wav_buffer.getvalue()

        normalized_format = response_format.lower()
        if normalized_format == "wav":
            return SynthesizedAudio(wav_data, "audio/wav")
        if normalized_format != "mp3":
            raise ValueError("response_format must be mp3 or wav")

        completed = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "128k",
                "-f",
                "mp3",
                "pipe:1",
            ],
            input=wav_data,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0 or not completed.stdout:
            error = completed.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"MP3 encoding failed: {error or 'ffmpeg failed'}")
        return SynthesizedAudio(completed.stdout, "audio/mpeg")
