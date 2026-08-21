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


if __name__ == "__main__":
    unittest.main()
