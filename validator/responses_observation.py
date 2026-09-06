# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Independent qualification reader; not an assignment scorer or capability.

No Core imports, network, signing, configuration, or economic effects. A valid
envelope proves internal transport consistency, not that its probabilities are
honest or its visible prefix is the complete conditional model context.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

MAX_BYTES = 1_048_576
SCHEMA = "responses-logprobs-observation.v1"


class ObservationError(ValueError):
    """Unusable evidence; callers must not convert this into worker failure."""


@dataclass(frozen=True)
class VerifiedObservation:
    status: str
    text_sha256: str
    observation_sha256: str
    position_count: int
    missing_delta_count: int
    observation: dict[str, Any]


def _require(condition: bool) -> None:
    if not condition:
        raise ObservationError("invalid Responses observation")


def _string(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        raise ObservationError("invalid Responses observation")
    _require(len(value) <= limit)
    _require(len(value.encode("utf-8")) <= limit)
    return value


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _position(value: Any, selected: bool) -> None:
    _require(isinstance(value, dict))
    allowed = {"token", "logprob", "bytes"} | ({"top_logprobs"} if selected else set())
    _require(set(value) <= allowed and {"token", "logprob"} <= set(value))
    _string(value["token"], 128)
    probability = value["logprob"]
    _require(
        type(probability) in (int, float)
        and -1_000_000 <= probability <= 0
        and math.isfinite(probability)
    )
    raw_bytes = value.get("bytes")
    _require(
        raw_bytes is None
        or (
            isinstance(raw_bytes, list)
            and len(raw_bytes) <= 128
            and all(type(byte) is int and 0 <= byte <= 255 for byte in raw_bytes)
        )
    )
    if selected:
        top = value.get("top_logprobs")
        _require(isinstance(top, list) and len(top) <= 20)
        for alternative in top:
            _position(alternative, False)


def verify_observation(raw: bytes, full_text: str) -> VerifiedObservation:
    """Validate serialized Core observations without trusting its coverage label.

    The surrounding assignment protocol must separately verify identity, nonce,
    freshness and its evidence commitment. This helper grants none of those.
    """
    try:
        _require(isinstance(raw, bytes) and len(raw) <= MAX_BYTES)
        text = _string(full_text, 16_384)
        observation = json.loads(raw, object_pairs_hook=_object)
        _require(
            isinstance(observation, dict)
            and set(observation)
            == {
                "schema",
                "api_format",
                "status",
                "reason",
                "terminal",
                "quality_eligible",
                "comparison_ready",
                "events",
            }
        )
        _require(
            observation["schema"] == SCHEMA
            and observation["api_format"] == "openai-responses"
        )
        _require(
            observation["quality_eligible"] is False
            and observation["comparison_ready"] is False
        )
        _require(observation["status"] in ("available", "partial", "unavailable"))
        _string(observation["reason"], 64)
        _require(
            observation["terminal"]
            in (
                None,
                "response.completed",
                "response.incomplete",
                "response.failed",
                "error",
            )
        )
        events = observation["events"]
        _require(isinstance(events, list) and len(events) <= 128)
        prefix = ""
        previous_sequence = -1
        part = None
        positions = missing = 0
        for event in events:
            _require(
                isinstance(event, dict)
                and set(event)
                == {
                    "sequence_number",
                    "item_id",
                    "output_index",
                    "content_index",
                    "visible_prefix_sha256",
                    "delta",
                    "positions",
                    "status",
                    "reason",
                }
            )
            sequence = event["sequence_number"]
            _require(type(sequence) is int and previous_sequence < sequence < 2**53)
            previous_sequence = sequence
            item = _string(event["item_id"], 128)
            _require(bool(item))
            indices = event["output_index"], event["content_index"]
            _require(all(type(index) is int and 0 <= index < 1024 for index in indices))
            current = (item, *indices)
            _require(part is None or part == current)
            part = current
            _require(
                event["visible_prefix_sha256"]
                == hashlib.sha256(prefix.encode("utf-8")).hexdigest()
            )
            prefix += _string(event["delta"], 16_384)
            _string(prefix, 16_384)
            items = event["positions"]
            _require(isinstance(items, list))
            positions += len(items)
            _require(positions <= 32)
            for position in items:
                _position(position, True)
            if items:
                _require(
                    event["status"] == "available"
                    and event["reason"] == "native_logprobs"
                )
            else:
                missing += 1
                _require(
                    event["status"] == "unavailable"
                    and event["reason"]
                    in (
                        "missing_logprobs",
                        "malformed_logprobs_or_event",
                        "event_too_large_or_invalid",
                    )
                )
        _require(prefix == text)
        status = observation["status"]
        if status != "unavailable":
            _require(positions > 0 and observation["terminal"] == "response.completed")
            _require(observation["reason"] == "native_logprobs")
            _require(status == ("partial" if missing else "available"))
        canonical = json.dumps(
            observation, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        return VerifiedObservation(
            status=status,
            text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            observation_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            position_count=positions,
            missing_delta_count=missing,
            observation=observation,
        )
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeError,
        RecursionError,
        OverflowError,
    ) as exc:
        raise ObservationError("invalid Responses observation") from exc
