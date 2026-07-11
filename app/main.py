from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
import os
from pathlib import Path
import tempfile
from typing import Annotated, Literal, Protocol
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from .auth import is_authorized
from .config import Settings
from .stt import FasterWhisperBackend
from .tts import QwenTtsBackend, SynthesizedAudio, VoiceNotReadyError


class SttBackend(Protocol):
    @property
    def ready(self) -> bool: ...

    def load(self) -> None: ...

    def transcribe(self, path: Path, language: str) -> str: ...


class TtsBackend(Protocol):
    @property
    def ready(self) -> bool: ...

    @property
    def clone_ready(self) -> bool: ...

    def load(self) -> None: ...

    def synthesize(
        self,
        text: str,
        voice: str,
        response_format: str,
        speed: float,
    ) -> SynthesizedAudio: ...

    def install_voice(self, audio: bytes, transcript: str | None) -> None: ...


class SpeechRequest(BaseModel):
    model: str
    input: str = Field(min_length=1)
    voice: str
    response_format: Literal["mp3", "wav"] = "mp3"
    speed: float = Field(default=1.0, ge=0.25, le=4.0)


def default_llm_ready_checker(url: str) -> bool:
    try:
        with urlopen(url, timeout=1.5) as response:
            return 200 <= response.status < 300
    except (OSError, URLError):
        return False


def create_app(
    settings: Settings,
    backend: SttBackend,
    tts_backend: TtsBackend,
    llm_ready_checker: Callable[[str], bool] = default_llm_ready_checker,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await run_in_threadpool(backend.load)
        await run_in_threadpool(tts_backend.load)
        yield

    application = FastAPI(
        title="EXAONE-Yaho AIRI Voice API",
        version="2.0.0",
        lifespan=lifespan,
    )

    def authorized(
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        if not is_authorized(settings.api_key, authorization):
            raise HTTPException(status_code=401, detail="Invalid bearer token")

    @application.get("/healthz")
    def healthz() -> dict[str, object]:
        stt_ready = backend.ready
        llm_ready = llm_ready_checker(settings.llm_health_url)
        tts_ready = tts_backend.ready
        return {
            "service": "gateway",
            "ready": stt_ready and llm_ready and tts_ready,
            "stt_ready": stt_ready,
            "llm_ready": llm_ready,
            "tts_ready": tts_ready,
            "tts_clone_ready": tts_backend.clone_ready,
        }

    @application.get("/v1/models", dependencies=[Depends(authorized)])
    def models() -> dict[str, object]:
        return {
            "object": "list",
            "data": [
                {
                    "id": "whisper-1",
                    "object": "model",
                    "owned_by": "self-hosted",
                },
                {
                    "id": "qwen3-tts",
                    "object": "model",
                    "owned_by": "self-hosted",
                },
            ],
        }

    @application.post(
        "/v1/audio/transcriptions",
        dependencies=[Depends(authorized)],
    )
    async def transcriptions(
        file: UploadFile = File(...),
        model: str = Form(...),
        language: str = Form(default="ko"),
    ) -> dict[str, str]:
        if model != "whisper-1":
            raise HTTPException(status_code=400, detail="model must be whisper-1")

        suffix = Path(file.filename or "audio.wav").suffix or ".wav"
        descriptor, temporary_name = tempfile.mkstemp(suffix=suffix)
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            with temporary_path.open("wb") as temporary:
                while chunk := await file.read(1024 * 1024):
                    temporary.write(chunk)
            text = await run_in_threadpool(
                backend.transcribe,
                temporary_path,
                language,
            )
        finally:
            temporary_path.unlink(missing_ok=True)

        return {"text": text}

    @application.post(
        "/v1/audio/speech",
        dependencies=[Depends(authorized)],
    )
    async def speech(request: SpeechRequest) -> Response:
        if request.model not in {"qwen3-tts", "tts-1"}:
            raise HTTPException(
                status_code=400,
                detail="model must be qwen3-tts or tts-1",
            )
        if len(request.input) > settings.tts_max_input_chars:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"input exceeds TTS_MAX_INPUT_CHARS="
                    f"{settings.tts_max_input_chars}"
                ),
            )

        try:
            result = await run_in_threadpool(
                tts_backend.synthesize,
                request.input,
                request.voice,
                request.response_format,
                request.speed,
            )
        except VoiceNotReadyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return Response(content=result.data, media_type=result.media_type)

    @application.put(
        "/v1/voices/{voice}",
        dependencies=[Depends(authorized)],
    )
    async def install_voice(
        voice: str,
        file: UploadFile = File(...),
        transcript: str | None = Form(default=None),
    ) -> dict[str, object]:
        if voice.lower() != settings.tts_clone_voice.lower():
            raise HTTPException(
                status_code=400,
                detail=f"voice must be {settings.tts_clone_voice}",
            )

        sample = bytearray()
        while chunk := await file.read(1024 * 1024):
            sample.extend(chunk)
            if len(sample) > 25 * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail="voice sample exceeds 25 MiB",
                )

        try:
            await run_in_threadpool(
                tts_backend.install_voice,
                bytes(sample),
                transcript,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return {
            "voice": settings.tts_clone_voice,
            "ready": tts_backend.clone_ready,
            "transcript_used": bool((transcript or "").strip()),
        }

    return application


runtime_settings = Settings.from_env()
runtime_backend = FasterWhisperBackend(runtime_settings)
runtime_tts_backend = QwenTtsBackend(runtime_settings)
app = create_app(runtime_settings, runtime_backend, runtime_tts_backend)
