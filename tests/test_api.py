import importlib
import os
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from app.config import Settings
from app.tts import SynthesizedAudio


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


class FakeTtsBackend:
    def __init__(self) -> None:
        self.ready = False
        self.clone_ready = False
        self.last_request: tuple[str, str, str, float] | None = None

    def load(self) -> None:
        self.ready = True

    def synthesize(
        self,
        text: str,
        voice: str,
        response_format: str,
        speed: float,
    ) -> SynthesizedAudio:
        self.last_request = (text, voice, response_format, speed)
        return SynthesizedAudio(b"ID3-test-audio", "audio/mpeg")

    def install_voice(self, audio: bytes, transcript: str | None) -> None:
        if not audio:
            raise AssertionError("voice sample is empty")
        self.clone_ready = True


def test_settings() -> Settings:
    return Settings(
        api_key=API_KEY,
        stt_model_id="/models/stt",
        stt_compute_type="int8_float16",
        stt_language="ko",
        log_level="INFO",
        llm_health_url="http://127.0.0.1:8000/health",
    )


class OpenAiCompatibleApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        main = load_main_module()
        self.backend = FakeSttBackend()
        self.tts_backend = FakeTtsBackend()
        self.client_context = TestClient(
            main.create_app(
                test_settings(),
                self.backend,
                self.tts_backend,
                llm_ready_checker=lambda _url: True,
            )
        )
        self.client = self.client_context.__enter__()
        self.auth_headers = {"Authorization": f"Bearer {API_KEY}"}

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)

    def test_health_reports_gateway_readiness(self) -> None:
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "service": "gateway",
                "ready": True,
                "stt_ready": True,
                "llm_ready": True,
                "tts_ready": True,
                "tts_clone_ready": False,
            },
        )

    def test_models_requires_bearer_authentication(self) -> None:
        response = self.client.get("/v1/models")

        self.assertEqual(response.status_code, 401)

    def test_models_returns_whisper_alias(self) -> None:
        response = self.client.get("/v1/models", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [model["id"] for model in response.json()["data"]],
            ["whisper-1", "qwen3-tts"],
        )

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

    def test_speech_returns_openai_compatible_audio(self) -> None:
        response = self.client.post(
            "/v1/audio/speech",
            headers=self.auth_headers,
            json={
                "model": "qwen3-tts",
                "input": "안녕! 오늘도 완전 신나게 가자!",
                "voice": "sohee",
                "response_format": "mp3",
                "speed": 1.1,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/mpeg")
        self.assertEqual(response.content, b"ID3-test-audio")
        self.assertEqual(
            self.tts_backend.last_request,
            ("안녕! 오늘도 완전 신나게 가자!", "sohee", "mp3", 1.1),
        )

    def test_speech_requires_bearer_authentication(self) -> None:
        response = self.client.post(
            "/v1/audio/speech",
            json={"model": "qwen3-tts", "input": "안녕", "voice": "sohee"},
        )

        self.assertEqual(response.status_code, 401)

    def test_speech_rejects_unknown_model(self) -> None:
        response = self.client.post(
            "/v1/audio/speech",
            headers=self.auth_headers,
            json={"model": "other", "input": "안녕", "voice": "sohee"},
        )

        self.assertEqual(response.status_code, 400)

    def test_voice_sample_upload_activates_clone_voice(self) -> None:
        response = self.client.put(
            "/v1/voices/yaho",
            headers=self.auth_headers,
            files={"file": ("reference.wav", b"RIFF-test", "audio/wav")},
            data={"transcript": "안녕, 나는 야호야."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ready"])
        self.assertTrue(self.tts_backend.clone_ready)


if __name__ == "__main__":
    unittest.main()
