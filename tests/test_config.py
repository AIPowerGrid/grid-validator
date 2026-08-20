import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from eth_account import Account

from validator.config import Settings


TEST_ACCOUNT = Account.from_key("0x" + "11" * 32)


@contextmanager
def _valid_settings(**overrides):
    values = {
        "VALIDATOR_API_KEY": "grid-key",
        "VALIDATOR_PRIVATE_KEY": TEST_ACCOUNT.key.hex(),
        "VALIDATOR_WALLET": TEST_ACCOUNT.address,
        "REQUIRE_STAKE": False,
        **overrides,
    }
    with ExitStack() as stack:
        for name, value in values.items():
            stack.enter_context(patch.object(Settings, name, value))
        yield


class SettingsValidationTests(unittest.TestCase):
    def test_preview_requires_signing_key(self):
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            with self.assertRaisesRegex(RuntimeError, "VALIDATOR_PRIVATE_KEY"):
                Settings.validate()

    def test_private_key_requires_linked_wallet(self):
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            with self.assertRaisesRegex(RuntimeError, "VALIDATOR_WALLET"):
                Settings.validate()

    def test_grid_api_url_must_include_http_scheme(self):
        with _valid_settings(GRID_API_URL="api.aipowergrid.io"):
            with self.assertRaisesRegex(RuntimeError, "GRID_API_URL"):
                Settings.validate()

    def test_grid_api_url_is_normalized_after_validation(self):
        with _valid_settings(GRID_API_URL="https://api.aipowergrid.io/"):
            Settings.validate()
            self.assertEqual(Settings.GRID_API_URL, "https://api.aipowergrid.io")

    def test_dashboard_port_must_be_valid_tcp_port(self):
        with _valid_settings(DASHBOARD_PORT=99999):
            with self.assertRaisesRegex(RuntimeError, "DASHBOARD_PORT"):
                Settings.validate()

    def test_wallet_must_be_valid_address(self):
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
            patch.object(Settings, "VALIDATOR_WALLET", "0xnot-a-wallet"),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            with self.assertRaisesRegex(RuntimeError, "20-byte 0x hex"):
                Settings.validate()

    def test_onchain_addresses_must_be_valid_when_set(self):
        with _valid_settings(VALIDATOR_STAKING_ADDR="bad"):
            with self.assertRaisesRegex(RuntimeError, "VALIDATOR_STAKING_ADDR"):
                Settings.validate()

    def test_onchain_addresses_and_wallet_are_normalized(self):
        with _valid_settings(
            AIPG_TOKEN_ADDR="0x" + "AB" * 20,
            VALIDATOR_STAKING_ADDR="0x" + "CD" * 20,
        ):
            Settings.validate()
            self.assertEqual(Settings.VALIDATOR_WALLET, TEST_ACCOUNT.address.lower())
            self.assertEqual(Settings.AIPG_TOKEN_ADDR, "0x" + "ab" * 20)
            self.assertEqual(Settings.VALIDATOR_STAKING_ADDR, "0x" + "cd" * 20)

    def test_private_key_wallet_must_match(self):
        other = Account.create()
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
            patch.object(Settings, "VALIDATOR_WALLET", other.address.lower()),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                Settings.validate()

    def test_private_key_wallet_match_passes(self):
        with _valid_settings():
            Settings.validate()


if __name__ == "__main__":
    unittest.main()
