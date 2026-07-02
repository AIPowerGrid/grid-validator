import unittest
from unittest.mock import patch

from eth_account import Account

from validator.config import Settings


class SettingsValidationTests(unittest.TestCase):
    def test_unsigned_v0_preview_does_not_require_wallet(self):
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            Settings.validate()

    def test_private_key_requires_wallet_for_verifiable_signature(self):
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", "0x" + "11" * 32),
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            with self.assertRaisesRegex(RuntimeError, "VALIDATOR_WALLET"):
                Settings.validate()

    def test_grid_api_url_must_include_http_scheme(self):
        with (
            patch.object(Settings, "GRID_API_URL", "api.aipowergrid.io"),
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            with self.assertRaisesRegex(RuntimeError, "GRID_API_URL"):
                Settings.validate()

    def test_grid_api_url_is_normalized_after_validation(self):
        with (
            patch.object(Settings, "GRID_API_URL", "https://api.aipowergrid.io/"),
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            Settings.validate()
            self.assertEqual(Settings.GRID_API_URL, "https://api.aipowergrid.io")

    def test_dashboard_port_must_be_valid_tcp_port(self):
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "DASHBOARD_PORT", 99999),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            with self.assertRaisesRegex(RuntimeError, "DASHBOARD_PORT"):
                Settings.validate()

    def test_private_key_rejects_whitespace_wallet(self):
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", "0x" + "11" * 32),
            patch.object(Settings, "VALIDATOR_WALLET", "   "),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            with self.assertRaisesRegex(RuntimeError, "VALIDATOR_WALLET"):
                Settings.validate()

    def test_optional_wallet_must_be_valid_address(self):
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
            patch.object(Settings, "VALIDATOR_WALLET", "0xnot-a-wallet"),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            with self.assertRaisesRegex(RuntimeError, "20-byte 0x hex"):
                Settings.validate()

    def test_optional_onchain_addresses_must_be_valid_when_set(self):
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "AIPG_TOKEN_ADDR", "0x" + "12" * 20),
            patch.object(Settings, "VALIDATOR_STAKING_ADDR", "bad"),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            with self.assertRaisesRegex(RuntimeError, "VALIDATOR_STAKING_ADDR"):
                Settings.validate()

    def test_onchain_addresses_are_normalized_after_validation(self):
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "AIPG_TOKEN_ADDR", "0x" + "AB" * 20),
            patch.object(Settings, "VALIDATOR_STAKING_ADDR", "0x" + "CD" * 20),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            Settings.validate()
            self.assertEqual(Settings.AIPG_TOKEN_ADDR, "0x" + "ab" * 20)
            self.assertEqual(Settings.VALIDATOR_STAKING_ADDR, "0x" + "cd" * 20)

    def test_optional_checksum_wallet_passes_without_private_key(self):
        account = Account.create()
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
            patch.object(Settings, "VALIDATOR_WALLET", account.address),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            Settings.validate()

    def test_wallet_is_normalized_after_validation(self):
        account = Account.create()
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
            patch.object(Settings, "VALIDATOR_WALLET", f"  {account.address}  "),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            Settings.validate()
            self.assertEqual(Settings.VALIDATOR_WALLET, account.address.lower())

    def test_private_key_wallet_must_match(self):
        account = Account.create()
        other = Account.create()
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", account.key.hex()),
            patch.object(Settings, "VALIDATOR_WALLET", other.address.lower()),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                Settings.validate()

    def test_private_key_wallet_match_passes(self):
        account = Account.create()
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", "grid-key"),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", account.key.hex()),
            patch.object(Settings, "VALIDATOR_WALLET", account.address.lower()),
            patch.object(Settings, "REQUIRE_STAKE", False),
        ):
            Settings.validate()


if __name__ == "__main__":
    unittest.main()
