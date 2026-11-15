import unittest
from unittest.mock import patch

from core.update_checker import check_for_update, find_newer_release, version_key


class UpdateCheckerTests(unittest.TestCase):

    def test_final_release_sorts_after_alpha(self):
        self.assertGreater(
            version_key("v0.3.0"),
            version_key("v0.3.0-alpha.5")
        )

    def test_newest_release_ignores_drafts_and_invalid_tags(self):
        releases = [
            {
                "tag_name": "v0.3.0-alpha.6",
                "name": "alpha.6",
                "html_url": "https://example.test/alpha.6",
                "draft": False,
            },
            {
                "tag_name": "v0.3.0-alpha.7",
                "name": "draft alpha.7",
                "html_url": "https://example.test/alpha.7",
                "draft": True,
            },
            {
                "tag_name": "not-a-version",
                "name": "invalid",
                "html_url": "https://example.test/invalid",
                "draft": False,
            },
        ]

        release = find_newer_release("0.3.0-alpha.5", releases)

        self.assertIsNotNone(release)
        self.assertEqual(release.tag_name, "v0.3.0-alpha.6")

    def test_same_version_does_not_trigger_update(self):
        release = find_newer_release(
            "0.3.0-alpha.5",
            [{
                "tag_name": "v0.3.0-alpha.5",
                "html_url": "https://example.test/alpha.5",
                "draft": False,
            }]
        )
        self.assertIsNone(release)

    @patch(
        "core.update_checker._fetch_releases",
        return_value=[{
            "tag_name": "v0.3.0-alpha.6",
            "name": "alpha.6",
            "html_url": "https://example.test/alpha.6",
            "draft": False,
        }]
    )
    def test_newer_release_triggers_notification(self, _fetch_releases):
        release = check_for_update("0.3.0-alpha.5")

        self.assertIsNotNone(release)
        self.assertEqual(release.tag_name, "v0.3.0-alpha.6")


if __name__ == "__main__":
    unittest.main()
