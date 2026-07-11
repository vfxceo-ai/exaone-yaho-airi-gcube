from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    api_key: str
    stt_model_id: str
    stt_compute_type: str
    stt_language: str
    log_level: str
    llm_health_url: str
    tts_custom_model_id: str = "/models/tts/custom"
    tts_clone_model_id: str = "/models/tts/base"
    tts_language: str = "Korean"
    tts_default_voice: str = "sohee"
    tts_clone_voice: str = "yaho"
    tts_reference_audio: Path = Path(
        "/mnt/dropbox/gcube/AIRI/voices/yaho/reference.wav"
    )
    tts_reference_text: Path = Path(
        "/mnt/dropbox/gcube/AIRI/voices/yaho/reference.txt"
    )
    tts_dtype: str = "bfloat16"
    tts_attention: str = "sdpa"
    tts_device: str = "cuda:0"
    tts_max_input_chars: int = 1000

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.environ.get("API_KEY", "")
        if len(api_key) < 32:
            raise RuntimeError("API_KEY must contain at least 32 characters")

        return cls(
            api_key=api_key,
            stt_model_id=os.getenv("STT_MODEL_ID", "/models/stt"),
            stt_compute_type=os.getenv("STT_COMPUTE_TYPE", "int8_float16"),
            stt_language=os.getenv("STT_LANGUAGE", "ko"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            llm_health_url=os.getenv("LLM_HEALTH_URL", "http://127.0.0.1:8000/health"),
            tts_custom_model_id=os.getenv(
                "TTS_CUSTOM_MODEL_ID",
                "/models/tts/custom",
            ),
            tts_clone_model_id=os.getenv(
                "TTS_CLONE_MODEL_ID",
                "/models/tts/base",
            ),
            tts_language=os.getenv("TTS_LANGUAGE", "Korean"),
            tts_default_voice=os.getenv("TTS_DEFAULT_VOICE", "sohee"),
            tts_clone_voice=os.getenv("TTS_CLONE_VOICE", "yaho"),
            tts_reference_audio=Path(
                os.getenv(
                    "TTS_REFERENCE_AUDIO",
                    "/mnt/dropbox/gcube/AIRI/voices/yaho/reference.wav",
                )
            ),
            tts_reference_text=Path(
                os.getenv(
                    "TTS_REFERENCE_TEXT",
                    "/mnt/dropbox/gcube/AIRI/voices/yaho/reference.txt",
                )
            ),
            tts_dtype=os.getenv("TTS_DTYPE", "bfloat16"),
            tts_attention=os.getenv("TTS_ATTENTION", "sdpa"),
            tts_device=os.getenv("TTS_DEVICE", "cuda:0"),
            tts_max_input_chars=int(os.getenv("TTS_MAX_INPUT_CHARS", "1000")),
        )
