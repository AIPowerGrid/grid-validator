# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Private local journal for assignments and signed attestation delivery."""

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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_assignments (
                    assignment_id TEXT PRIMARY KEY,
                    assignment TEXT NOT NULL,
                    created INTEGER NOT NULL,
                    updated INTEGER NOT NULL,
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

    def journal_assignment(self, assignment: dict) -> str:
        """Persist an assignment before its targeted probe is requested."""
        assignment_id = str(assignment.get("assignment_id") or "")
        if not assignment_id:
            raise ValueError("assignment_id is required")
        body = _canonical(assignment)
        if len(body.encode("utf-8")) > 1024 * 1024:
            raise ValueError("assignment exceeds the local journal limit")
        now = int(time.time())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO pending_assignments
                    (assignment_id, assignment, created, updated, attempts, status)
                VALUES (?, ?, ?, ?, 0, 'pending')
                """,
                (assignment_id, body, now, now),
            )
        return assignment_id

    def pending_assignments(self, limit: int = 100) -> list[dict]:
        safe_limit = max(1, min(int(limit), 1000))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT assignment
                FROM pending_assignments
                WHERE status = 'pending'
                ORDER BY created ASC, assignment_id ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def journaled_assignment_ids(self, *, include_dead: bool = False) -> set[str]:
        with self._connect() as connection:
            if include_dead:
                rows = connection.execute(
                    "SELECT assignment_id FROM pending_assignments"
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT assignment_id
                    FROM pending_assignments
                    WHERE status = 'pending'
                    """
                ).fetchall()
        return {str(row[0]) for row in rows}

    def promote_assignment(self, assignment_id: str, envelope: dict) -> str:
        """Atomically replace a journaled assignment with its signed envelope."""
        envelope_assignment_id = str(
            (envelope.get("payload") or {}).get("assignment_id") or ""
        )
        if not assignment_id or envelope_assignment_id != assignment_id:
            raise ValueError("signed envelope does not match the journaled assignment")
        body = _canonical(envelope)
        item_id = _item_id(envelope)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            journaled = connection.execute(
                """
                SELECT 1
                FROM pending_assignments
                WHERE assignment_id = ? AND status = 'pending'
                """,
                (assignment_id,),
            ).fetchone()
            if journaled is None:
                raise ValueError("assignment is not pending in the local journal")
            connection.execute(
                """
                INSERT OR IGNORE INTO pending_attestations
                    (id, envelope, created, attempts, status)
                VALUES (?, ?, ?, 0, 'pending')
                """,
                (item_id, body, int(time.time())),
            )
            connection.execute(
                "DELETE FROM pending_assignments WHERE assignment_id = ?",
                (assignment_id,),
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

    def tracked_attestation_assignment_ids(self) -> set[str]:
        """Return assignment IDs with pending or dead signed evidence."""
        assignment_ids: set[str] = set()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT envelope FROM pending_attestations"
            ).fetchall()
        for row in rows:
            assignment_id = str(
                (json.loads(row[0]).get("payload") or {}).get("assignment_id") or ""
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

    def assignment_failed(
        self,
        assignment_id: str,
        *,
        max_attempts: int,
        max_age_seconds: int,
    ) -> bool:
        """Increment a probe failure and dead-letter exhausted assignment work."""
        now = int(time.time())
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT created, attempts
                FROM pending_assignments
                WHERE assignment_id = ? AND status = 'pending'
                """,
                (assignment_id,),
            ).fetchone()
            if not row:
                return False
            attempts = int(row[1]) + 1
            dead = attempts >= max_attempts or now - int(row[0]) >= max_age_seconds
            connection.execute(
                """
                UPDATE pending_assignments
                SET attempts = ?, updated = ?, status = ?
                WHERE assignment_id = ?
                """,
                (attempts, now, "dead" if dead else "pending", assignment_id),
            )
        return dead

    def retry_dead(self, kind: str = "all") -> dict[str, int]:
        """Explicitly revive dead letters after an operator reviews the cause."""
        if kind not in {"all", "attestations", "assignments"}:
            raise ValueError("kind must be all, attestations, or assignments")
        now = int(time.time())
        revived = {"attestations": 0, "assignments": 0}
        with self._connect() as connection:
            if kind in {"all", "attestations"}:
                result = connection.execute(
                    """
                    UPDATE pending_attestations
                    SET attempts = 0, created = ?, status = 'pending'
                    WHERE status = 'dead'
                    """,
                    (now,),
                )
                revived["attestations"] = max(0, int(result.rowcount or 0))
            if kind in {"all", "assignments"}:
                result = connection.execute(
                    """
                    UPDATE pending_assignments
                    SET attempts = 0, created = ?, updated = ?, status = 'pending'
                    WHERE status = 'dead'
                    """,
                    (now, now),
                )
                revived["assignments"] = max(0, int(result.rowcount or 0))
        return revived

    def dead_letters(self, limit: int = 20) -> dict[str, list[dict]]:
        """Return bounded local identifiers for operator review, never secrets."""
        safe_limit = max(1, min(int(limit), 100))
        now = int(time.time())
        with self._connect() as connection:
            attestation_rows = connection.execute(
                """
                SELECT id, envelope, created, attempts
                FROM pending_attestations
                WHERE status = 'dead'
                ORDER BY created ASC, id ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
            assignment_rows = connection.execute(
                """
                SELECT assignment_id, created, attempts
                FROM pending_assignments
                WHERE status = 'dead'
                ORDER BY created ASC, assignment_id ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        attestations = []
        for item_id, envelope, created, attempts in attestation_rows:
            assignment_id = str(
                (json.loads(envelope).get("payload") or {}).get("assignment_id") or ""
            )
            attestations.append(
                {
                    "id": str(item_id),
                    "assignment_id": assignment_id,
                    "attempts": int(attempts),
                    "age_seconds": max(0, now - int(created)),
                }
            )
        assignments = [
            {
                "assignment_id": str(assignment_id),
                "attempts": int(attempts),
                "age_seconds": max(0, now - int(created)),
            }
            for assignment_id, created, attempts in assignment_rows
        ]
        return {"attestations": attestations, "assignments": assignments}

    def counts(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) FROM pending_attestations GROUP BY status"
            ).fetchall()
        counts = {str(status): int(count) for status, count in rows}
        return {"pending": counts.get("pending", 0), "dead": counts.get("dead", 0)}

    def assignment_counts(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) FROM pending_assignments GROUP BY status"
            ).fetchall()
        counts = {str(status): int(count) for status, count in rows}
        return {"pending": counts.get("pending", 0), "dead": counts.get("dead", 0)}
