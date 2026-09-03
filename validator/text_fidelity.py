# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Independent scorer for bounded text-model fidelity witnesses."""

from __future__ import annotations

import json
import math
import re
from typing import Any

SCHEMA = "aipg.validator.text.fidelity.challenge.v1"
POLICY_ID = "text.fidelity.v1"
KIND = "text.fidelity"
MAX_DISTRIBUTION_TOKENS = 20
MAX_PROMPT_BYTES = 4_096
REFERENCE_AGREEMENT_MAX = 0.08
CANDIDATE_MATCH_MAX = 0.12
CANDIDATE_ANOMALY_MIN = 0.30


class FidelityEvidenceError(ValueError):
    """Raised when coordinator-provided evidence violates the public contract."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _finite_logprob(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not math.isfinite(result) or result > 0 or result < -1_000_000:
        return None
    return result


def validate_challenge(challenge: Any) -> dict[str, Any]:
    if not isinstance(challenge, dict):
        raise FidelityEvidenceError("challenge is malformed")
    refs = challenge.get("reference_worker_ids")
    request = challenge.get("request")
    comparison = challenge.get("comparison")
    expected_challenge_keys = {
        "schema",
        "kind",
        "prompt",
        "reference_worker_ids",
        "scoring_policy_id",
        "request",
        "comparison",
    }
    expected_request_keys = {
        "max_tokens",
        "temperature",
        "top_p",
        "seed",
        "reasoning_effort",
        "logprobs",
        "top_logprobs",
    }
    valid_references = isinstance(refs, list) and all(
        isinstance(value, str) and 0 < len(value) <= 64 for value in refs
    )
    if (
        set(challenge) != expected_challenge_keys
        or challenge.get("schema") != SCHEMA
        or challenge.get("kind") != KIND
        or challenge.get("scoring_policy_id") != POLICY_ID
        or not isinstance(challenge.get("prompt"), str)
        or not challenge["prompt"]
        or len(challenge["prompt"].encode("utf-8")) > MAX_PROMPT_BYTES
        or not isinstance(refs, list)
        or not 1 <= len(refs) <= 2
        or len(set(refs)) != len(refs)
        or not valid_references
        or not isinstance(request, dict)
        or set(request) != expected_request_keys
        or isinstance(request.get("temperature"), bool)
        or request.get("temperature") != 0
        or isinstance(request.get("top_p"), bool)
        or request.get("top_p") != 1
        or request.get("logprobs") is not True
        or isinstance(request.get("seed"), bool)
        or not isinstance(request.get("seed"), int)
        or not 0 <= request["seed"] < 2**31
        or request.get("reasoning_effort") != "medium"
        or isinstance(request.get("max_tokens"), bool)
        or not isinstance(request.get("max_tokens"), int)
        or not 1 <= request["max_tokens"] <= 32
        or isinstance(request.get("top_logprobs"), bool)
        or not isinstance(request.get("top_logprobs"), int)
        or not 2 <= request["top_logprobs"] <= MAX_DISTRIBUTION_TOKENS
        or comparison
        != {
            "metric": "jensen_shannon_nats.v1",
            "reference_agreement_max": REFERENCE_AGREEMENT_MAX,
            "candidate_match_max": CANDIDATE_MATCH_MAX,
            "candidate_anomaly_min": CANDIDATE_ANOMALY_MIN,
            "negative_requires_references": 2,
        }
    ):
        raise FidelityEvidenceError("challenge is malformed")
    return challenge


def validate_witnesses(
    challenge: dict[str, Any],
    witnesses: Any,
    *,
    target_worker_id: str,
) -> list[dict[str, Any]]:
    challenge = validate_challenge(challenge)
    expected = [
        ("candidate", target_worker_id),
        *(("reference", worker_id) for worker_id in challenge["reference_worker_ids"]),
    ]
    if not isinstance(witnesses, list) or len(witnesses) != len(expected):
        raise FidelityEvidenceError("witness set is malformed")
    normalized = []
    for raw, (role, worker_id) in zip(witnesses, expected, strict=True):
        if not isinstance(raw, dict):
            raise FidelityEvidenceError("witness set is malformed")
        distribution = raw.get("distribution")
        latency_ms = raw.get("latency_ms")
        if (
            raw.get("role") != role
            or raw.get("worker_id") != worker_id
            or not isinstance(raw.get("output_hash"), str)
            or not re.fullmatch(r"[0-9a-fA-F]{64}", raw["output_hash"])
            or not isinstance(raw.get("finish_reason"), str)
            or len(raw["finish_reason"]) > 32
            or isinstance(latency_ms, bool)
            or not isinstance(latency_ms, int)
            or not 0 <= latency_ms <= 3_600_000
            or not isinstance(distribution, list)
            or not distribution
            or len(distribution) > MAX_DISTRIBUTION_TOKENS
        ):
            raise FidelityEvidenceError("witness set is malformed")
        clean = []
        seen = set()
        for item in distribution:
            if not isinstance(item, dict):
                raise FidelityEvidenceError("distribution is malformed")
            token = item.get("token")
            logprob = _finite_logprob(item.get("logprob"))
            if (
                not isinstance(token, str)
                or not token
                or len(token.encode("utf-8")) > 128
                or token in seen
                or logprob is None
            ):
                raise FidelityEvidenceError("distribution is malformed")
            seen.add(token)
            clean.append({"token": token, "logprob": logprob})
        normalized.append(
            {
                "role": role,
                "worker_id": worker_id,
                "output_hash": raw["output_hash"].lower(),
                "finish_reason": raw["finish_reason"],
                "distribution": clean,
                "latency_ms": latency_ms,
            }
        )
    return normalized


def response_commitment(witnesses: list[dict[str, Any]]) -> str:
    return canonical({"witnesses": witnesses})


def _probabilities(distribution: list[dict[str, Any]]) -> dict[str, float]:
    probabilities = {item["token"]: math.exp(item["logprob"]) for item in distribution}
    known = sum(probabilities.values())
    if known > 1:
        probabilities = {token: value / known for token, value in probabilities.items()}
        known = 1.0
    probabilities["\u0000OTHER"] = max(0.0, 1.0 - known)
    return probabilities


def _kl(left: dict[str, float], right: dict[str, float]) -> float:
    total = 0.0
    for token, probability in left.items():
        if probability <= 0:
            continue
        other = right.get(token, 0.0)
        if other <= 0:
            return math.inf
        total += probability * math.log(probability / other)
    return total


def jensen_shannon(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> float:
    p = _probabilities(left)
    q = _probabilities(right)
    keys = set(p) | set(q)
    midpoint = {key: (p.get(key, 0.0) + q.get(key, 0.0)) / 2 for key in keys}
    return (_kl(p, midpoint) + _kl(q, midpoint)) / 2


def score_witnesses(
    challenge: dict[str, Any],
    witnesses: Any,
    *,
    target_worker_id: str,
    latency_budget_s: float,
) -> tuple[str, dict[str, Any]]:
    """Return a conservative verdict; one-reference mismatches are inconclusive."""
    try:
        normalized = validate_witnesses(
            challenge,
            witnesses,
            target_worker_id=target_worker_id,
        )
    except FidelityEvidenceError as exc:
        return "inconclusive", {"reason": str(exc)}
    candidate = normalized[0]
    references = normalized[1:]
    candidate_distances = [
        jensen_shannon(candidate["distribution"], ref["distribution"])
        for ref in references
    ]
    if len(references) == 2:
        reference_distance = jensen_shannon(
            references[0]["distribution"], references[1]["distribution"]
        )
        if reference_distance > REFERENCE_AGREEMENT_MAX:
            return "inconclusive", {
                "reason": "references_disagree",
                "reference_distance": reference_distance,
            }
    else:
        reference_distance = None
    mean_distance = sum(candidate_distances) / len(candidate_distances)
    detail = {
        "reason": "candidate_matches_references",
        "candidate_distance": mean_distance,
        "reference_distance": reference_distance,
        "reference_count": len(references),
    }
    if mean_distance <= CANDIDATE_MATCH_MAX:
        verdict = (
            "slow" if candidate["latency_ms"] > latency_budget_s * 1000 else "healthy"
        )
        return verdict, detail
    if len(references) < 2:
        return "inconclusive", {**detail, "reason": "single_reference_mismatch"}
    if mean_distance >= CANDIDATE_ANOMALY_MIN:
        return "failed", {
            **detail,
            "reason": "candidate_diverges_from_agreeing_references",
        }
    return "inconclusive", {**detail, "reason": "distance_in_gray_zone"}
