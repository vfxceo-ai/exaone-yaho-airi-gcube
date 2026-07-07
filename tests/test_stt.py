from concurrent.futures import ThreadPoolExecutor
import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
import time
import unittest

from app.config import Settings


def load_stt_module():
    try:
        return importlib.import_module("app.stt")
    except ModuleNotFoundError as exc:
        raise AssertionError("app.stt has not been implemented yet") from exc


class Segment:
    text = "확인"


class ProbeModel:
    def __init__(self) -> None:
        self.guard = Lock()
        self.active = 0
        self.peak = 0

    def transcribe(self, *_args, **_kwargs):
        with self.guard:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(0.05)
        with self.guard:
            self.active -= 1
        return iter([Segment()]), object()


def settings() -> Settings:
    return Settings(
        api_key="x" * 32,
        stt_model_id="large-v3-turbo",
        stt_compute_type="int8_float16",
        stt_language="ko",
        log_level="INFO",
    )


class SttBackendContractTests(unittest.TestCase):
    def test_backend_starts_not_ready(self) -> None:
        stt = load_stt_module()

        service = stt.FasterWhisperBackend(settings())

        self.assertFalse(service.ready)

    def test_transcribe_before_load_is_rejected(self) -> None:
        stt = load_stt_module()
        service = stt.FasterWhisperBackend(settings())

        with TemporaryDirectory() as directory:
            audio = Path(directory) / "sample.wav"
            audio.write_bytes(b"RIFF-test")
            with self.assertRaisesRegex(RuntimeError, "not ready"):
                service.transcribe(audio, "ko")

    def test_backend_serializes_gpu_transcription(self) -> None:
        stt = load_stt_module()
        service = stt.FasterWhisperBackend(settings())
        probe = ProbeModel()
        service._model = probe

        with TemporaryDirectory() as directory:
            audio = Path(directory) / "sample.wav"
            audio.write_bytes(b"RIFF-test")
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(service.transcribe, audio, "ko")
                    for _ in range(2)
                ]
                self.assertEqual(
                    [future.result() for future in futures],
                    ["확인", "확인"],
                )

        self.assertEqual(probe.peak, 1)


if __name__ == "__main__":
    unittest.main()
