"""Regression tests for bridge input, route verification and session ownership."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from connect_core import ConnectError, TorSession, bridge_lines, configuration

OBFS4 = "obfs4 192.0.2.2:443 " + "a" * 40 + " cert=YWJj iat-mode=0"
WEBTUNNEL = "webtunnel [2001:db8::2]:443 " + "b" * 40 + " url=https://bridge.example/path ver=0.0.1"


class BridgeTests(unittest.TestCase):
    def test_transport_lines_and_optional_prefix(self):
        self.assertEqual(bridge_lines("Bridge " + OBFS4 + "\n\n" + WEBTUNNEL), [OBFS4, WEBTUNNEL])

    def test_rejects_config_injection_and_nontransport_relays(self):
        for line in [OBFS4 + "\nSocksPort 0.0.0.0:9050", OBFS4 + " # hi", OBFS4 + "\\", OBFS4 + '"',
                     "192.0.2.2:443 " + "a" * 40, WEBTUNNEL.replace("https://", "http://"),
                     WEBTUNNEL.replace("bridge.example", "user:pass@bridge.example")]:
            with self.subTest(line=line), self.assertRaises(ValueError):
                bridge_lines(line)

    def test_rejects_duplicate_options_invalid_address_and_limits(self):
        for line in [OBFS4 + " cert=YWJj", OBFS4.replace(":443", ":65536"),
                     OBFS4.replace("192.0.2.2", "example.com"), OBFS4.replace("iat-mode=0", "iat-mode=9"),
                     "\n".join([OBFS4] * 9), "", "x" * 16001]:
            with self.subTest(line=line[:100]), self.assertRaises(ValueError):
                bridge_lines(line)

    def test_custom_config_is_bridge_only_and_loopback_only(self):
        content = configuration(Path("runtime"), Path("state"), "custom", WEBTUNNEL)
        for required in ["UseBridges 1", "SocksPort 127.0.0.1:auto IsolateSOCKSAuth", "ControlPort 127.0.0.1:auto",
                         "CookieAuthentication 1", "__OwningControllerProcess", "Bridge " + WEBTUNNEL]:
            self.assertIn(required, content)
        self.assertNotIn("0.0.0.0", content)
        self.assertNotIn("DisableNetwork 0", content)

    def test_no_direct_transport_mode(self):
        with self.assertRaises(ValueError):
            configuration(Path("runtime"), Path("state"), "direct", "")


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="usafe-unit-")
        self.addCleanup(self.folder.cleanup)
        self.session = TorSession(Path(self.folder.name) / "runtime", Path(self.folder.name) / "state")
        self.session.process = Mock()
        self.session.process.poll.return_value = None
        self.session.socks_port = 12345

    @patch("connect_core.subprocess.run")
    def test_https_check_uses_remote_dns_and_explicit_proxy(self, run):
        run.return_value = Mock(returncode=0, stdout=b'{"IsTor":true,"IP":"192.0.2.9"}')
        self.assertTrue(self.session.check_connection())
        args = run.call_args.args[0]
        self.assertEqual(args[1], "--disable")
        self.assertIn("socks5h://127.0.0.1:12345", args)
        self.assertIn("--fail", args)
        self.assertEqual(args[args.index("--noproxy") + 1], "")
        self.assertNotIn("--insecure", args)
        self.assertEqual(run.call_count, 1)

    @patch("connect_core.subprocess.run")
    def test_wrong_route_never_reports_success(self, run):
        for payload in [b'{"IsTor":false}', b'{"IsTor":"true"}', b'not json']:
            self.session.verified = True
            run.return_value = Mock(returncode=0, stdout=payload)
            with self.assertRaises(RuntimeError):
                self.session.check_connection()
            self.assertFalse(self.session.verified)

    @patch("connect_core.subprocess.run")
    def test_timeout_clears_previous_verification_without_fallback(self, run):
        self.session.verified = True
        run.side_effect = subprocess.TimeoutExpired("curl", 40)
        with self.assertRaises(ConnectError) as raised:
            self.session.check_connection()
        self.assertEqual(raised.exception.code, "route_check")
        self.assertFalse(self.session.verified)
        self.assertEqual(run.call_count, 1)

    @patch("connect_core.subprocess.run")
    def test_stop_during_check_cannot_report_connected(self, run):
        def finish(*args, **kwargs):
            self.session.process = None
            self.session.cancelled.set()
            return Mock(returncode=0, stdout=b'{"IsTor":true}')
        run.side_effect = finish
        with self.assertRaises(RuntimeError):
            self.session.check_connection()
        self.assertFalse(self.session.verified)

    def test_second_session_cannot_lock_or_remove_first_session_files(self):
        self.session.process = None
        self.session._acquire_instance()
        config = self.session.state_dir / "torrc"
        config.write_text("private bridge")
        second = TorSession(self.session.runtime, self.session.state_dir)
        with self.assertRaises(RuntimeError):
            second._acquire_instance()
        second.stop()
        self.assertTrue(config.exists())
        self.session.stop()
        self.assertFalse(config.exists())
        third = TorSession(self.session.runtime, self.session.state_dir)
        third._acquire_instance()
        third.stop()

    @patch("connect_core.subprocess.Popen")
    def test_cancel_before_start_never_spawns_tor(self, popen):
        self.session.process = None
        self.session.cancelled.set()
        with self.assertRaises(RuntimeError):
            self.session.start()
        popen.assert_not_called()

    def test_modified_runtime_is_rejected(self):
        runtime = self.session.runtime
        (runtime / "tor").mkdir(parents=True)
        (runtime / "verified-files.json").write_text(json.dumps({"files": {"tor/tor.exe": "0" * 64}}))
        (runtime / "tor/tor.exe").write_bytes(b"altered binary")
        with self.assertRaises(RuntimeError):
            self.session._verify_runtime()

    @patch("connect_core.subprocess.Popen")
    def test_browser_cannot_open_without_verified_connection(self, popen):
        with self.assertRaises(RuntimeError):
            self.session.launch_browser(Path("firefox.exe"))
        popen.assert_not_called()

    @patch.dict("connect_core.os.environ", {"TOR_CONTROL_PASSWD": "inherited-secret", "TOR_SOCKS_PORT": "9999"})
    @patch("connect_core.subprocess.Popen")
    def test_browser_uses_this_session_and_drops_inherited_tor_settings(self, popen):
        browser = Path(self.folder.name) / "Tor Browser/Browser/firefox.exe"
        (browser.parent / "TorBrowser").mkdir(parents=True)
        browser.touch()
        self.session.verified = True
        self.session.control_port = 23456
        self.session.launch_browser(browser)
        env = popen.call_args.kwargs["env"]
        self.assertEqual(env["TOR_SOCKS_PORT"], "12345")
        self.assertEqual(env["TOR_CONTROL_PORT"], "23456")
        self.assertEqual(env["TOR_SKIP_LAUNCH"], "1")
        self.assertEqual(env["TOR_SOCKS_HOST"], "127.0.0.1")
        self.assertNotIn("TOR_CONTROL_PASSWD", env)
        self.assertIn("https://www.argodelta.com/tools/usafe/", popen.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
