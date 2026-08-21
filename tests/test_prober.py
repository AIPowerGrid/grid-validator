import unittest
import hashlib
from unittest.mock import patch

from validator import prober


class ProberTests(unittest.TestCase):
    def test_score_failed_on_empty_answer(self):
        canary = {"expect": "42"}
        self.assertEqual(prober.score(canary, "", 0.1), "failed")

    def test_score_healthy_on_correct_answer_under_budget(self):
        canary = {"expect": "42"}
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(prober.score(canary, "42", 0.1), "healthy")

    def test_score_echo_requires_exact_nonce(self):
        canary = {"kind": "echo", "expect": "ABC123EF"}
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(prober.score(canary, "ABC123EF", 0.1), "healthy")
            self.assertEqual(prober.score(canary, "`ABC123EF`", 0.1), "healthy")
            self.assertEqual(prober.score(canary, "Reply with exactly ABC123EF", 0.1), "failed")
            self.assertEqual(prober.score(canary, "ABC123EF and nothing else", 0.1), "failed")

    def test_score_qa_allows_answer_in_short_phrase(self):
        canary = {"kind": "qa", "expect": "42"}
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(prober.score(canary, "The answer is 42.", 0.1), "healthy")

    def test_score_qa_requires_numeric_answer_boundary(self):
        canary = {"kind": "qa", "expect": "42"}
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(prober.score(canary, "142", 0.1), "failed")
            self.assertEqual(prober.score(canary, "42nd", 0.1), "failed")
            self.assertEqual(prober.score(canary, "about 42 tokens", 0.1), "healthy")

    def test_score_slow_on_correct_answer_over_budget(self):
        canary = {"expect": "42"}
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 1):
            self.assertEqual(prober.score(canary, "42", 2), "slow")

    def test_score_committed_grades_without_plaintext_answer(self):
        canary = {
            "kind": "math.add",
            "expected_hash": hashlib.sha256(b"42").hexdigest(),
        }
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(
                prober.score_committed(canary, "The answer is 42.", 0.1),
                "healthy",
            )
            self.assertEqual(prober.score_committed(canary, "420", 0.1), "failed")
            self.assertEqual(prober.score_committed(canary, "41 or 42", 0.1), "failed")

    def test_score_committed_echo_remains_exact(self):
        canary = {
            "kind": "echo",
            "expected_hash": hashlib.sha256(b"ABC123EF").hexdigest(),
        }
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(prober.score_committed(canary, "`ABC123EF`", 0.1), "healthy")
            self.assertEqual(
                prober.score_committed(canary, "token ABC123EF", 0.1),
                "failed",
            )

    def test_score_committed_rejects_malformed_commitment(self):
        with self.assertRaisesRegex(ValueError, "expected_hash"):
            prober.score_committed({"kind": "echo", "expected_hash": "bad"}, "x", 0.1)

    def test_make_canary_generates_unpredictable_math_qa(self):
        with (
            patch.object(prober.secrets, "randbelow", side_effect=[0, 2, 3]),
            patch.object(prober.secrets, "token_hex", return_value="abc123ef"),
        ):
            canary = prober.make_canary(1)

        self.assertEqual(canary["kind"], "qa")
        self.assertEqual(canary["nonce"], "abc123ef")
        self.assertEqual(canary["prompt"], "What is 13 plus 14? Reply with only the number.")
        self.assertEqual(canary["expect"], "27")

    def test_make_canary_generates_multiplication_qa(self):
        with (
            patch.object(prober.secrets, "randbelow", side_effect=[2, 1, 2]),
            patch.object(prober.secrets, "token_hex", return_value="abc123ef"),
        ):
            canary = prober.make_canary(3)

        self.assertEqual(canary["prompt"], "What is 7 multiplied by 8? Reply with only the number.")
        self.assertEqual(canary["expect"], "56")

    def test_media_names_are_not_text_models(self):
        self.assertFalse(prober.is_text_model("stable-diffusion-xl"))
        self.assertTrue(prober.is_text_model("qwen3-32b"))


if __name__ == "__main__":
    unittest.main()
