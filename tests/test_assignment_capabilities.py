# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unsupported policies must not borrow a known canary's scoring authority."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from eth_account import Account
from eth_account.messages import encode_defunct

from validator import main
from validator.config import Settings
from validator.outbox import AttestationOutbox


def assignment_pair(capability: str, sealed: bool) -> tuple[dict, dict]:
    assignment = {
        "assignment_id": "asg-capability-test",
        "probe_group_id": "prg-capability-test",
        "grid_nonce": "nonce-capability-test",
        "target_worker_id": "worker-capability-test",
        "model": "test-model",
        "modality": "text",
        "capability": capability,
        "scoring_policy_id": "text.batch.unique.v8",
        "canary_kind": "math.add",
        "challenge": {
            "kind": "math.add",
            "prompt": "What is 19 + 23? Reply with only the number.",
            "expected_hash": hashlib.sha256(b"42").hexdigest(),
        },
    }
    prompt_hash = hashlib.sha256(assignment["challenge"]["prompt"].encode()).hexdigest()
    response_hash = hashlib.sha256(b"42").hexdigest()
    evidence = {
        key: assignment[key]
        for key in (
            "assignment_id",
            "probe_group_id",
            "grid_nonce",
            "model",
            "modality",
            "capability",
            "canary_kind",
        )
    }
    evidence.update(
        worker_id=assignment["target_worker_id"],
        prompt_hash=prompt_hash,
        response_hash=response_hash,
    )
    result = {
        **assignment,
        "status": "completed",
        "output_text": "42",
        "probe_latency_ms": 10,
        "prompt_hash": prompt_hash,
        "response_hash": response_hash,
        "evidence_hash": hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    if sealed:
        seal = main._sha256_text(main._canonical(main._assignment_seal_payload(result)))
        result["assignment_seal"] = seal
        assignment = {
            key: assignment[key]
            for key in ("assignment_id", "modality", "capability", "scoring_policy_id")
        }
        assignment.update(sealed=True, assignment_seal=seal)
    return assignment, result


class AssignmentCapabilitiesTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_capability_never_probed_scored_or_signed(self):
        for sealed in (False, True):
            for capability in ("text.responses.future.v1", "text.fidelity.v999"):
                with self.subTest(sealed=sealed, capability=capability):
                    assignment, result = assignment_pair(capability, sealed)
                    with tempfile.TemporaryDirectory() as directory:
                        outbox = AttestationOutbox(
                            str(Path(directory) / "state.sqlite3")
                        )
                        outbox.journal_assignment(assignment)
                        grid = AsyncMock()
                        grid.probe_assignment.return_value = result
                        grid.submit_attestation.return_value = True
                        signer = Account.create()
                        with (
                            patch.object(Settings, "VALIDATOR_WALLET", signer.address),
                            patch.object(
                                Settings, "VALIDATOR_PRIVATE_KEY", signer.key.hex()
                            ),
                            patch.object(
                                main.attest, "sign", wraps=main.attest.sign
                            ) as sign,
                            patch.object(
                                main.prober,
                                "score_committed",
                                wraps=main.prober.score_committed,
                            ) as score,
                        ):
                            accepted = await main._probe_assignment(
                                grid, assignment, outbox
                            )
                        self.assertEqual(accepted, 0)
                        grid.probe_assignment.assert_not_awaited()
                        grid.submit_attestation.assert_not_awaited()
                        sign.assert_not_called()
                        score.assert_not_called()
                        self.assertEqual(outbox.counts(), {"pending": 0, "dead": 0})

    async def test_known_arithmetic_capabilities_still_sign_bound_evidence(self):
        for sealed in (False, True):
            for capability in ("text.basic.v1", "text.reasoning.v1"):
                with self.subTest(sealed=sealed, capability=capability):
                    assignment, result = assignment_pair(capability, sealed)
                    with tempfile.TemporaryDirectory() as directory:
                        outbox = AttestationOutbox(
                            str(Path(directory) / "state.sqlite3")
                        )
                        outbox.journal_assignment(assignment)
                        grid = AsyncMock()
                        grid.probe_assignment.return_value = result
                        grid.submit_attestation.return_value = True
                        signer = Account.create()
                        with (
                            patch.object(Settings, "VALIDATOR_WALLET", signer.address),
                            patch.object(
                                Settings, "VALIDATOR_PRIVATE_KEY", signer.key.hex()
                            ),
                        ):
                            accepted = await main._probe_assignment(
                                grid, assignment, outbox
                            )
                        self.assertEqual(accepted, 1)
                        grid.probe_assignment.assert_awaited_once_with(
                            assignment["assignment_id"]
                        )
                        envelope = grid.submit_attestation.await_args.args[0]
                        self.assertEqual(envelope["payload"]["capability"], capability)
                        self.assertEqual(
                            envelope["payload"]["evidence_hash"],
                            result["evidence_hash"],
                        )
                        self.assertEqual(envelope["payload"]["verdict"], "healthy")
                        recovered = Account.recover_message(
                            encode_defunct(
                                text=main.attest._canonical(envelope["payload"])
                            ),
                            signature=envelope["signature"],
                        )
                        self.assertEqual(recovered, signer.address)

    async def test_missing_or_malformed_capability_skips_without_probe(self):
        for capability in (None, "", [], {}, 1, True):
            with self.subTest(capability=capability):
                assignment, _ = assignment_pair("text.basic.v1", False)
                assignment["capability"] = capability
                grid = AsyncMock()
                with tempfile.TemporaryDirectory() as directory:
                    outbox = AttestationOutbox(str(Path(directory) / "state.sqlite3"))
                    self.assertEqual(
                        await main._probe_assignment(grid, assignment, outbox), 0
                    )
                    grid.probe_assignment.assert_not_awaited()
                    grid.submit_attestation.assert_not_awaited()

    async def test_unknown_policy_retries_and_restart_never_create_a_verdict(self):
        assignment, result = assignment_pair("text.responses.future.v1", True)
        grid = AsyncMock()
        grid.validator_assignments.return_value = [assignment]
        grid.probe_assignment.return_value = result
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "state.sqlite3")
            with (
                patch.object(main.attest, "runtime_capabilities", return_value=[]),
                patch.object(Settings, "ASSIGNMENT_MAX_ATTEMPTS", 2),
                patch.object(main.attest, "sign") as sign,
            ):
                for round_index in range(3):
                    outbox = AttestationOutbox(path)
                    self.assertEqual(
                        await main.probe_round(grid, round_index, outbox), 0
                    )
                self.assertEqual(outbox.assignment_counts(), {"pending": 0, "dead": 1})
                self.assertEqual(outbox.counts(), {"pending": 0, "dead": 0})
                sign.assert_not_called()
            grid.probe_assignment.assert_not_awaited()
            grid.submit_attestation.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
