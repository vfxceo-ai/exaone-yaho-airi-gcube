from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
import time
import unittest

from app.config import Settings


def settings(directory: str) -> Settings:
    voice_dir = Path(directory)
    return Settings(
        api_key="x" * 32,
        stt_model_id="/models/stt",
        stt_compute_type="int8_float16",
        stt_language="ko",
        log_level="INFO",
        llm_health_url="http://127.0.0.1:8000/health",
        tts_reference_audio=voice_dir / "reference.wav",
        tts_reference_text=voice_dir / "reference.txt",
    )


class ProbeCustomModel:
    def __init__(self) -> None:
        self.guard = Lock()
        self.active = 0
        self.peak = 0

    def generate_custom_voice(self, **_kwargs):
        with self.guard:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(0.05)
        with self.guard:
            self.active -= 1
        return [[0.0, 0.1, 0.0]], 24000


class ProbeCloneModel:
    def __init__(self) -> None:
        self.prompt_calls: list[dict[str, object]] = []

    def create_voice_clone_prompt(self, **kwargs):
        self.prompt_calls.append(kwargs)
        return ["cached-prompt"]


class QwenTtsBackendContractTests(unittest.TestCase):
    def test_backend_starts_not_ready(self) -> None:
        from app.tts import QwenTtsBackend

        with TemporaryDirectory() as directory:
            service = QwenTtsBackend(settings(directory))

        self.assertFalse(service.ready)
        self.assertFalse(service.clone_ready)

    def test_custom_voice_generation_is_serialized(self) -> None:
        from app.tts import QwenTtsBackend, SynthesizedAudio

        with TemporaryDirectory() as directory:
            service = QwenTtsBackend(settings(directory))
            probe = ProbeCustomModel()
            service._custom_model = probe
            service._encode_audio = lambda *_args, **_kwargs: SynthesizedAudio(
                b"ID3",
                "audio/mpeg",
            )

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(service.synthesize, "안녕", "sohee", "mp3", 1.0)
                    for _ in range(2)
                ]
                self.assertEqual([future.result().data for future in futures], [b"ID3", b"ID3"])

        self.assertEqual(probe.peak, 1)

    def test_yaho_voice_requires_a_reference_sample(self) -> None:
        from app.tts import QwenTtsBackend, VoiceNotReadyError

        with TemporaryDirectory() as directory:
            service = QwenTtsBackend(settings(directory))
            service._custom_model = ProbeCustomModel()

            with self.assertRaises(VoiceNotReadyError):
                service.synthesize("안녕", "yaho", "mp3", 1.0)

    def test_install_voice_caches_transcript_aware_clone_prompt(self) -> None:
        from app.tts import QwenTtsBackend

        with TemporaryDirectory() as directory:
            service = QwenTtsBackend(settings(directory))
            probe = ProbeCloneModel()
            service._clone_model = probe
            service._normalize_reference_audio = lambda _audio: b"RIFF-normalized"

            service.install_voice(b"source-audio", "안녕, 나는 야호야.")

            self.assertTrue(service.clone_ready)
            self.assertEqual(
                settings(directory).tts_reference_audio.read_bytes(),
                b"RIFF-normalized",
            )
            self.assertEqual(
                settings(directory).tts_reference_text.read_text(encoding="utf-8"),
                "안녕, 나는 야호야.",
            )
            self.assertEqual(probe.prompt_calls[0]["x_vector_only_mode"], False)

    def test_install_voice_without_transcript_uses_xvector_only(self) -> None:
        from app.tts import QwenTtsBackend

        with TemporaryDirectory() as directory:
            service = QwenTtsBackend(settings(directory))
            probe = ProbeCloneModel()
            service._clone_model = probe
            service._normalize_reference_audio = lambda _audio: b"RIFF-normalized"

            service.install_voice(b"source-audio", None)

            self.assertTrue(service.clone_ready)
            self.assertEqual(probe.prompt_calls[0]["x_vector_only_mode"], True)


if __name__ == "__main__":
    unittest.main()
