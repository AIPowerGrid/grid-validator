# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

import copy
import hashlib
import json
import unittest

from validator.responses_observation import ObservationError, verify_observation


def fixture():
    return {
        "schema": "responses-logprobs-observation.v1",
        "api_format": "openai-responses",
        "status": "available",
        "reason": "native_logprobs",
        "terminal": "response.completed",
        "quality_eligible": False,
        "comparison_ready": False,
        "events": [
            {
                "sequence_number": 3,
                "item_id": "msg-test",
                "output_index": 1,
                "content_index": 0,
                "visible_prefix_sha256": hashlib.sha256(b"").hexdigest(),
                "delta": "Blue",
                "status": "available",
                "reason": "native_logprobs",
                "positions": [
                    {
                        "token": "Blue",
                        "logprob": -0.25,
                        "bytes": [66, 108, 117, 101],
                        "top_logprobs": [
                            {"token": "Green", "logprob": -2.125, "bytes": None}
                        ],
                    }
                ],
            }
        ],
    }


def read(value, text="Blue"):
    return verify_observation(json.dumps(value).encode(), text)


class ResponsesObservationTests(unittest.TestCase):
    def test_native_values_unchanged(self):
        source = fixture()
        before = copy.deepcopy(source)
        result = read(source)
        self.assertEqual(result.observation, before)
        self.assertEqual(result.position_count, 1)
        self.assertEqual(result.missing_delta_count, 0)
        self.assertEqual(result.status, "available")
        self.assertEqual(source, before)

    def test_partial_coverage_preserved_and_cannot_be_relabelled_complete(self):
        source = fixture()
        missing = copy.deepcopy(source["events"][0])
        missing.update(
            sequence_number=2,
            delta="A ",
            positions=[],
            status="unavailable",
            reason="missing_logprobs",
        )
        source["events"][0]["visible_prefix_sha256"] = hashlib.sha256(b"A ").hexdigest()
        source["events"].insert(0, missing)
        source["status"] = "partial"
        self.assertEqual(read(source, "A Blue").missing_delta_count, 1)
        source["status"] = "available"
        with self.assertRaises(ObservationError):
            read(source, "A Blue")

    def test_absent_probabilities_are_valid_unavailable_not_failed(self):
        source = fixture()
        source.update(status="unavailable", reason="missing_logprobs")
        source["events"][0].update(
            positions=[], status="unavailable", reason="missing_logprobs"
        )
        result = read(source)
        self.assertEqual(result.status, "unavailable")
        self.assertNotIn("verdict", result.observation)

    def test_malformed_and_overflow_probabilities_rejected(self):
        for value in (
            True,
            "-1",
            None,
            1,
            -1_000_001,
            float("nan"),
            float("inf"),
            10**1000,
        ):
            with self.subTest(value_type=type(value).__name__):
                source = fixture()
                source["events"][0]["positions"][0]["logprob"] = value
                with self.assertRaises(ObservationError):
                    read(source)

    def test_bad_frames_rejected(self):
        for key, value in (
            ("sequence_number", True),
            ("sequence_number", -1),
            ("sequence_number", 2**53),
            ("item_id", ""),
            ("item_id", "x" * 129),
            ("content_index", True),
            ("output_index", -1),
            ("visible_prefix_sha256", "0" * 64),
            ("delta", "Wrong"),
            ("positions", [{}]),
            ("extra", "uncommitted"),
        ):
            with self.subTest(key=key):
                source = fixture()
                source["events"][0][key] = value
                with self.assertRaises(ObservationError):
                    read(source)

    def test_forbidden_authority_or_wrong_envelope(self):
        for key, value in (
            ("schema", "other"),
            ("api_format", "openai-chat"),
            ("quality_eligible", True),
            ("comparison_ready", True),
            ("status", "healthy"),
            ("terminal", "response.failed"),
            ("events", []),
            ("extra", "uncommitted"),
        ):
            with self.subTest(key=key):
                source = fixture()
                source[key] = value
                with self.assertRaises(ObservationError):
                    read(source)

    def test_replayed_sequence_and_changed_output_part_rejected(self):
        for change in ({}, {"sequence_number": 4, "item_id": "other"}):
            source = fixture()
            second = copy.deepcopy(source["events"][0])
            second.update(
                visible_prefix_sha256=hashlib.sha256(b"Blue").hexdigest(), **change
            )
            source["events"].append(second)
            with self.assertRaises(ObservationError):
                read(source, "BlueBlue")

    def test_rejects_excess_positions_alternatives_and_bad_bytes(self):
        for variant in ("positions", "alternatives", "bytes", "unicode"):
            source = fixture()
            selected = source["events"][0]["positions"][0]
            if variant == "positions":
                source["events"][0]["positions"] *= 33
            elif variant == "alternatives":
                selected["top_logprobs"] *= 21
            elif variant == "bytes":
                selected["bytes"] = [True]
            else:
                selected["token"] = "\ud800"
            with self.assertRaises(ObservationError):
                read(source)

    def test_malformed_json_duplicate_keys_and_limits(self):
        for raw in (
            b"null",
            b"{",
            b'{"x":1,"x":2}',
            b"x" * 1_048_577,
            b"[" * 2000 + b"]" * 2000,
        ):
            with self.assertRaises(ObservationError):
                verify_observation(raw, "")

    def test_fabricated_but_well_formed_probabilities_are_not_detected(self):
        source = fixture()
        source["events"][0]["positions"][0]["logprob"] = -0.5
        result = read(source)
        self.assertEqual(result.position_count, 1)
        self.assertFalse(result.observation["quality_eligible"])
        # Internal consistency is not an execution proof or anti-forgery check.
        self.assertNotIn("verdict", result.observation)


if __name__ == "__main__":
    unittest.main()
