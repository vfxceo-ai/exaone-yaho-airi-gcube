from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
from pathlib import Path
import tempfile
from typing import Annotated, Protocol

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from .auth import is_authorized
from .config import Settings
from .stt import FasterWhisperBackend


class SttBackend(Protocol):
    @property
    def ready(self) -> bool: ...

    def load(self) -> None: ...

    def transcribe(self, path: Path, language: str) -> str: ...


def create_app(settings: Settings, backend: SttBackend) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await run_in_threadpool(backend.load)
        yield

    application = FastAPI(
        title="EXAONE-Yaho AIRI STT API",
        version="1.0.0",
        lifespan=lifespan,
    )

    def authorized(
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        if not is_authorized(settings.api_key, authorization):
            raise HTTPException(status_code=401, detail="Invalid bearer token")

    @application.get("/healthz")
    def healthz() -> dict[str, object]:
        return {"service": "stt", "ready": backend.ready}

    @application.get("/v1/models", dependencies=[Depends(authorized)])
    def models() -> dict[str, object]:
        return {
            "object": "list",
            "data": [
                {
                    "id": "whisper-1",
                    "object": "model",
                    "owned_by": "self-hosted",
                }
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

    return application


runtime_settings = Settings.from_env()
runtime_backend = FasterWhisperBackend(runtime_settings)
app = create_app(runtime_settings, runtime_backend)
