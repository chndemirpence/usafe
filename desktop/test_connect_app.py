"""App lifecycle regressions using a real hidden Tk root and fake network sessions."""
import time
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

from connect_app import App, COPY
from connect_core import ConnectError


class AppTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for timer in self.root.tk.call("after", "info"):
            self.root.after_cancel(timer)
        self.app.session.stop()
        self.root.destroy()

    def pump(self):
        deadline = time.monotonic() + 2
        while self.app.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.app.poll()
        self.root.update()
        self.assertFalse(self.app.busy)

    def test_timeout_shows_localized_recovery_and_records_attempt(self):
        with patch("connect_app.TorSession.start", side_effect=ConnectError("timeout", "private bridge details")):
            self.app.connect()
            self.pump()
        self.assertEqual(self.app.current_state, "error")
        self.assertNotIn("private bridge details", self.app.detail.cget("text"))
        self.assertEqual(self.app.recovery_button.cget("text"), COPY["en"]["try_obfs4"])
        self.app.select_language(1)
        self.assertEqual(self.app.recovery_button.cget("text"), COPY["tr"]["try_obfs4"])
        self.assertEqual(self.app.attempts[0]["outcome"], "failed")

    def test_stop_discards_late_success(self):
        self.app.user_stopped = True
        self.app.current_state = "offline"
        self.app.events.put({"state": "connected", "progress": 100})
        self.app.poll()
        self.assertEqual(self.app.current_state, "offline")
        self.assertIsNone(self.app.checked_at)

    def test_recovery_stops_existing_session_before_new_attempt(self):
        self.app.mode.set("snowflake")
        self.app.issue = "route_check"
        self.app.current_state = "error"
        stopped = []
        with patch.object(self.app.session, "stop", side_effect=lambda: stopped.append(True)), \
                patch.object(self.app, "connect") as connect:
            self.app.recover()
            self.pump()
            connect.assert_called_once()
        self.assertTrue(stopped)
        self.assertEqual(self.app.mode.get(), "obfs4")

    def test_custom_recovery_waits_for_user_input(self):
        self.app.mode.set("obfs4")
        self.app.issue = "timeout"
        self.app.current_state = "error"
        with patch.object(self.app, "connect") as connect:
            self.app.recover()
            self.pump()
            connect.assert_not_called()
        self.assertEqual(self.app.mode.get(), "custom")
        self.assertEqual(self.app.current_state, "ready")

    def test_dead_process_clears_stale_verified_state(self):
        self.app.session.process = Mock()
        self.app.session.process.poll.return_value = 1
        self.app.session.verified = True
        self.app.current_state = "connected"
        self.app.poll()
        self.assertFalse(self.app.session.verified)
        self.assertEqual(self.app.issue, "tor_stopped")
        self.assertEqual(str(self.app.open_button.cget("state")), "disabled")

    def test_offline_dialogs_do_not_leave_dead_translation_widgets(self):
        count = len(self.app.labels)
        self.app.show_guide()
        self.app.export_summary()
        for child in self.root.winfo_children():
            if isinstance(child, tk.Toplevel):
                child.destroy()
        self.app.select_language(1)
        self.app.select_language(0)
        self.assertEqual(len(self.app.labels), count)


if __name__ == "__main__":
    unittest.main()
