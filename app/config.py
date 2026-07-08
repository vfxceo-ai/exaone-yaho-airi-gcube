from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    api_key: str
    stt_model_id: str
    stt_compute_type: str
    stt_language: str
    log_level: str
    llm_health_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.environ.get("API_KEY", "")
        if len(api_key) < 32:
            raise RuntimeError("API_KEY must contain at least 32 characters")

        return cls(
            api_key=api_key,
            stt_model_id=os.getenv("STT_MODEL_ID", "large-v3-turbo"),
            stt_compute_type=os.getenv("STT_COMPUTE_TYPE", "int8_float16"),
            stt_language=os.getenv("STT_LANGUAGE", "ko"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            llm_health_url=os.getenv("LLM_HEALTH_URL", "http://127.0.0.1:8000/health"),
        )
