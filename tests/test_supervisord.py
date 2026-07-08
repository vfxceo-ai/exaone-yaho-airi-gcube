from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
SUPERVISORD_CONF = ROOT / "supervisord.conf"


class LlamaServerSupervisordContractTests(unittest.TestCase):
    def test_llama_server_runs_from_app_directory(self) -> None:
        text = SUPERVISORD_CONF.read_text(encoding="utf-8")

        self.assertIn("[program:llama-server]", text)
        self.assertIn("directory=/app", text)


if __name__ == "__main__":
    unittest.main()
