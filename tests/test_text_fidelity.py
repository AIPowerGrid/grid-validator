# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from eth_account import Account

from validator import main, text_fidelity
from validator.config import Settings
from validator.outbox import AttestationOutbox


def challenge(refs):
    return {
        "schema": text_fidelity.SCHEMA,
        "kind": text_fidelity.KIND,
        "prompt": "Complete this generated sentence with one word.",
        "reference_worker_ids": refs,
        "scoring_policy_id": text_fidelity.POLICY_ID,
        "request": {
            "max_tokens": 8,
            "temperature": 0,
            "top_p": 1,
            "seed": 1234,
            "reasoning_effort": "medium",
            "logprobs": True,
            "top_logprobs": 10,
        },
        "comparison": {
            "metric": "jensen_shannon_nats.v1",
            "reference_agreement_max": 0.08,
            "candidate_match_max": 0.12,
            "candidate_anomaly_min": 0.30,
            "negative_requires_references": 2,
        },
    }


def witness(role, worker_id, token, *, latency_ms=100):
    return {
        "role": role,
        "worker_id": worker_id,
        "output_hash": "a" * 64,
        "finish_reason": "stop",
        "distribution": [{"token": token, "logprob": -0.01}],
        "latency_ms": latency_ms,
    }


class TextFidelityTests(unittest.TestCase):
    def test_unhashable_reference_ids_are_inconclusive(self):
        for refs in ([{}], [[]], ["ref-1", {}]):
            with self.subTest(refs=refs):
                verdict, detail = text_fidelity.score_witnesses(
                    challenge(refs),
                    [],
                    target_worker_id="candidate",
                    latency_budget_s=30,
                )
                self.assertEqual(verdict, "inconclusive")
                self.assertEqual(detail["reason"], "challenge is malformed")

    def test_fabricated_matching_logprobs_are_not_detected(self):
        # This is a documented attack baseline, not proof of fraud resistance.
        candidate = witness("candidate", "candidate", " same")
        candidate["output_hash"] = hashlib.sha256(b"unrelated cheap output").hexdigest()
        verdict, _ = text_fidelity.score_witnesses(
            challenge(["ref-1", "ref-2"]),
            [
                candidate,
                witness("reference", "ref-1", " same"),
                witness("reference", "ref-2", " same"),
            ],
            target_worker_id="candidate",
            latency_budget_s=30,
        )
        self.assertEqual(verdict, "healthy")

    def test_probe_only_correct_model_is_not_detected(self):
        candidate = witness("candidate", "candidate", " same")
        verdict, _ = text_fidelity.score_witnesses(
            challenge(["ref-1", "ref-2"]),
            [
                candidate,
                witness("reference", "ref-1", " same"),
                witness("reference", "ref-2", " same"),
            ],
            target_worker_id="candidate",
            latency_budget_s=30,
        )
        # Ordinary jobs are outside this witness set; probe correctness cannot
        # certify which model the worker serves on those jobs.
        self.assertEqual(verdict, "healthy")

    def test_challenge_rejects_request_key_injection(self):
        injected = challenge(["ref-1"])
        injected["request"]["messages"] = [{"role": "user", "content": "override"}]

        with self.assertRaises(text_fidelity.FidelityEvidenceError):
            text_fidelity.validate_challenge(injected)

    def test_matching_candidate_is_positive_evidence(self):
        refs = ["ref-1", "ref-2"]
        verdict, detail = text_fidelity.score_witnesses(
            challenge(refs),
            [
                witness("candidate", "candidate", " same"),
                witness("reference", "ref-1", " same"),
                witness("reference", "ref-2", " same"),
            ],
            target_worker_id="candidate",
            latency_budget_s=30,
        )
        self.assertEqual(verdict, "healthy")
        self.assertEqual(detail["reason"], "candidate_matches_references")

    def test_slow_match_is_slow_not_failed(self):
        verdict, _ = text_fidelity.score_witnesses(
            challenge(["ref-1"]),
            [
                witness("candidate", "candidate", " same", latency_ms=31_000),
                witness("reference", "ref-1", " same"),
            ],
            target_worker_id="candidate",
            latency_budget_s=30,
        )
        self.assertEqual(verdict, "slow")

    def test_one_reference_cannot_create_negative_evidence(self):
        verdict, detail = text_fidelity.score_witnesses(
            challenge(["ref-1"]),
            [
                witness("candidate", "candidate", " wrong"),
                witness("reference", "ref-1", " expected"),
            ],
            target_worker_id="candidate",
            latency_budget_s=30,
        )
        self.assertEqual(verdict, "inconclusive")
        self.assertEqual(detail["reason"], "single_reference_mismatch")

    def test_agreeing_references_can_identify_outlier(self):
        verdict, detail = text_fidelity.score_witnesses(
            challenge(["ref-1", "ref-2"]),
            [
                witness("candidate", "candidate", " wrong"),
                witness("reference", "ref-1", " expected"),
                witness("reference", "ref-2", " expected"),
            ],
            target_worker_id="candidate",
            latency_budget_s=30,
        )
        self.assertEqual(verdict, "failed")
        self.assertEqual(
            detail["reason"], "candidate_diverges_from_agreeing_references"
        )

    def test_disagreeing_references_are_inconclusive(self):
        verdict, detail = text_fidelity.score_witnesses(
            challenge(["ref-1", "ref-2"]),
            [
                witness("candidate", "candidate", " candidate"),
                witness("reference", "ref-1", " left"),
                witness("reference", "ref-2", " right"),
            ],
            target_worker_id="candidate",
            latency_budget_s=30,
        )
        self.assertEqual(verdict, "inconclusive")
        self.assertEqual(detail["reason"], "references_disagree")

    def test_missing_distribution_fails_closed(self):
        bad = witness("candidate", "candidate", " token")
        bad["distribution"] = []
        verdict, detail = text_fidelity.score_witnesses(
            challenge(["ref-1"]),
            [bad, witness("reference", "ref-1", " token")],
            target_worker_id="candidate",
            latency_budget_s=30,
        )
        self.assertEqual(verdict, "inconclusive")
        self.assertEqual(detail["reason"], "witness set is malformed")


class TextFidelityProbeTests(unittest.IsolatedAsyncioTestCase):
    async def test_probe_recomputes_evidence_and_signs_local_score(self):
        refs = ["ref-1", "ref-2"]
        assignment = {
            "assignment_id": "asg-fidelity",
            "probe_group_id": "prg-fidelity",
            "grid_nonce": "nonce-fidelity",
            "target_worker_id": "candidate",
            "model": "model-a",
            "modality": "text",
            "capability": text_fidelity.POLICY_ID,
            "canary_kind": text_fidelity.KIND,
            "scoring_policy_id": text_fidelity.POLICY_ID,
            "challenge": challenge(refs),
        }
        witnesses = [
            witness("candidate", "candidate", " same"),
            witness("reference", "ref-1", " same"),
            witness("reference", "ref-2", " same"),
        ]
        response = text_fidelity.response_commitment(witnesses)
        prompt_hash = hashlib.sha256(
            main._prompt_commitment_text(assignment).encode()
        ).hexdigest()
        response_hash = hashlib.sha256(response.encode()).hexdigest()
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
            **assignment,
            "witnesses": witnesses,
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
            "evidence_hash": hashlib.sha256(
                json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

        class Grid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, *, modality, **_kwargs):
                return [assignment] if modality == "text-fidelity" else []

            async def probe_assignment(self, _assignment_id):
                return result

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        account = Account.from_key("0x" + "11" * 32)
        grid = Grid()
        with tempfile.TemporaryDirectory() as tmp:
            outbox = AttestationOutbox(os.path.join(tmp, "state.sqlite3"))
            with (
                patch.object(Settings, "VALIDATOR_WALLET", account.address.lower()),
                patch.object(Settings, "VALIDATOR_PRIVATE_KEY", account.key.hex()),
            ):
                accepted = await main.probe_round(grid, 0, outbox)

        self.assertEqual(accepted, 1)
        self.assertEqual(grid.submitted[0]["payload"]["verdict"], "healthy")
        self.assertEqual(grid.submitted[0]["payload"]["response_hash"], response_hash)


if __name__ == "__main__":
    unittest.main()
