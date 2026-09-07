import unittest

from validator import update_check


class UpdateCheckTests(unittest.IsolatedAsyncioTestCase):
    async def test_newer_validated_release_is_reported(self):
        async def releases():
            return [
                {"tag_name": "definitely-not-a-release", "draft": False},
                {"tag_name": "v0.2.0-preview", "draft": False},
                {"tag_name": "v9.0.0", "draft": True},
            ]

        notice = await update_check.check_for_update(
            current_tag="v0.1.0-preview.1",
            fetch_releases=releases,
        )

        self.assertIsNotNone(notice)
        self.assertEqual(notice.latest_tag, "v0.2.0-preview")
        self.assertEqual(
            notice.url,
            "https://github.com/AIPowerGrid/grid-validator/releases/tag/v0.2.0-preview",
        )

    async def test_same_or_older_release_is_not_reported(self):
        async def releases():
            return [
                {"tag_name": "v0.1.0-preview.1", "draft": False},
                {"tag_name": "v0.1.0-preview", "draft": False},
                {"tag_name": "v0.0.9", "draft": False},
            ]

        self.assertIsNone(
            await update_check.check_for_update(
                current_tag="v0.1.0-preview.1",
                fetch_releases=releases,
            )
        )

    async def test_stable_release_supersedes_same_version_preview(self):
        async def releases():
            return [{"tag_name": "v0.1.0", "draft": False}]

        notice = await update_check.check_for_update(
            current_tag="v0.1.0-preview.1",
            fetch_releases=releases,
        )

        self.assertEqual(notice.latest_tag, "v0.1.0")

    async def test_network_or_shape_failure_is_nonfatal(self):
        async def failed():
            raise RuntimeError("offline")

        self.assertIsNone(await update_check.check_for_update(current_tag="v0.1.0", fetch_releases=failed))

        async def malformed():
            return [{"tag_name": "../../malicious", "draft": False}]

        self.assertIsNone(await update_check.check_for_update(current_tag="v0.1.0", fetch_releases=malformed))

    async def test_unavailable_is_not_up_to_date(self):
        for payload in (None, {}, "bad", [], [{"tag_name": "v9.0.0", "draft": "false"}], [{"tag_name": "v" + "9" * 5000 + ".0.0", "draft": False}]):
            async def releases():
                return payload
            result = await update_check.inspect_update(
                current_tag="v0.1.0-preview.13", fetch_releases=releases
            )
            self.assertEqual(result.status, "unavailable")

    async def test_stable_channel_never_suggests_prerelease(self):
        async def releases():
            return [
                {"tag_name": "v9.0.0-preview.1", "draft": False},
                {"tag_name": "v0.2.0", "draft": False},
            ]
        result = await update_check.inspect_update(current_tag="v0.1.0", fetch_releases=releases)
        self.assertEqual(result.latest_tag, "v0.2.0")

    async def test_source_build_does_not_contact_github(self):
        async def releases():
            self.fail("source build queried releases")
        result = await update_check.inspect_update(current_tag="v0.1.0-dev", fetch_releases=releases)
        self.assertEqual(result.status, "source_build")


if __name__ == "__main__":
    unittest.main()
