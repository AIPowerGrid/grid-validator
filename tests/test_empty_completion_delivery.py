# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Committed empty text is evidence; missing or unverifiable responses are not."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from eth_account import Account
from eth_account.messages import encode_defunct

from validator import main
from validator.config import Settings
from validator.outbox import AttestationOutbox


def empty_pair(sealed=False, finish="stop"):
    assignment = {
        "assignment_id": "asg-empty-test",
        "probe_group_id": "prg-empty-test",
        "grid_nonce": "nonce-empty-test",
        "target_worker_id": "worker-empty-test",
        "model": "test-model",
        "modality": "text",
        "capability": "text.stop_sequence.v1",
        "canary_kind": "stop.sequence",
        "scoring_policy_id": "text.batch.unique.v8",
        "challenge": {
            "kind": "stop.sequence",
            "prompt": "Reply with PREFIX<STOP_TEST>TAIL.",
            "expected_hash": hashlib.sha256(b"PREFIX").hexdigest(),
            "stop": ["<STOP_TEST>"],
        },
    }
    evidence = {key: assignment[key] for key in (
        "assignment_id", "probe_group_id", "grid_nonce", "model", "modality",
        "capability", "canary_kind",
    )}
    evidence.update(
        worker_id=assignment["target_worker_id"],
        prompt_hash=hashlib.sha256(assignment["challenge"]["prompt"].encode()).hexdigest(),
        response_hash=hashlib.sha256(b"").hexdigest(),
    )
    result = {
        **assignment, "status": "completed", "output_text": "",
        "reasoning_text": None, "tool_calls": None, "tool_chain": None,
        "finish_reason": finish, "probe_latency_ms": 25, "grid": {},
        "prompt_hash": evidence["prompt_hash"], "response_hash": evidence["response_hash"],
        "evidence_hash": hashlib.sha256(main._canonical(evidence).encode()).hexdigest(),
    }
    if sealed:
        seal = main._sha256_text(main._canonical(main._assignment_seal_payload(result)))
        result["assignment_seal"] = seal
        assignment = {key: assignment[key] for key in (
            "assignment_id", "modality", "capability", "scoring_policy_id",
        )}
        assignment.update(sealed=True, assignment_seal=seal)
    return assignment, result


class EmptyCompletionDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_verified_empty_without_worker_error_flag_is_delivered(self):
        for sealed in (False, True):
            for finish in ("stop", "length"):
                with self.subTest(sealed=sealed, finish=finish), tempfile.TemporaryDirectory() as folder:
                    assignment, result = empty_pair(sealed, finish)
                    outbox = AttestationOutbox(str(Path(folder) / "state.sqlite3"))
                    outbox.journal_assignment(assignment)
                    grid = AsyncMock()
                    grid.probe_assignment.return_value = result
                    grid.submit_attestation.return_value = True
                    account = Account.create()
                    with (
                        patch.object(Settings, "VALIDATOR_WALLET", account.address.lower()),
                        patch.object(Settings, "VALIDATOR_PRIVATE_KEY", account.key.hex()),
                    ):
                        self.assertEqual(await main._probe_assignment(grid, assignment, outbox), 1)
                    envelope = grid.submit_attestation.call_args.args[0]
                    self.assertEqual(envelope["payload"]["verdict"], "failed")
                    self.assertEqual(envelope["payload"]["response_hash"], hashlib.sha256(b"").hexdigest())
                    signer = Account.recover_message(
                        encode_defunct(text=main._canonical(envelope["payload"])),
                        signature=envelope["signature"],
                    )
                    self.assertEqual(signer, account.address)
                    self.assertEqual(outbox.pending_assignments(), [])
                    self.assertEqual(outbox.pending(), [])

    async def test_missing_or_tampered_empty_evidence_never_signed(self):
        mutations = (
            {"response_hash": "0" * 64}, {"evidence_hash": "0" * 64},
            {"prompt_hash": "0" * 64}, {"target_worker_id": "other-worker"},
            {"grid_nonce": "other-nonce"}, {"status": "pending"},
            {"status": "unavailable"}, {"output_text": None},
            {"assignment_seal": "0" * 64},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                assignment, result = empty_pair(sealed=True)
                result.update(mutation)
                outbox = AttestationOutbox(str(Path(folder) / "state.sqlite3"))
                outbox.journal_assignment(assignment)
                grid = AsyncMock()
                grid.probe_assignment.return_value = result
                with patch.object(main.attest, "sign") as sign:
                    self.assertEqual(await main._probe_assignment(grid, assignment, outbox), 0)
                    sign.assert_not_called()
                grid.submit_attestation.assert_not_called()
                self.assertEqual(len(outbox.pending_assignments()), 1)
                self.assertEqual(outbox.pending(), [])

    async def test_empty_failure_delivery_retries_same_envelope_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            assignment, result = empty_pair(sealed=True)
            path = str(Path(folder) / "state.sqlite3")
            outbox = AttestationOutbox(path)
            outbox.journal_assignment(assignment)
            grid = AsyncMock()
            grid.probe_assignment.return_value = result
            grid.submit_attestation.return_value = False
            account = Account.create()
            with (
                patch.object(Settings, "VALIDATOR_WALLET", account.address.lower()),
                patch.object(Settings, "VALIDATOR_PRIVATE_KEY", account.key.hex()),
            ):
                self.assertEqual(await main._probe_assignment(grid, assignment, outbox), 0)
            grid.submit_attestation.assert_awaited_once()
            first = grid.submit_attestation.call_args.args[0]
            self.assertEqual(outbox.pending_assignments(), [])
            self.assertEqual(len(outbox.pending()), 1)
            grid.submit_attestation.return_value = True
            reopened = AttestationOutbox(path)
            with patch.object(main.attest, "sign") as sign:
                self.assertEqual(await main._flush_outbox(grid, reopened), 1)
                sign.assert_not_called()
            self.assertEqual(grid.submit_attestation.call_args.args[0], first)
            grid.probe_assignment.assert_awaited_once()
            self.assertEqual(reopened.pending(), [])


if __name__ == "__main__":
    unittest.main()
