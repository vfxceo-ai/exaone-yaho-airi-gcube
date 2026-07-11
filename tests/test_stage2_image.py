from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class Stage2ImageContractTests(unittest.TestCase):
    def test_dockerfile_bakes_both_qwen_tts_checkpoints(self) -> None:
        text = (ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice", text)
        self.assertIn("Qwen/Qwen3-TTS-12Hz-0.6B-Base", text)
        self.assertIn("/opt/models/tts/custom", text)
        self.assertIn("/opt/models/tts/base", text)

    def test_dockerfile_uses_cuda_13_pytorch_wheels(self) -> None:
        text = (ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("torch==2.12.1", text)
        self.assertIn("torchaudio==2.12.1", text)
        self.assertIn("https://download.pytorch.org/whl/cu130", text)
        self.assertIn("requirements-tts.txt", text)

    def test_nginx_exposes_tts_prefix(self) -> None:
        text = (ROOT / "nginx.conf").read_text(encoding="utf-8")

        self.assertIn("location /tts/v1/", text)
        self.assertIn("proxy_pass http://127.0.0.1:8001/v1/;", text)

    def test_voice_api_uses_combined_virtual_environment(self) -> None:
        text = (ROOT / "supervisord.conf").read_text(encoding="utf-8")

        self.assertIn("/opt/voice-venv/bin/uvicorn", text)

    def test_stage2_manifest_keeps_connection_and_dropbox_contract(self) -> None:
        text = (ROOT / "workload-stage2.template.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn('containerImage: "${GHCR_OWNER}/exaone-yaho-airi:stage2"', text)
        self.assertIn("maxConnection: 20", text)
        self.assertIn('"98": "/mnt/dropbox"', text)
        self.assertIn('gpuCode: "${GPU_CODE}"', text)
        self.assertIn("TTS_REFERENCE_AUDIO", text)
        self.assertIn("TTS_REFERENCE_TEXT", text)

    def test_workflow_publishes_stage2_tag(self) -> None:
        text = (ROOT / ".github" / "workflows" / "build.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("requirements-tts.txt", text)
        self.assertIn("exaone-yaho-airi:stage2", text)


if __name__ == "__main__":
    unittest.main()
