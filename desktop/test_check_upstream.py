import unittest
from urllib.request import Request

from check_upstream import RestrictedRedirect, assess, browser_version, expert_version, version_parts


class UpstreamReviewTests(unittest.TestCase):
    def feed(self, version="16.0.1"):
        binary = f"https://dist.torproject.org/torbrowser/{version}/tor-browser-windows-x86_64-portable-{version}.exe"
        return {"version": version, "binary": binary, "sig": binary + ".asc"}

    def links(self, version):
        url = f"https://dist.torproject.org/torbrowser/{version}/tor-expert-bundle-windows-x86_64-{version}.tar.gz"
        return f'<a href="{url}">Download</a><a href="{url}.asc">Signature</a>'

    def test_browser_artifact_matches_release_and_platform(self):
        self.assertEqual(browser_version(self.feed()), "16.0.1")
        for field in ("binary", "sig"):
            data = self.feed()
            data[field] = data[field].replace("x86_64", "i686")
            with self.assertRaises(ValueError):
                browser_version(data)

    def test_foreign_origin_is_rejected(self):
        data = self.feed()
        data["binary"] = data["binary"].replace("dist.torproject.org", "evil.example")
        with self.assertRaises(ValueError):
            browser_version(data)

    def test_expert_ignores_alpha_and_sorts_numerically(self):
        self.assertEqual(expert_version(self.links("16.0.9") + self.links("16.0.10") + self.links("17.0a1")), "16.0.10")

    def test_expert_requires_official_signature_link(self):
        with self.assertRaises(ValueError):
            expert_version(self.links("16.0.1").replace(".tar.gz.asc", ".sig"))

    def test_status_current_new_old_inconsistent(self):
        for browser, expert, expected in (("16.0.1", "16.0.1", "matches-current-pin"),
                                        ("16.0.2", "16.0.2", "update-review-required"),
                                        ("16.0", "16.0", "upstream-older-than-pin"),
                                        ("16.0.2", "16.0.1", "upstream-inconsistent")):
            with self.subTest(expected=expected):
                self.assertEqual(assess("16.0.1", browser, expert)["status"], expected)

    def test_malformed_or_alpha_version_rejected(self):
        for version in (None, "16.0a1", "16/../1", "16", "16.1.1.1.1"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                version_parts(version)

    def test_cross_host_and_insecure_redirects_rejected(self):
        request = Request("https://aus1.torproject.org/feed")
        for target in ("http://aus1.torproject.org/feed", "https://example.com/feed"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                RestrictedRedirect().redirect_request(request, None, 302, "Found", {}, target)


if __name__ == "__main__":
    unittest.main()
