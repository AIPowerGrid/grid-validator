import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from eth_account import Account

from validator import main
from validator.config import Settings
from validator.outbox import AttestationOutbox

TEST_ACCOUNT = Account.from_key("0x" + "11" * 32)


class ProbeRoundTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.outbox = AttestationOutbox(os.path.join(self.tmp.name, "state.sqlite3"))

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _assignment():
        return {
            "assignment_id": "asg_1",
            "probe_group_id": "prg_1",
            "grid_nonce": "grid-nonce-1",
            "target_worker_id": "worker-1",
            "model": "qwen3-32b",
            "modality": "text",
            "capability": "text.basic.v1",
            "canary_kind": "math.add",
            "challenge": {
                "kind": "math.add",
                "prompt": "What is 19 + 23? Reply with only the number.",
                "expected_hash": hashlib.sha256(b"42").hexdigest(),
            },
        }

    @classmethod
    def _result(cls, **overrides):
        assignment = cls._assignment()
        prompt_hash = hashlib.sha256(
            assignment["challenge"]["prompt"].encode("utf-8")
        ).hexdigest()
        response_hash = hashlib.sha256(b"42").hexdigest()
        evidence = {
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
        }
        evidence_hash = hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        result = {
            "status": "completed",
            "output_text": "42",
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "target_worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
            "evidence_hash": evidence_hash,
        }
        result.update(overrides)
        return result

    @staticmethod
    def _image_assignment():
        return {
            "assignment_id": "asg_image_1",
            "probe_group_id": "prg_image_1",
            "grid_nonce": "grid-image-nonce-1",
            "target_worker_id": "worker-candidate",
            "model": "deterministic-image-model",
            "modality": "image",
            "capability": "image.fidelity.v1",
            "canary_kind": "image.fidelity",
            "challenge": {
                "schema": "aipg.validator.media.challenge.v1",
                "kind": "image.fidelity",
                "modality": "image",
                "scoring_policy_id": "image.fidelity.v1",
                "prompt": "private randomized prompt",
                "recipe_root": "0x" + "12" * 32,
                "parameters": {
                    "seed": 123456,
                    "width": 512,
                    "height": 512,
                    "steps": 12,
                    "n": 1,
                },
                "reference_worker_ids": ["worker-reference-a", "worker-reference-b"],
            },
        }

    @classmethod
    def _image_result(cls):
        assignment = cls._image_assignment()
        witnesses = [
            {
                "role": "candidate",
                "worker_id": "worker-candidate",
                "url": "https://media.example/candidate.webp?secret=one",
                "sha256": "a" * 64,
                "bytes": 1000,
                "content_type": "image/webp",
                "latency_ms": 1200,
            },
            {
                "role": "reference",
                "worker_id": "worker-reference-a",
                "url": "https://media.example/reference-a.webp?secret=two",
                "sha256": "b" * 64,
                "bytes": 1001,
                "content_type": "image/webp",
                "latency_ms": 1100,
            },
            {
                "role": "reference",
                "worker_id": "worker-reference-b",
                "url": "https://media.example/reference-b.webp?secret=three",
                "sha256": "c" * 64,
                "bytes": 1002,
                "content_type": "image/webp",
                "latency_ms": 1150,
            },
        ]
        prompt_hash = hashlib.sha256(
            main._prompt_commitment_text(assignment).encode()
        ).hexdigest()
        response_text = main._media_response_commitment({"witnesses": witnesses})
        assert response_text is not None
        response_hash = hashlib.sha256(response_text.encode()).hexdigest()
        evidence = {
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
        }
        return {
            "status": "completed",
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "target_worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "witnesses": witnesses,
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
            "evidence_hash": hashlib.sha256(
                json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

    @staticmethod
    def _video_assignment():
        return {
            "assignment_id": "asg_video_1",
            "probe_group_id": "prg_video_1",
            "grid_nonce": "grid-video-nonce-1",
            "target_worker_id": "worker-video-candidate",
            "model": "video-model",
            "modality": "video",
            "capability": "video.contract.v1",
            "canary_kind": "video.contract",
            "challenge": {
                "schema": "aipg.validator.media.challenge.v1",
                "kind": "video.contract",
                "modality": "video",
                "scoring_policy_id": "video.contract.v1",
                "prompt": "private randomized moving subject",
                "recipe_root": "0x" + "34" * 32,
                "parameters": {
                    "seed": 987654,
                    "width": 512,
                    "height": 512,
                    "frame_count": 16,
                    "fps": 8.0,
                    "duration_s": 2.0,
                    "motion_required": True,
                },
                "reference_worker_ids": [],
            },
        }

    @classmethod
    def _video_result(cls):
        assignment = cls._video_assignment()
        witnesses = [{
            "role": "candidate",
            "worker_id": assignment["target_worker_id"],
            "url": "https://media.example/candidate.mp4?secret=video",
            "sha256": "d" * 64,
            "bytes": 4096,
            "content_type": "video/mp4",
            "latency_ms": 2400,
        }]
        prompt_hash = hashlib.sha256(
            main._prompt_commitment_text(assignment).encode()
        ).hexdigest()
        response_text = main._media_response_commitment({"witnesses": witnesses})
        assert response_text is not None
        response_hash = hashlib.sha256(response_text.encode()).hexdigest()
        evidence = {
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
        }
        return {
            "status": "completed",
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "target_worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "witnesses": witnesses,
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
            "evidence_hash": hashlib.sha256(
                json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

    async def test_assignment_probe_submits_grid_bound_attestation(self):
        class FakeGrid:
            def __init__(self):
                self.probed = []
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [ProbeRoundTests._assignment()]

            async def probe_assignment(self, assignment_id):
                self.probed.append(assignment_id)
                return ProbeRoundTests._result()

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

            async def list_workers(self):
                raise AssertionError("assignments should be preferred over inventory")

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
        ):
            attempted = await main.probe_round(grid, 0, self.outbox)

        self.assertEqual(attempted, 1)
        self.assertEqual(grid.probed, ["asg_1"])
        payload = grid.submitted[0]["payload"]
        self.assertEqual(payload["assignment_source"], "grid")
        self.assertEqual(payload["assignment_id"], "asg_1")
        self.assertEqual(payload["probe_group_id"], "prg_1")
        self.assertEqual(payload["grid_nonce"], "grid-nonce-1")
        self.assertEqual(payload["worker_id"], "worker-1")
        self.assertEqual(payload["capability"], "text.basic.v1")
        self.assertEqual(payload["verdict"], "healthy")
        self.assertEqual(payload["prompt_hash"], ProbeRoundTests._result()["prompt_hash"])
        self.assertEqual(payload["response_hash"], ProbeRoundTests._result()["response_hash"])
        self.assertEqual(payload["evidence_hash"], ProbeRoundTests._result()["evidence_hash"])
        self.assertIsNotNone(grid.submitted[0]["signature"])

    async def test_assignment_probe_rejects_mismatched_core_commitment(self):
        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [ProbeRoundTests._assignment()]

            async def probe_assignment(self, _assignment_id):
                return ProbeRoundTests._result(response_hash="f" * 64)

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        self.assertEqual(await main.probe_round(grid, 0, self.outbox), 0)
        self.assertEqual(grid.submitted, [])

    async def test_unavailable_local_scorer_submits_no_worker_verdict(self):
        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [ProbeRoundTests._assignment()]

            async def probe_assignment(self, _assignment_id):
                return ProbeRoundTests._result()

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with patch.object(
            main.prober,
            "score_committed",
            side_effect=main.prober.ScorerUnavailable("local scorer unavailable"),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 0)

        self.assertEqual(grid.submitted, [])
        self.assertEqual(self.outbox.counts(), {"pending": 0, "dead": 0})

    async def test_assignment_probe_scores_and_signs_witnessed_tool_call(self):
        assignment = {
            **self._assignment(),
            "capability": "text.tool_call.v1",
            "canary_kind": "tool.call",
        }
        tool_calls = [{
            "id": "call_opaque", "type": "function",
            "function": {
                "name": "record_c", "arguments": '{"token_b":"A1","count_a":7}',
            },
        }]
        expected = json.dumps(
            {"arguments": {"count_a": 7, "token_b": "A1"}, "name": "record_c"},
            sort_keys=True, separators=(",", ":"),
        )
        assignment["challenge"] = {
            "kind": "tool.call",
            "prompt": "Call record_c exactly once.",
            "expected_hash": hashlib.sha256(expected.encode()).hexdigest(),
        }
        response_commitment = json.dumps(
            {"text": "", "tool_calls": tool_calls},
            sort_keys=True, separators=(",", ":"),
        )
        prompt_hash = hashlib.sha256(assignment["challenge"]["prompt"].encode()).hexdigest()
        response_hash = hashlib.sha256(response_commitment.encode()).hexdigest()
        evidence = {
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
        }
        result = {
            "status": "completed", "output_text": "", "tool_calls": tool_calls,
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "target_worker_id": assignment["target_worker_id"],
            "model": assignment["model"], "modality": assignment["modality"],
            "capability": assignment["capability"], "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash, "response_hash": response_hash,
            "evidence_hash": hashlib.sha256(
                json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [assignment]

            async def probe_assignment(self, _assignment_id):
                return result

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 1)

        payload = grid.submitted[0]["payload"]
        self.assertEqual(payload["capability"], "text.tool_call.v1")
        self.assertEqual(payload["verdict"], "healthy")
        self.assertEqual(payload["response_hash"], response_hash)

    async def test_assignment_probe_scores_and_signs_two_step_tool_chain(self):
        assignment = {
            **self._assignment(),
            "capability": "text.tool_chain.v1",
            "canary_kind": "tool.chain",
        }
        expected_calls = [
            {"arguments": {"key_a": "K1"}, "name": "lookup_a"},
            {"arguments": {"token_c": "T1", "total_b": 42}, "name": "submit_b"},
        ]
        chain = [
            {"text": "", "finish_reason": "tool_calls", "tool_calls": [{
                "id": "call_1", "type": "function",
                "function": {"name": "lookup_a", "arguments": '{"key_a":"K1"}'},
            }]},
            {"text": "", "finish_reason": "tool_calls", "tool_calls": [{
                "id": "call_2", "type": "function",
                "function": {
                    "name": "submit_b",
                    "arguments": '{"total_b":42,"token_c":"T1"}',
                },
            }]},
        ]
        expected = json.dumps(expected_calls, sort_keys=True, separators=(",", ":"))
        assignment["challenge"] = {
            "kind": "tool.chain",
            "prompt": "Call lookup_a and then submit_b.",
            "expected_hash": hashlib.sha256(expected.encode()).hexdigest(),
            "steps": [
                {"expected_hash": "a" * 64, "tools": [], "tool_choice": {}},
                {
                    "expected_hash": "b" * 64,
                    "tool_result": {"left": 19, "right": 23, "token": "T1"},
                    "tools": [],
                    "tool_choice": {},
                },
            ],
        }
        response_commitment = main._response_commitment_text(
            assignment, {"output_text": "", "tool_chain": chain}
        )
        prompt_hash = hashlib.sha256(
            main._prompt_commitment_text(assignment).encode()
        ).hexdigest()
        response_hash = hashlib.sha256(response_commitment.encode()).hexdigest()
        evidence = {
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
        }
        result = {
            "status": "completed",
            "output_text": "",
            "tool_calls": chain[-1]["tool_calls"],
            "tool_chain": chain,
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "target_worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
            "evidence_hash": hashlib.sha256(
                json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [assignment]

            async def probe_assignment(self, _assignment_id):
                return result

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 1)

        payload = grid.submitted[0]["payload"]
        self.assertEqual(payload["capability"], "text.tool_chain.v1")
        self.assertEqual(payload["verdict"], "healthy")
        self.assertEqual(payload["response_hash"], response_hash)

    async def test_assignment_probe_scores_and_commits_token_limit_evidence(self):
        token = "limit_marker"
        max_tokens = 192
        assignment = {
            **self._assignment(),
            "capability": "text.token_limit.v1",
            "canary_kind": "token.limit",
        }
        assignment["challenge"] = {
            "kind": "token.limit",
            "prompt": f"Repeat {token} until the generation limit stops you.",
            "expected_hash": hashlib.sha256(token.encode()).hexdigest(),
            "max_tokens": max_tokens,
        }
        pieces = []
        while main.prober._count_tokens(" ".join(pieces)) < max_tokens // 2:
            pieces.append(token)
        output_text = " ".join(pieces)
        result = {
            "status": "completed",
            "output_text": output_text,
            "reasoning_text": "",
            "finish_reason": "length",
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "target_worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
        }
        response_commitment = main._response_commitment_text(assignment, result)
        prompt_hash = hashlib.sha256(
            main._prompt_commitment_text(assignment).encode()
        ).hexdigest()
        response_hash = hashlib.sha256(response_commitment.encode()).hexdigest()
        evidence = {
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
        }
        result.update({
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
            "evidence_hash": hashlib.sha256(
                json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        })

        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [assignment]

            async def probe_assignment(self, _assignment_id):
                return result

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 1)

        payload = grid.submitted[0]["payload"]
        self.assertEqual(payload["capability"], "text.token_limit.v1")
        self.assertEqual(payload["verdict"], "healthy")
        self.assertEqual(payload["response_hash"], response_hash)
        self.assertEqual(main._assignment_canary(assignment)["max_tokens"], max_tokens)

    async def test_reasoning_only_token_limit_is_failed_evidence_not_a_skip(self):
        token = "visible_marker"
        assignment = {
            **self._assignment(),
            "capability": "text.token_limit.v1",
            "canary_kind": "token.limit",
        }
        assignment["challenge"] = {
            "kind": "token.limit",
            "prompt": f"Repeat {token} until the generation limit stops you.",
            "expected_hash": hashlib.sha256(token.encode()).hexdigest(),
            "max_tokens": 192,
        }
        result = {
            "status": "completed",
            "output_text": "",
            "reasoning_text": "hidden reasoning consumed the output budget",
            "finish_reason": "length",
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "target_worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
        }
        response_commitment = main._response_commitment_text(assignment, result)
        prompt_hash = hashlib.sha256(
            main._prompt_commitment_text(assignment).encode()
        ).hexdigest()
        response_hash = hashlib.sha256(response_commitment.encode()).hexdigest()
        evidence = {
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
        }
        result.update(
            {
                "prompt_hash": prompt_hash,
                "response_hash": response_hash,
                "evidence_hash": hashlib.sha256(
                    json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
            }
        )

        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [assignment]

            async def probe_assignment(self, _assignment_id):
                return result

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 1)

        self.assertEqual(grid.submitted[0]["payload"]["verdict"], "failed")

    def test_assignment_canary_preserves_code_hidden_inputs_for_local_scoring(self):
        assignment = {
            **self._assignment(),
            "capability": "text.code.v1",
            "canary_kind": "code.function",
        }
        assignment["challenge"] = {
            "kind": "code.function",
            "prompt": "Write the requested function.",
            "expected_hash": "a" * 64,
            "function_name": "transform_a1b2c3d4",
            "test_inputs": [-2, 0, 7],
        }

        canary = main._assignment_canary(assignment)

        self.assertEqual(canary["function_name"], "transform_a1b2c3d4")
        self.assertEqual(canary["test_inputs"], [-2, 0, 7])

    def test_token_limit_commitment_binds_reasoning_and_finish_reason(self):
        assignment = {
            "canary_kind": "token.limit",
            "challenge": {"kind": "token.limit"},
        }
        base = {
            "output_text": "ABC ABC",
            "reasoning_text": "private synthetic reasoning",
            "finish_reason": "length",
        }
        committed = main._response_commitment_text(assignment, base)

        self.assertNotEqual(
            committed,
            main._response_commitment_text(
                assignment, {**base, "reasoning_text": "changed"}
            ),
        )
        self.assertNotEqual(
            committed,
            main._response_commitment_text(
                assignment, {**base, "finish_reason": "stop"}
            ),
        )

    async def test_target_worker_empty_completion_is_signed_as_failed_evidence(self):
        assignment = self._assignment()
        prompt_hash = hashlib.sha256(
            assignment["challenge"]["prompt"].encode()
        ).hexdigest()
        response_hash = hashlib.sha256(b"").hexdigest()
        evidence = {
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
        }
        result = {
            **self._result(),
            "output_text": "",
            "grid": {"probe_failed": True},
            "response_hash": response_hash,
            "evidence_hash": hashlib.sha256(
                json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [assignment]

            async def probe_assignment(self, _assignment_id):
                return result

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 1)

        self.assertEqual(grid.submitted[0]["payload"]["verdict"], "failed")

    async def test_assignment_probe_rejects_wrong_target_binding(self):
        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [ProbeRoundTests._assignment()]

            async def probe_assignment(self, _assignment_id):
                return ProbeRoundTests._result(target_worker_id="worker-2")

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        self.assertEqual(await main.probe_round(grid, 0, self.outbox), 0)
        self.assertEqual(grid.submitted, [])

    async def test_image_assignment_signs_hashes_without_witness_urls(self):
        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, *, modality, **_kwargs):
                return [ProbeRoundTests._image_assignment()] if modality == "image" else []

            async def probe_assignment(self, _assignment_id):
                return ProbeRoundTests._image_result()

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
            patch.object(Settings, "MEDIA_ALLOWED_ORIGINS", ("https://media.example",)),
            patch.object(
                main.attest,
                "runtime_capabilities",
                return_value=["text.instruction.v1", "image.fidelity.v1"],
            ),
            patch.object(
                main.media_prober,
                "score_image_fidelity_witnesses",
                new=AsyncMock(return_value=("healthy", {"policy": "image.fidelity.v1"})),
            ),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 1)

        payload = grid.submitted[0]["payload"]
        self.assertEqual(payload["modality"], "image")
        self.assertEqual(payload["capability"], "image.fidelity.v1")
        self.assertEqual(payload["verdict"], "healthy")
        self.assertEqual(payload["latency_ms"], 1200)
        rendered = json.dumps(grid.submitted[0])
        self.assertNotIn("media.example", rendered)
        self.assertNotIn("secret=", rendered)

    async def test_inconclusive_image_assignment_is_not_attested(self):
        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, *, modality, **_kwargs):
                return [ProbeRoundTests._image_assignment()] if modality == "image" else []

            async def probe_assignment(self, _assignment_id):
                return ProbeRoundTests._image_result()

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "MEDIA_ALLOWED_ORIGINS", ("https://media.example",)),
            patch.object(
                main.attest,
                "runtime_capabilities",
                return_value=["image.fidelity.v1"],
            ),
            patch.object(
                main.media_prober,
                "score_image_fidelity_witnesses",
                new=AsyncMock(
                    return_value=("inconclusive", {"reason": "references-disagree"})
                ),
            ),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 0)

        self.assertEqual(grid.submitted, [])
        self.assertEqual(self.outbox.counts(), {"pending": 0, "dead": 0})

    async def test_video_assignment_signs_committed_witness_without_url(self):
        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, *, modality, **_kwargs):
                return [ProbeRoundTests._video_assignment()] if modality == "video" else []

            async def probe_assignment(self, _assignment_id):
                return ProbeRoundTests._video_result()

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
            patch.object(Settings, "MEDIA_ALLOWED_ORIGINS", ("https://media.example",)),
            patch.object(
                main.attest,
                "runtime_capabilities",
                return_value=["text.instruction.v1", "video.contract.v1"],
            ),
            patch.object(
                main.media_prober,
                "score_video_witnesses",
                new=AsyncMock(return_value=("healthy", {"policy": "video.contract.v1"})),
            ),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 1)

        payload = grid.submitted[0]["payload"]
        self.assertEqual(payload["modality"], "video")
        self.assertEqual(payload["capability"], "video.contract.v1")
        self.assertEqual(payload["verdict"], "healthy")
        self.assertEqual(payload["latency_ms"], 2400)
        rendered = json.dumps(grid.submitted[0])
        self.assertNotIn("media.example", rendered)
        self.assertNotIn("secret=", rendered)

    async def test_no_assignment_fails_closed_without_inventory_or_model_fallback(self):
        class FakeGrid:
            async def validator_assignments(self, **_kwargs):
                return []

        self.assertEqual(await main.probe_round(FakeGrid(), 0, self.outbox), 0)

    async def test_failed_delivery_is_replayed_without_reprobing(self):
        class FakeGrid:
            def __init__(self):
                self.probes = 0
                self.submissions = 0

            async def validator_assignments(self, **_kwargs):
                return [ProbeRoundTests._assignment()] if self.probes == 0 else []

            async def probe_assignment(self, _assignment_id):
                self.probes += 1
                return ProbeRoundTests._result()

            async def submit_attestation(self, _envelope):
                self.submissions += 1
                return self.submissions > 1

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 0)
            self.assertEqual(self.outbox.counts(), {"pending": 1, "dead": 0})
            self.assertEqual(await main.probe_round(grid, 1, self.outbox), 1)

        self.assertEqual(grid.probes, 1)
        self.assertEqual(grid.submissions, 2)
        self.assertEqual(self.outbox.counts(), {"pending": 0, "dead": 0})

    async def test_completed_probe_is_recovered_from_assignment_journal_after_restart(self):
        class FakeGrid:
            def __init__(self):
                self.assignment_polls = 0
                self.probes = 0
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                self.assignment_polls += 1
                return [ProbeRoundTests._assignment()] if self.assignment_polls == 1 else []

            async def probe_assignment(self, _assignment_id):
                self.probes += 1
                if self.probes == 1:
                    return None
                return ProbeRoundTests._result(
                    replayed=True,
                    probe_latency_ms=12_345,
                )

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 0)
            self.assertEqual(
                self.outbox.assignment_counts(),
                {"pending": 1, "dead": 0},
            )

            reopened = AttestationOutbox(self.outbox.path)
            self.assertEqual(await main.probe_round(grid, 1, reopened), 1)

        self.assertEqual(grid.probes, 2)
        self.assertEqual(grid.submitted[0]["payload"]["latency_ms"], 12_345)
        self.assertEqual(reopened.assignment_counts(), {"pending": 0, "dead": 0})
        self.assertEqual(reopened.counts(), {"pending": 0, "dead": 0})

    async def test_one_assignment_exception_does_not_cancel_siblings(self):
        first = self._assignment()
        second = {**self._assignment(), "assignment_id": "asg_2", "grid_nonce": "nonce-2"}

        class FakeGrid:
            async def validator_assignments(self, **_kwargs):
                return [first, second]

        async def fake_probe(_grid, assignment, outbox):
            if assignment["assignment_id"] == "asg_1":
                raise RuntimeError("synthetic probe crash")
            outbox.promote_assignment(
                "asg_2",
                {"payload": {"assignment_id": "asg_2"}, "signature": "0x1234"},
            )
            return 1

        with patch.object(main, "_probe_assignment", side_effect=fake_probe):
            self.assertEqual(await main.probe_round(FakeGrid(), 0, self.outbox), 1)

        self.assertEqual(self.outbox.journaled_assignment_ids(), {"asg_1"})
        self.assertEqual(self.outbox.pending_assignment_ids(), {"asg_2"})

    async def test_replayed_result_without_original_latency_is_not_signed(self):
        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [ProbeRoundTests._assignment()]

            async def probe_assignment(self, _assignment_id):
                return ProbeRoundTests._result(replayed=True)

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        self.assertEqual(await main.probe_round(grid, 0, self.outbox), 0)
        self.assertEqual(grid.submitted, [])
        self.assertEqual(self.outbox.assignment_counts(), {"pending": 1, "dead": 0})


class RunStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_raises_when_required_stake_contract_is_missing(self):
        with (
            patch("validator.config.Settings.validate", return_value=None),
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
            patch.object(Settings, "REQUIRE_STAKE", True),
            patch(
                "validator.staking.assert_eligible",
                side_effect=main.staking.NotDeployed("missing staking contract"),
            ),
            patch("validator.main.GridClient", side_effect=AssertionError("grid should not start")),
        ):
            with self.assertRaisesRegex(RuntimeError, "Stake contract not deployed"):
                await main.run()

    async def test_run_raises_required_stake_runtime_failures_before_grid_start(self):
        with (
            patch("validator.config.Settings.validate", return_value=None),
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
            patch.object(Settings, "REQUIRE_STAKE", True),
            patch(
                "validator.staking.assert_eligible",
                side_effect=RuntimeError("Insufficient stake"),
            ),
            patch("validator.main.GridClient", side_effect=AssertionError("grid should not start")),
        ):
            with self.assertRaisesRegex(RuntimeError, "Insufficient stake"):
                await main.run()


class MainModuleEntrypointTests(unittest.TestCase):
    def test_python_m_validator_main_reports_config_errors_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, ".env")
            with open(env_path, "w", encoding="utf-8") as fh:
                fh.write(
                    "GRID_API_URL=http://127.0.0.1:1\n"
                    "VALIDATOR_API_KEY=grid-key\n"
                    "VALIDATOR_REQUIRE_STAKE=false\n"
                    "PROBE_INTERVAL_S=abc\n"
                )
            env = os.environ.copy()
            env["VALIDATOR_ENV"] = env_path
            result = subprocess.run(
                [sys.executable, "-m", "validator.main"],
                cwd=os.getcwd(),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Startup:", result.stdout)
        self.assertIn("PROBE_INTERVAL_S must be an integer", result.stdout)
        self.assertNotIn("Traceback", result.stdout)


if __name__ == "__main__":
    unittest.main()
