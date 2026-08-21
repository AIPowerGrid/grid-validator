# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Private local delivery queue for signed validator attestations."""

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _item_id(envelope: dict) -> str:
    assignment_id = str((envelope.get("payload") or {}).get("assignment_id") or "")
    identity = f"assignment:{assignment_id}" if assignment_id else _canonical(envelope)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


class AttestationOutbox:
    def __init__(self, path: str):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            # Private state needs directory traversal for this user only.
            os.chmod(self.path.parent, 0o700)  # nosemgrep: insecure-file-permissions
        except OSError:
            pass
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_attestations (
                    id TEXT PRIMARY KEY,
                    envelope TEXT NOT NULL,
                    created INTEGER NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending'
                )
                """
            )
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def enqueue(self, envelope: dict) -> str:
        body = _canonical(envelope)
        item_id = _item_id(envelope)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO pending_attestations
                    (id, envelope, created, attempts, status)
                VALUES (?, ?, ?, 0, 'pending')
                """,
                (item_id, body, int(time.time())),
            )
        return item_id

    def get_pending(self, item_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, envelope, created, attempts
                FROM pending_attestations
                WHERE id = ? AND status = 'pending'
                """,
                (item_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "envelope": json.loads(row[1]),
            "created": int(row[2]),
            "attempts": int(row[3]),
        }

    def pending(self, limit: int = 100) -> list[dict]:
        safe_limit = max(1, min(int(limit), 1000))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, envelope, created, attempts
                FROM pending_attestations
                WHERE status = 'pending'
                ORDER BY created ASC, id ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            {
                "id": row[0],
                "envelope": json.loads(row[1]),
                "created": int(row[2]),
                "attempts": int(row[3]),
            }
            for row in rows
        ]

    def pending_assignment_ids(self) -> set[str]:
        assignment_ids: set[str] = set()
        for item in self.pending(limit=1000):
            assignment_id = str(
                (item["envelope"].get("payload") or {}).get("assignment_id") or ""
            )
            if assignment_id:
                assignment_ids.add(assignment_id)
        return assignment_ids

    def delivered(self, item_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM pending_attestations WHERE id = ?", (item_id,))

    def failed(self, item_id: str, *, max_attempts: int, max_age_seconds: int) -> bool:
        """Increment failure count and return True when the item is dead-lettered."""
        now = int(time.time())
        with self._connect() as connection:
            row = connection.execute(
                "SELECT created, attempts FROM pending_attestations WHERE id = ?",
                (item_id,),
            ).fetchone()
            if not row:
                return False
            attempts = int(row[1]) + 1
            dead = attempts >= max_attempts or now - int(row[0]) >= max_age_seconds
            connection.execute(
                """
                UPDATE pending_attestations
                SET attempts = ?, status = ?
                WHERE id = ?
                """,
                (attempts, "dead" if dead else "pending", item_id),
            )
        return dead

    def counts(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) FROM pending_attestations GROUP BY status"
            ).fetchall()
        counts = {str(status): int(count) for status, count in rows}
        return {"pending": counts.get("pending", 0), "dead": counts.get("dead", 0)}
