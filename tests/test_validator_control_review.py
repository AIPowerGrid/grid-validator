import importlib.util
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "verify-validator-control.py"
SPEC = importlib.util.spec_from_file_location("validator_control_review", SCRIPT)
assert SPEC and SPEC.loader
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)

VALIDATOR_ID = "val_" + "a" * 32


def status(
    *, registration="active", online=True, version="v0.1.0-preview.13", **updates
):
    payload = {
        "schema": "aipg.validator.public-status.v1",
        "validator_id": VALIDATOR_ID,
        "registration_status": registration,
        "online": online,
        "software_version": version,
        "software_version_supported": True,
        "economic_effect": "none",
    }
    payload.update(updates)
    return payload


class Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class SequenceFetcher:
    def __init__(self, payloads):
        self.payloads = iter(payloads)
        self.last = None

    def __call__(self, _api_url, _validator_id):
        try:
            self.last = next(self.payloads)
        except StopIteration:
            pass
        if isinstance(self.last, Exception):
            raise self.last
        return self.last


class ValidatorControlReviewTests(unittest.TestCase):
    def test_observes_same_identity_suspend_and_resume(self):
        clock = Clock()
        lines = []
        review.verify_control(
            VALIDATOR_ID,
            api_url="https://api.example.test",
            timeout_seconds=30,
            interval_seconds=1,
            fetcher=SequenceFetcher(
                [
                    status(),
                    status(),
                    status(registration="suspended", online=False),
                    status(registration="suspended", online=False),
                    status(),
                ]
            ),
            monotonic=clock.monotonic,
            sleep=clock.sleep,
            emit=lines.append,
        )
        text = "\n".join(lines)
        self.assertIn("READY", text)
        self.assertIn("signed suspension", text)
        self.assertIn("PASS", text)
        self.assertIn("not independent operation", text)
        self.assertNotIn("private", text.lower())

    def test_rejects_copied_or_changed_identity(self):
        clock = Clock()
        with self.assertRaisesRegex(review.ControlCheckError, "different validator ID"):
            review.verify_control(
                VALIDATOR_ID,
                api_url="https://api.example.test",
                timeout_seconds=30,
                interval_seconds=1,
                fetcher=SequenceFetcher(
                    [status(validator_id="val_" + "b" * 32)]
                ),
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )

    def test_semantic_violation_during_poll_fails_without_retry(self):
        clock = Clock()
        fetcher = SequenceFetcher(
            [status(), status(validator_id="val_" + "b" * 32), status()]
        )
        with self.assertRaisesRegex(review.ControlCheckError, "different validator ID"):
            review.verify_control(
                VALIDATOR_ID,
                api_url="https://api.example.test",
                timeout_seconds=30,
                interval_seconds=1,
                fetcher=fetcher,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
                emit=lambda _line: None,
            )
        self.assertEqual(clock.now, 1)

    def test_transient_status_failure_is_bounded_and_recoverable(self):
        clock = Clock()
        review.verify_control(
            VALIDATOR_ID,
            api_url="https://api.example.test",
            timeout_seconds=30,
            interval_seconds=1,
            fetcher=SequenceFetcher(
                [
                    status(),
                    review.PublicStatusUnavailable("temporary"),
                    status(registration="suspended", online=False),
                    status(),
                ]
            ),
            monotonic=clock.monotonic,
            sleep=clock.sleep,
            emit=lambda _line: None,
        )

    def test_requires_supported_non_economic_active_start(self):
        cases = [
            (status(software_version_supported=False), "frozen supported"),
            (status(economic_effect="routing"), "economic_effect=none"),
            (
                status(registration="suspended", online=False),
                "active and online",
            ),
        ]
        for payload, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                review.ControlCheckError, message
            ):
                review.verify_control(
                    VALIDATOR_ID,
                    api_url="https://api.example.test",
                    timeout_seconds=30,
                    interval_seconds=1,
                    fetcher=SequenceFetcher([payload]),
                )

    def test_times_out_without_signed_suspension(self):
        clock = Clock()
        with self.assertRaisesRegex(review.ControlCheckError, "signed suspension"):
            review.verify_control(
                VALIDATOR_ID,
                api_url="https://api.example.test",
                timeout_seconds=30,
                interval_seconds=10,
                fetcher=SequenceFetcher([status()]),
                monotonic=clock.monotonic,
                sleep=clock.sleep,
                emit=lambda _line: None,
            )

    def test_bounds_ids_urls_and_polling(self):
        with self.assertRaisesRegex(review.ControlCheckError, "validator ID"):
            review.verify_control(
                "val_not-valid",
                api_url="https://api.example.test",
                timeout_seconds=30,
                interval_seconds=1,
            )
        with self.assertRaises(review.argparse.ArgumentTypeError):
            review._validated_api_url("http://api.example.test")
        self.assertEqual(
            review._validated_api_url("http://127.0.0.1:7010/"),
            "http://127.0.0.1:7010",
        )
        with self.assertRaisesRegex(review.ControlCheckError, "timeout"):
            review.verify_control(
                VALIDATOR_ID,
                api_url="https://api.example.test",
                timeout_seconds=5,
                interval_seconds=1,
            )

    def test_cli_failure_is_concise(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = review.main(["val_not-valid"])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("FAIL validator ID", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
