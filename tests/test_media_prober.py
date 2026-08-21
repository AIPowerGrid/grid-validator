import unittest
from unittest.mock import patch

from validator import media_prober


class MediaChallengeTests(unittest.TestCase):
    def test_preview_canary_uses_cryptographic_seed_and_not_round_index(self):
        choices = iter([
            "dragon", "cobalt", "on the moon", "wide establishing view",
            "moonlit haze", "moving steadily from left to right",
        ])
        with (
            patch.object(media_prober.secrets, "choice", side_effect=choices),
            patch.object(media_prober.secrets, "token_hex", return_value="a1b2c3"),
            patch.object(media_prober.secrets, "randbits", return_value=987654321),
        ):
            canary = media_prober.make_media_canary(0, kind="video")

        self.assertEqual(canary["payload"]["seed"], 987654321)
        self.assertIn("dragon", canary["prompt"])
        self.assertIn("moving steadily from left to right", canary["prompt"])
        self.assertEqual(canary["payload"]["frames"], 16)

    def test_no_public_fixed_seed_constant_exists(self):
        self.assertFalse(hasattr(media_prober, "CANARY_SEED"))


if __name__ == "__main__":
    unittest.main()
