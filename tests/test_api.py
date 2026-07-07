import importlib
import os
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from app.config import Settings


API_KEY = "test-secret-0123456789abcdef0123456789"
os.environ.setdefault("API_KEY", API_KEY)


def load_main_module():
    try:
        return importlib.import_module("app.main")
    except ModuleNotFoundError as exc:
        raise AssertionError("app.main has not been implemented yet") from exc


class FakeSttBackend:
    def __init__(self) -> None:
        self.ready = False

    def load(self) -> None:
        self.ready = True

    def transcribe(self, path: Path, language: str) -> str:
        if not path.exists():
            raise AssertionError("temporary upload does not exist")
        if language != "ko":
            raise AssertionError(f"unexpected language: {language}")
        return "오늘 기분 완전 좋아"


def test_settings() -> Settings:
    return Settings(
        api_key=API_KEY,
        stt_model_id="large-v3-turbo",
        stt_compute_type="int8_float16",
        stt_language="ko",
        log_level="INFO",
    )


class OpenAiCompatibleApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        main = load_main_module()
        self.backend = FakeSttBackend()
        self.client_context = TestClient(
            main.create_app(test_settings(), self.backend)
        )
        self.client = self.client_context.__enter__()
        self.auth_headers = {"Authorization": f"Bearer {API_KEY}"}

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)

    def test_health_reports_stt_readiness(self) -> None:
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"service": "stt", "ready": True})

    def test_models_requires_bearer_authentication(self) -> None:
        response = self.client.get("/v1/models")

        self.assertEqual(response.status_code, 401)

    def test_models_returns_whisper_alias(self) -> None:
        response = self.client.get("/v1/models", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["id"], "whisper-1")

    def test_transcription_returns_openai_json(self) -> None:
        response = self.client.post(
            "/v1/audio/transcriptions",
            headers=self.auth_headers,
            files={"file": ("voice.wav", b"RIFF-test", "audio/wav")},
            data={"model": "whisper-1", "language": "ko"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"text": "오늘 기분 완전 좋아"})

    def test_transcription_rejects_unknown_model(self) -> None:
        response = self.client.post(
            "/v1/audio/transcriptions",
            headers=self.auth_headers,
            files={"file": ("voice.wav", b"RIFF-test", "audio/wav")},
            data={"model": "other-model"},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
