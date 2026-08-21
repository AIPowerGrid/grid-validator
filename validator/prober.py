# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Canary generation + output scoring.

Legacy local canaries retain echo and generated arithmetic for isolated tests.
Grid-issued shared probes additionally support strict JSON, randomized context
retrieval, generated multistep logic, and exact function calls. Expected
answers remain one-way
commitments; this node normalizes and hashes the worker response independently.

Verdicts: "healthy" | "slow" | "failed".
"""

import hashlib
import json
import secrets
import re

from .config import Settings


# v0 runs against /v1/models, which doesn't carry modality, so we can't send a
# text canary to an image/video model (it would always "fail" and produce
# useless evidence). Skip names that look like media models. Layer 3b's
# worker-list endpoint carries real job_types and removes the need for this
# heuristic.
_MEDIA_HINTS = (
    "ltx",
    "stable-diffusion",
    "sd-",
    "sdxl",
    "flux",
    "comfy",
    "video",
    "image",
    "kandinsky",
    "pixart",
    "wan2",
    "hunyuan",
)


def is_text_model(name: str) -> bool:
    n = (name or "").lower()
    return not any(h in n for h in _MEDIA_HINTS)


def _rand_int(minimum: int, maximum: int) -> int:
    """Cryptographic randomness keeps public challenge templates unpredictable."""
    return minimum + secrets.randbelow(maximum - minimum + 1)


def _make_qa_canary() -> dict:
    """Generate a simple, answerable QA canary without committing answer keys."""
    variant = secrets.randbelow(3)
    nonce = secrets.token_hex(4)

    if variant == 0:
        a = _rand_int(11, 89)
        b = _rand_int(11, 89)
        answer = a + b
        prompt = f"What is {a} plus {b}? Reply with only the number."
    elif variant == 1:
        a = _rand_int(50, 99)
        b = _rand_int(10, 44)
        answer = a - b
        prompt = f"What is {a} minus {b}? Reply with only the number."
    else:
        a = _rand_int(6, 19)
        b = _rand_int(6, 19)
        answer = a * b
        prompt = f"What is {a} multiplied by {b}? Reply with only the number."

    return {
        "kind": "qa",
        "nonce": nonce,
        "prompt": prompt,
        "expect": str(answer),
    }


def make_canary(round_index: int) -> dict:
    """Build one canary. Alternates echo/qa by round so both run regularly."""
    if round_index % 2 == 0:
        nonce = secrets.token_hex(4).upper()  # 8 hex chars
        return {
            "kind": "echo",
            "nonce": nonce,
            "prompt": f"Reply with exactly this token and nothing else: {nonce}",
            "expect": nonce,
        }
    return _make_qa_canary()


def _strip_think(text: str) -> str:
    """Reasoning models wrap chain-of-thought in <think>…</think>; judge only the
    actual answer that follows."""
    return re.sub(
        r"<think(?:ing)?>.*?</think(?:ing)?>",
        "",
        text or "",
        flags=re.DOTALL,
    ).strip()


def _strip_wrapping_quotes(text: str) -> str:
    """Allow harmless wrappers around an otherwise exact nonce answer."""
    answer = (text or "").strip()
    wrappers = (("`", "`"), ('"', '"'), ("'", "'"))
    changed = True
    while changed and len(answer) >= 2:
        changed = False
        for left, right in wrappers:
            if answer.startswith(left) and answer.endswith(right):
                answer = answer[1:-1].strip()
                changed = True
                break
    return answer


def _qa_contains_expected(answer: str, expect: str) -> bool:
    if re.fullmatch(r"-?\d+", expect):
        return re.search(rf"(?<![a-z0-9-]){re.escape(expect)}(?![a-z0-9])", answer) is not None
    return expect.lower() in answer.lower()


def score(canary: dict, text: str, latency_s: float) -> str:
    """Grade a worker's reply to a canary."""
    answer = _strip_think(text)
    if not answer:
        return "failed"
    expect = canary["expect"]
    if canary.get("kind") == "echo":
        correct = _strip_wrapping_quotes(answer).lower() == expect.lower()
    else:
        correct = _qa_contains_expected(answer.lower(), expect.lower())
    if not correct:
        return "failed"
    if latency_s > Settings.LATENCY_BUDGET_S:
        return "slow"
    return "healthy"


def score_committed(canary: dict, text: str, latency_s: float) -> str:
    """Grade against Core's one-way expected-answer commitment.

    This keeps the answer itself out of the assignment response while allowing
    the validator to judge the worker output without trusting Core's verdict.
    """
    expected_hash = str(canary.get("expected_hash") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ValueError("canary expected_hash must be a lowercase SHA-256 digest")
    candidate = _normalized_committed_answer(
        str(canary.get("kind") or ""), text, canary.get("tool_calls")
    )
    if candidate is None:
        return "failed"
    actual_hash = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    if not secrets.compare_digest(actual_hash, expected_hash):
        return "failed"
    if latency_s > Settings.LATENCY_BUDGET_S:
        return "slow"
    return "healthy"


def _normalized_tool_call(tool_calls) -> str | None:
    if not isinstance(tool_calls, list) or len(tool_calls) != 1:
        return None
    call = tool_calls[0]
    if not isinstance(call, dict):
        return None
    function = call.get("function")
    if not isinstance(function, dict) or not isinstance(function.get("name"), str):
        return None
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except (TypeError, ValueError):
            return None
    if not isinstance(arguments, dict):
        return None
    return json.dumps(
        {"name": function["name"], "arguments": arguments},
        sort_keys=True,
        separators=(",", ":"),
    )


def _normalized_committed_answer(kind: str, text: str, tool_calls=None) -> str | None:
    answer = _strip_think(text)
    if kind == "tool.call":
        if answer:
            return None
        return _normalized_tool_call(tool_calls)
    if not answer:
        return None
    if kind in ("echo", "context.retrieve", "stop.sequence"):
        candidate = _strip_wrapping_quotes(answer)
        return candidate if candidate and not re.search(r"\s", candidate) else None
    if kind == "json.object":
        try:
            parsed = json.loads(answer)
        except (TypeError, ValueError):
            return None
        if not isinstance(parsed, dict):
            return None
        return json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    if kind.startswith("math.") or kind == "logic.steps":
        numbers = re.findall(r"(?<![a-z0-9-])-?\d+(?![a-z0-9])", answer.lower())
        return numbers[0] if len(numbers) == 1 else None
    return None
