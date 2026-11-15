"""Recovery decisions and data minimization, independent of a live Tor network."""
import json
import unittest

from connect_core import ConnectError
from connect_help import ADVICE, GUIDE, attempt_record, connection_report, error_code, recovery_method


class HelpTests(unittest.TestCase):
    def test_operational_errors_do_not_suggest_another_transport(self):
        for issue in ("runtime", "profile_busy", "bridge_input", "unknown", "cancelled"):
            for mode in ("snowflake", "obfs4", "custom"):
                self.assertIsNone(recovery_method(issue, mode))

    def test_connection_failure_offers_deliberate_alternative(self):
        self.assertEqual(recovery_method("timeout", "snowflake"), "obfs4")
        self.assertEqual(recovery_method("timeout", "obfs4"), "custom")
        self.assertEqual(recovery_method("route_check", "custom"), "snowflake")

    def test_private_exception_details_never_become_ui_error_codes(self):
        self.assertEqual(error_code(OSError("secret/bridge/192.0.2.1")), "unknown")
        self.assertEqual(error_code(ConnectError("private identifier", "anything")), "unknown")
        self.assertEqual(error_code(ConnectError("timeout", "private bridge")), "timeout")

    def test_export_allowlist_removes_extra_fields_and_limits_history(self):
        attempt = attempt_record("snowflake", "failed", 20, 12.1, "timeout")
        attempt.update(ip="192.0.2.1", bridge="PRIVATE", url="https://private.example", raw_log="SECRET")
        report = connection_report("0.1.2", [attempt] * 15, False, "error", "needed_help", "connection")
        payload = json.dumps(report)
        self.assertEqual(len(report["attempts"]), 10)
        self.assertEqual(report["attempts"][0]["elapsed_seconds_rounded"], 10)
        for value in ("192.0.2.1", "PRIVATE", "private.example", "SECRET", "raw_log"):
            self.assertNotIn(value, payload)

    def test_invalid_feedback_cannot_insert_free_text(self):
        with self.assertRaises(ValueError):
            connection_report("0.1.2", [], False, "ready", "my email is private@example.com")

    def test_translations_cover_all_recovery_guidance(self):
        for advice in ADVICE.values():
            self.assertTrue(advice.en)
            self.assertTrue(advice.tr)
        self.assertEqual(len(GUIDE["en"]), len(GUIDE["tr"]))


if __name__ == "__main__":
    unittest.main()
