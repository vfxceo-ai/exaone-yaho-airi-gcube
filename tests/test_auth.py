import importlib
import unittest


API_KEY = "test-secret-0123456789abcdef0123456789"


def load_auth_module():
    try:
        return importlib.import_module("app.auth")
    except ModuleNotFoundError as exc:
        raise AssertionError("app.auth has not been implemented yet") from exc


class AuthContractTests(unittest.TestCase):
    def test_missing_bearer_token_is_rejected(self) -> None:
        auth = load_auth_module()

        self.assertFalse(auth.is_authorized(API_KEY, None))

    def test_wrong_bearer_token_is_rejected(self) -> None:
        auth = load_auth_module()

        self.assertFalse(auth.is_authorized(API_KEY, "Bearer wrong"))

    def test_matching_bearer_token_is_accepted(self) -> None:
        auth = load_auth_module()

        self.assertTrue(auth.is_authorized(API_KEY, f"Bearer {API_KEY}"))

    def test_non_bearer_scheme_is_rejected(self) -> None:
        auth = load_auth_module()

        self.assertFalse(auth.is_authorized(API_KEY, f"Basic {API_KEY}"))


if __name__ == "__main__":
    unittest.main()
