from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
import os
from pathlib import Path
import tempfile
from typing import Annotated, Protocol
from urllib.error import URLError
from urllib.request import urlopen

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


def default_llm_ready_checker(url: str) -> bool:
    try:
        with urlopen(url, timeout=1.5) as response:
            return 200 <= response.status < 300
    except (OSError, URLError):
        return False


def create_app(
    settings: Settings,
    backend: SttBackend,
    llm_ready_checker: Callable[[str], bool] = default_llm_ready_checker,
) -> FastAPI:
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
        stt_ready = backend.ready
        llm_ready = llm_ready_checker(settings.llm_health_url)
        return {
            "service": "gateway",
            "ready": stt_ready and llm_ready,
            "stt_ready": stt_ready,
            "llm_ready": llm_ready,
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
