import json
import os
import sqlite3
import tempfile
import time
import unittest

from validator.outbox import AttestationOutbox


class AttestationOutboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "validator", "state.sqlite3")
        self.outbox = AttestationOutbox(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _envelope():
        return {"payload": {"assignment_id": "asg_1"}, "signature": "0x1234"}

    def test_persists_across_reopen_and_enqueue_is_idempotent(self):
        item_id = self.outbox.enqueue(self._envelope())
        self.assertEqual(self.outbox.enqueue(self._envelope()), item_id)

        changed_signature = self._envelope()
        changed_signature["signature"] = "0xabcd"
        self.assertEqual(self.outbox.enqueue(changed_signature), item_id)

        reopened = AttestationOutbox(self.path)
        self.assertEqual(reopened.counts(), {"pending": 1, "dead": 0})
        self.assertEqual(reopened.pending()[0]["envelope"], self._envelope())
        self.assertEqual(reopened.get_pending(item_id)["envelope"], self._envelope())
        self.assertEqual(reopened.pending_assignment_ids(), {"asg_1"})

    def test_delivered_removes_item(self):
        item_id = self.outbox.enqueue(self._envelope())
        self.outbox.delivered(item_id)
        self.assertEqual(self.outbox.counts(), {"pending": 0, "dead": 0})

    def test_failure_dead_letters_at_attempt_limit(self):
        item_id = self.outbox.enqueue(self._envelope())
        self.assertFalse(
            self.outbox.failed(item_id, max_attempts=2, max_age_seconds=3600)
        )
        self.assertTrue(
            self.outbox.failed(item_id, max_attempts=2, max_age_seconds=3600)
        )
        self.assertEqual(self.outbox.counts(), {"pending": 0, "dead": 1})

    def test_failure_dead_letters_expired_item(self):
        item_id = self.outbox.enqueue(self._envelope())
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "UPDATE pending_attestations SET created = ? WHERE id = ?",
                (int(time.time()) - 3601, item_id),
            )
        self.assertTrue(
            self.outbox.failed(item_id, max_attempts=20, max_age_seconds=3600)
        )
        self.assertEqual(self.outbox.counts(), {"pending": 0, "dead": 1})

    def test_database_contains_no_private_key_field(self):
        self.outbox.enqueue(self._envelope())
        with sqlite3.connect(self.path) as connection:
            envelope = connection.execute(
                "SELECT envelope FROM pending_attestations"
            ).fetchone()[0]
        self.assertEqual(json.loads(envelope), self._envelope())
        self.assertNotIn("private", envelope.lower())

    def test_assignment_journal_survives_restart_and_promotes_atomically(self):
        assignment = {
            "assignment_id": "asg_1",
            "grid_nonce": "nonce-1",
            "challenge": {"prompt": "synthetic prompt"},
        }
        self.outbox.journal_assignment(assignment)

        reopened = AttestationOutbox(self.path)
        self.assertEqual(reopened.pending_assignments(), [assignment])
        self.assertEqual(reopened.assignment_counts(), {"pending": 1, "dead": 0})

        changed = {**assignment, "grid_nonce": "mutated"}
        reopened.journal_assignment(changed)
        self.assertEqual(reopened.pending_assignments(), [assignment])

        item_id = reopened.promote_assignment("asg_1", self._envelope())
        promoted = AttestationOutbox(self.path)
        self.assertEqual(promoted.pending_assignments(), [])
        self.assertEqual(promoted.assignment_counts(), {"pending": 0, "dead": 0})
        self.assertEqual(promoted.get_pending(item_id)["envelope"], self._envelope())

    def test_promotion_requires_matching_pending_assignment(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.outbox.promote_assignment("asg_other", self._envelope())
        with self.assertRaisesRegex(ValueError, "not pending"):
            self.outbox.promote_assignment("asg_1", self._envelope())

    def test_dead_letters_require_explicit_retry(self):
        assignment = {"assignment_id": "asg_1", "challenge": {}}
        self.outbox.journal_assignment(assignment)
        self.assertTrue(
            self.outbox.assignment_failed(
                "asg_1",
                max_attempts=1,
                max_age_seconds=3600,
            )
        )
        item_id = self.outbox.enqueue(self._envelope())
        self.assertTrue(
            self.outbox.failed(item_id, max_attempts=1, max_age_seconds=3600)
        )
        self.assertEqual(self.outbox.pending_assignments(), [])
        self.assertEqual(self.outbox.get_pending(item_id), None)
        dead = self.outbox.dead_letters()
        self.assertEqual(dead["assignments"][0]["assignment_id"], "asg_1")
        self.assertEqual(dead["attestations"][0]["assignment_id"], "asg_1")
        self.assertEqual(dead["assignments"][0]["attempts"], 1)

        revived = self.outbox.retry_dead()
        self.assertEqual(revived, {"attestations": 1, "assignments": 1})
        self.assertEqual(self.outbox.pending_assignments(), [assignment])
        self.assertIsNotNone(self.outbox.get_pending(item_id))

    def test_assignment_journal_rejects_missing_id_and_oversize(self):
        with self.assertRaisesRegex(ValueError, "assignment_id"):
            self.outbox.journal_assignment({"challenge": {}})
        with self.assertRaisesRegex(ValueError, "journal limit"):
            self.outbox.journal_assignment(
                {"assignment_id": "asg_large", "challenge": {"prompt": "x" * (1024 * 1024)}}
            )


if __name__ == "__main__":
    unittest.main()
