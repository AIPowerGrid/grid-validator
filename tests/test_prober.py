import unittest
import hashlib
import json
from unittest.mock import patch

from validator import prober


class ProberTests(unittest.TestCase):
    @staticmethod
    def _repeat_to_tokens(token: str, minimum: int) -> str:
        pieces = []
        while prober._count_tokens(" ".join(pieces)) < minimum:
            pieces.append(token)
        return " ".join(pieces)

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

    def test_score_committed_json_is_semantic_and_rejects_markdown(self):
        expected = json.dumps(
            {"alpha": "A1", "count": 7},
            sort_keys=True,
            separators=(",", ":"),
        )
        canary = {
            "kind": "json.object",
            "expected_hash": hashlib.sha256(expected.encode()).hexdigest(),
        }
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(
                prober.score_committed(canary, '{"count":7,"alpha":"A1"}', 0.1),
                "healthy",
            )
            self.assertEqual(
                prober.score_committed(canary, f"```json\n{expected}\n```", 0.1),
                "failed",
            )

    def test_score_committed_context_requires_exact_token(self):
        canary = {
            "kind": "context.retrieve",
            "expected_hash": hashlib.sha256(b"A1B2C3D4").hexdigest(),
        }
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(prober.score_committed(canary, "`A1B2C3D4`", 0.1), "healthy")
            self.assertEqual(
                prober.score_committed(canary, "The value is A1B2C3D4", 0.1),
                "failed",
            )

    def test_score_committed_16k_context_uses_the_same_exact_contract(self):
        canary = {
            "kind": "context.retrieve.16k",
            "expected_hash": hashlib.sha256(b"A1B2C3D4").hexdigest(),
        }
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(
                prober.score_committed(canary, "`A1B2C3D4`", 0.1),
                "healthy",
            )
            self.assertEqual(
                prober.score_committed(canary, "A1B2C3D4 extra", 0.1),
                "failed",
            )

    def test_score_committed_32k_context_uses_the_same_exact_contract(self):
        canary = {
            "kind": "context.retrieve.32k",
            "expected_hash": hashlib.sha256(b"A1B2C3D4").hexdigest(),
        }
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(
                prober.score_committed(canary, "`A1B2C3D4`", 0.1),
                "healthy",
            )
            self.assertEqual(
                prober.score_committed(canary, "A1B2C3D4 extra", 0.1),
                "failed",
            )

    def test_score_committed_multistep_rejects_ambiguous_numbers(self):
        canary = {
            "kind": "logic.steps",
            "expected_hash": hashlib.sha256(b"42").hexdigest(),
        }
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(
                prober.score_committed(canary, "The final result is 42.", 0.1),
                "healthy",
            )
            self.assertEqual(prober.score_committed(canary, "41 or 42", 0.1), "failed")

    def test_score_committed_tool_call_requires_one_exact_call_and_no_text(self):
        expected = json.dumps(
            {"arguments": {"count_a": 7, "token_b": "A1"}, "name": "record_c"},
            sort_keys=True, separators=(",", ":"),
        )
        correct = [{
            "id": "call_opaque", "type": "function",
            "function": {
                "name": "record_c", "arguments": '{"token_b":"A1","count_a":7}',
            },
        }]
        canary = {
            "kind": "tool.call",
            "expected_hash": hashlib.sha256(expected.encode()).hexdigest(),
            "tool_calls": correct,
        }
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(prober.score_committed(canary, "", 0.1), "healthy")
            self.assertEqual(prober.score_committed(canary, "I called it.", 0.1), "failed")
            self.assertEqual(
                prober.score_committed({**canary, "tool_calls": correct + correct}, "", 0.1),
                "failed",
            )

    def test_score_committed_tool_chain_requires_both_exact_calls(self):
        expected_calls = [
            {"arguments": {"key_a": "K1"}, "name": "lookup_a"},
            {"arguments": {"token_c": "T1", "total_b": 42}, "name": "submit_b"},
        ]
        chain = [
            {
                "text": "",
                "tool_calls": [{
                    "id": "call_1", "type": "function",
                    "function": {"name": "lookup_a", "arguments": '{"key_a":"K1"}'},
                }],
            },
            {
                "text": "",
                "tool_calls": [{
                    "id": "call_2", "type": "function",
                    "function": {
                        "name": "submit_b",
                        "arguments": '{"total_b":42,"token_c":"T1"}',
                    },
                }],
            },
        ]
        expected = json.dumps(expected_calls, sort_keys=True, separators=(",", ":"))
        canary = {
            "kind": "tool.chain",
            "expected_hash": hashlib.sha256(expected.encode()).hexdigest(),
            "tool_calls": chain,
        }
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(prober.score_committed(canary, "", 0.1), "healthy")
            self.assertEqual(
                prober.score_committed({**canary, "tool_calls": chain[:1]}, "", 0.1),
                "failed",
            )

    def test_score_committed_stop_sequence_requires_only_the_prefix(self):
        canary = {
            "kind": "stop.sequence",
            "expected_hash": hashlib.sha256(b"ABC123").hexdigest(),
        }
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(prober.score_committed(canary, "ABC123", 0.1), "healthy")
            self.assertEqual(
                prober.score_committed(canary, "ABC123<STOP_XYZ>TAIL", 0.1),
                "failed",
            )

    def test_score_committed_token_limit_requires_cutoff_and_bounded_grid_count(self):
        token = "repeat_marker"
        max_tokens = 192
        canary = {
            "kind": "token.limit",
            "max_tokens": max_tokens,
            "expected_hash": hashlib.sha256(token.encode()).hexdigest(),
        }
        healthy = self._repeat_to_tokens(token, max_tokens // 2)
        too_short = healthy.rsplit(" ", 1)[0]
        too_long = self._repeat_to_tokens(token, ((max_tokens * 5) + 3) // 4 + 9)
        with patch.object(prober.Settings, "LATENCY_BUDGET_S", 30):
            self.assertEqual(
                prober.score_committed(
                    canary, healthy, 0.1, finish_reason="length"
                ),
                "healthy",
            )
            self.assertEqual(
                prober.score_committed(canary, healthy, 0.1, finish_reason="stop"),
                "failed",
            )
            self.assertEqual(
                prober.score_committed(
                    canary, too_short, 0.1, finish_reason="length"
                ),
                "failed",
            )
            self.assertEqual(
                prober.score_committed(
                    canary,
                    healthy + " WRONG",
                    0.1,
                    finish_reason="length",
                ),
                "failed",
            )
            self.assertEqual(
                prober.score_committed(
                    canary, too_long, 0.1, finish_reason="length"
                ),
                "failed",
            )

    def test_score_committed_token_limit_counts_reasoning_output(self):
        token = "visible_marker"
        max_tokens = 160
        visible = self._repeat_to_tokens(token, max_tokens // 2)
        reasoning = self._repeat_to_tokens("reasoning_marker", max_tokens)
        canary = {
            "kind": "token.limit",
            "max_tokens": max_tokens,
            "expected_hash": hashlib.sha256(token.encode()).hexdigest(),
        }
        self.assertEqual(
            prober.score_committed(
                canary,
                visible,
                0.1,
                reasoning_text=reasoning,
                finish_reason="length",
            ),
            "failed",
        )

    def test_token_limit_capability_fails_closed_when_encoding_cannot_load(self):
        canary = {
            "kind": "token.limit",
            "max_tokens": 64,
            "expected_hash": hashlib.sha256(b"repeat_marker").hexdigest(),
        }
        with (
            patch.object(prober, "_TOKEN_ENCODING", None),
            patch.object(
                prober.tiktoken,
                "get_encoding",
                side_effect=ValueError("plugin unavailable"),
            ),
            patch.object(
                prober._tiktoken_openai_public,
                "o200k_base",
                side_effect=OSError("encoding unavailable"),
            ),
        ):
            self.assertFalse(prober.token_limit_available())
            with self.assertRaises(prober.ScorerUnavailable):
                prober.score_committed(
                    canary,
                    "repeat_marker repeat_marker",
                    0.1,
                    finish_reason="length",
                )

    def test_score_committed_unknown_kind_fails_closed(self):
        canary = {
            "kind": "unknown",
            "expected_hash": hashlib.sha256(b"x").hexdigest(),
        }
        self.assertEqual(prober.score_committed(canary, "x", 0.1), "failed")

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
