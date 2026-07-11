import importlib
import os
import unittest
from unittest.mock import patch


VALID_API_KEY = "test-secret-0123456789abcdef0123456789"


def load_config_module():
    try:
        return importlib.import_module("app.config")
    except ModuleNotFoundError as exc:
        raise AssertionError("app.config has not been implemented yet") from exc


class SettingsContractTests(unittest.TestCase):
    def test_api_key_is_required(self) -> None:
        config = load_config_module()

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "at least 32 characters"):
                config.Settings.from_env()

    def test_short_api_key_is_rejected(self) -> None:
        config = load_config_module()

        with patch.dict(os.environ, {"API_KEY": "too-short"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "at least 32 characters"):
                config.Settings.from_env()

    def test_defaults_target_korean_large_v3_turbo(self) -> None:
        config = load_config_module()

        with patch.dict(os.environ, {"API_KEY": VALID_API_KEY}, clear=True):
            settings = config.Settings.from_env()

        self.assertEqual(settings.api_key, VALID_API_KEY)
        self.assertEqual(settings.stt_model_id, "/models/stt")
        self.assertEqual(settings.stt_compute_type, "int8_float16")
        self.assertEqual(settings.stt_language, "ko")
        self.assertEqual(settings.log_level, "INFO")
        self.assertEqual(settings.llm_health_url, "http://127.0.0.1:8000/health")
        self.assertEqual(settings.tts_custom_model_id, "/models/tts/custom")
        self.assertEqual(settings.tts_clone_model_id, "/models/tts/base")
        self.assertEqual(settings.tts_language, "Korean")
        self.assertEqual(settings.tts_default_voice, "sohee")
        self.assertEqual(settings.tts_clone_voice, "yaho")
        self.assertEqual(
            settings.tts_reference_audio.as_posix(),
            "/mnt/dropbox/gcube/AIRI/voices/yaho/reference.wav",
        )
        self.assertEqual(
            settings.tts_reference_text.as_posix(),
            "/mnt/dropbox/gcube/AIRI/voices/yaho/reference.txt",
        )
        self.assertEqual(settings.tts_dtype, "bfloat16")
        self.assertEqual(settings.tts_attention, "sdpa")
        self.assertEqual(settings.tts_max_input_chars, 1000)


if __name__ == "__main__":
    unittest.main()
