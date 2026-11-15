"""USAFE Connect's Windows Tor session manager.

Transport implementations and bridge defaults come from a verified Tor release.
The application never changes the system proxy or retries a request directly.
"""
from __future__ import annotations

import ipaddress
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
MODES = ("snowflake", "obfs4", "custom")


def bridge_lines(text: str) -> list[str]:
    """Accept transport bridge lines, never arbitrary torrc directives."""
    if len(text) > 16000:
        raise ValueError("Use at most eight bridge lines.")
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("Bridge "):
            line = line[7:]
        if any(ord(char) < 32 or ord(char) > 126 for char in line) or any(char in line for char in '\\"#'):
            raise ValueError("A bridge contains an unexpected character.")
        parts = line.split()
        if len(parts) < 4 or parts[0] not in ("obfs4", "webtunnel"):
            raise ValueError("Paste an obfs4 or WebTunnel bridge from your trusted distributor.")
        address, separator, port = parts[1].rpartition(":")
        if not separator or not port.isdigit() or not 1 <= int(port) <= 65535:
            raise ValueError("The bridge needs a valid address and port.")
        try:
            ipaddress.ip_address(address.strip("[]"))
        except ValueError as error:
            raise ValueError("The bridge address must be an IPv4 or IPv6 address.") from error
        if not re.fullmatch(r"[0-9A-Fa-f]{40}", parts[2]):
            raise ValueError("The bridge fingerprint must contain 40 hexadecimal characters.")
        options = {}
        for part in parts[3:]:
            key, equal, value = part.partition("=")
            if not equal or not value or key in options:
                raise ValueError("Check the bridge options.")
            options[key] = value
        if parts[0] == "obfs4":
            if set(options) != {"cert", "iat-mode"} or options["iat-mode"] not in ("0", "1", "2"):
                raise ValueError("An obfs4 bridge requires cert and iat-mode.")
            if not re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", options["cert"]):
                raise ValueError("Check the obfs4 certificate.")
        else:
            if not {"url"} <= options.keys() or not options.keys() <= {"url", "ver"}:
                raise ValueError("A WebTunnel bridge requires its HTTPS url.")
            parsed = urlsplit(options["url"])
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ValueError("The WebTunnel URL must be HTTPS without credentials or a fragment.")
            if "ver" in options and not re.fullmatch(r"[0-9.]+", options["ver"]):
                raise ValueError("Check the WebTunnel version.")
        lines.append(" ".join(parts))
    if not lines or len(lines) > 8:
        raise ValueError("Paste between one and eight bridge lines.")
    return lines


def quoted_path(path: Path) -> str:
    value = str(path.resolve())
    if any(char in value for char in '\r\n"'):
        raise ValueError("Unsupported character in folder path.")
    return json.dumps(value)


def configuration(runtime: Path, state_dir: Path, mode: str, custom: str) -> str:
    if mode not in MODES:
        raise ValueError("Choose Snowflake, obfs4, or a custom bridge.")
    if mode == "custom":
        bridges = bridge_lines(custom)
    else:
        config = json.loads((runtime / "tor/pluggable_transports/pt_config.json").read_text())
        bridges = config["bridges"][mode]
        if not bridges or any(not line.startswith(mode + " ") or "\n" in line or "\r" in line for line in bridges):
            raise ValueError("Invalid signed transport configuration.")
    lines = [
        "ClientOnly 1", "AvoidDiskWrites 1", "SafeLogging 1", "Log notice stdout",
        "SocksPort 127.0.0.1:auto IsolateSOCKSAuth", "ControlPort 127.0.0.1:auto",
        "CookieAuthentication 1", "UseBridges 1", "DormantCanceledByStartup 1",
        "DataDirectory " + quoted_path(state_dir / "data"),
        "CookieAuthFile " + quoted_path(state_dir / "control.cookie"),
        "ControlPortWriteToFile " + quoted_path(state_dir / "control.port"),
        "GeoIPFile " + quoted_path(runtime / "data/geoip"),
        "GeoIPv6File " + quoted_path(runtime / "data/geoip6"),
        "ClientTransportPlugin obfs4,snowflake,webtunnel exec pluggable_transports\\lyrebird.exe",
        "__OwningControllerProcess " + str(os.getpid()),
    ]
    return "\n".join(lines + ["Bridge " + line for line in bridges]) + "\n"


class TorSession:
    def __init__(self, runtime: Path, state_dir: Path):
        self.runtime = runtime.resolve()
        self.state_dir = state_dir.resolve()
        self.process = None
        self.socks_port = None
        self.control_port = None
        self.verified = False
        self.cancelled = threading.Event()
        self.lock = threading.RLock()
        self.progress = 0
        self.mode = None
        self.instance_lock = None

    def _acquire_instance(self):
        import msvcrt
        self.state_dir.mkdir(parents=True, exist_ok=True)
        handle = (self.state_dir / "session.lock").open("a+b")
        if handle.seek(0, 2) == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            handle.close()
            raise RuntimeError("Another USAFE connection is using this profile. Close it first.") from error
        self.instance_lock = handle

    def _verify_runtime(self):
        manifest = json.loads((self.runtime / "verified-files.json").read_text())
        for name in ("tor/tor.exe", "tor/pluggable_transports/lyrebird.exe", "tor/pluggable_transports/pt_config.json"):
            if hashlib.sha256((self.runtime / name).read_bytes()).hexdigest() != manifest["files"].get(name):
                raise RuntimeError("The Tor bundle has changed. Restore the verified runtime before connecting.")

    def _read_reply(self, stream):
        lines = []
        for _ in range(80):
            line = stream.readline(16384).decode("utf-8", errors="replace").rstrip("\r\n")
            if not line:
                raise RuntimeError("Tor control connection closed.")
            lines.append(line)
            if len(line) >= 4 and line[3] == " ":
                if not line.startswith("250 "):
                    raise RuntimeError("Tor could not complete the connection request.")
                return "\n".join(lines)
        raise RuntimeError("Unexpected Tor control response.")

    def control(self, command: str):
        cookie = (self.state_dir / "control.cookie").read_bytes()
        if len(cookie) != 32 or not self.control_port:
            raise RuntimeError("Tor control is not ready.")
        with socket.create_connection(("127.0.0.1", self.control_port), timeout=3) as connection:
            stream = connection.makefile("rwb", buffering=0)
            stream.write(("AUTHENTICATE " + cookie.hex() + "\r\n").encode())
            self._read_reply(stream)
            stream.write((command + "\r\n").encode())
            return self._read_reply(stream)

    def _consume_output(self, process):
        # Discard raw logs. Bridge addresses and other network details are private.
        with process.stdout:
            for line in process.stdout:
                match = re.search(r"Bootstrapped (\d+)%", line)
                if match:
                    self.progress = int(match[1])

    def start(self, mode="snowflake", custom="", notify=lambda message: None, timeout=150):
        with self.lock:
            if self.process and self.process.poll() is None:
                raise RuntimeError("A connection is already running.")
            if self.cancelled.is_set():
                raise RuntimeError("Connection cancelled.")
            self._verify_runtime()
            config = configuration(self.runtime, self.state_dir, mode, custom)
            self._acquire_instance()
            try:
                (self.state_dir / "control.port").unlink(missing_ok=True)
                (self.state_dir / "control.cookie").unlink(missing_ok=True)
                torrc = self.state_dir / "torrc"
                torrc.write_text(config, encoding="utf-8")
                self.progress = 0
                self.verified = False
                self.mode = mode
                self.process = subprocess.Popen(
                    [str(self.runtime / "tor/tor.exe"), "-f", str(torrc)],
                    cwd=self.runtime / "tor", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW,
                )
            except Exception:
                self.stop()
                raise
            process = self.process
            threading.Thread(target=self._consume_output, args=(process,), daemon=True).start()
        deadline = time.monotonic() + timeout
        last_progress = -1
        try:
            while time.monotonic() < deadline:
                if self.cancelled.wait(0.3):
                    raise RuntimeError("Connection cancelled.")
                if process.poll() is not None:
                    raise RuntimeError("Tor stopped. Check the bundle and try another bridge.")
                if self.progress != last_progress:
                    last_progress = self.progress
                    notify({"state": "connecting", "progress": self.progress})
                if self.control_port is None:
                    try:
                        value = (self.state_dir / "control.port").read_text().strip()
                        match = re.fullmatch(r"PORT=127\.0\.0\.1:(\d+)", value)
                        if match:
                            self.control_port = int(match[1])
                    except FileNotFoundError:
                        pass
                if self.progress == 100 and self.control_port:
                    listeners = self.control("GETINFO net/listeners/socks")
                    match = re.search(r'"127\.0\.0\.1:(\d+)"', listeners)
                    if not match:
                        raise RuntimeError("Tor did not provide a local SOCKS listener.")
                    self.socks_port = int(match[1])
                    notify({"state": "verifying", "progress": 100})
                    self.check_connection()
                    notify({"state": "connected", "progress": 100})
                    return
            raise RuntimeError("This transport did not connect in time. Try another transport or a fresh bridge.")
        except Exception:
            self.stop()
            raise

    def check_connection(self):
        """Use SOCKS remote DNS and verify Tor egress over certificate-checked HTTPS."""
        self.verified = False
        process = self.process
        if not process or process.poll() is not None or not self.socks_port:
            raise RuntimeError("Connect before checking the route.")
        curl = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/curl.exe"
        result = subprocess.run([
            str(curl), "--disable", "--silent", "--show-error", "--fail", "--proxy",
            f"socks5h://127.0.0.1:{self.socks_port}", "--noproxy", "", "--proto", "=https",
            "--connect-timeout", "15", "--max-time", "35", "--max-filesize", "8192",
            "https://check.torproject.org/api/ip",
        ], capture_output=True, timeout=40, creationflags=NO_WINDOW)
        if result.returncode:
            raise RuntimeError("Tor is bootstrapped, but the HTTPS route check failed. Retry or change transport.")
        try:
            valid = json.loads(result.stdout).get("IsTor") is True
        except (ValueError, AttributeError):
            valid = False
        if not valid:
            raise RuntimeError("The route check did not confirm a Tor exit.")
        with self.lock:
            if self.cancelled.is_set() or self.process is not process or process.poll() is not None:
                raise RuntimeError("Connection stopped.")
            self.verified = True
        return True

    def launch_browser(self, browser: Path):
        if self.cancelled.is_set() or not self.verified or not self.process or self.process.poll() is not None:
            raise RuntimeError("Verify the Tor connection before opening the browser.")
        browser = browser.resolve()
        if (browser.name.lower() != "firefox.exe" or not browser.is_file()
                or not (browser.parent / "TorBrowser").is_dir()):
            raise ValueError("Choose firefox.exe inside a Tor Browser / Browser folder.")
        env = os.environ.copy()
        for key in list(env):
            if key.startswith("TOR_"):
                del env[key]
        env.update({"TOR_SKIP_LAUNCH": "1", "TOR_SOCKS_HOST": "127.0.0.1",
                    "TOR_SOCKS_PORT": str(self.socks_port), "TOR_CONTROL_PORT": str(self.control_port),
                    "TOR_CONTROL_HOST": "127.0.0.1",
                    "TOR_CONTROL_COOKIE_AUTH_FILE": str(self.state_dir / "control.cookie")})
        return subprocess.Popen([str(browser), "-no-remote", "https://check.torproject.org/",
                                 "https://www.argodelta.com/tools/usafe/"],
                                cwd=browser.parent, env=env)

    def stop(self):
        self.cancelled.set()
        with self.lock:
            self.verified = False
            process = self.process
            if process and process.poll() is None:
                try:
                    self.control("SIGNAL SHUTDOWN")
                    process.wait(timeout=6)
                except (OSError, RuntimeError, subprocess.TimeoutExpired):
                    process.terminate()
                    try:
                        process.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=4)
            self.process = None
            self.socks_port = None
            self.control_port = None
            # Tor retains guard state under data/. Remove the private bridge configuration.
            if self.instance_lock:
                try:
                    for name in ("torrc", "control.cookie", "control.port"):
                        (self.state_dir / name).unlink(missing_ok=True)
                finally:
                    self.instance_lock.close()
                    self.instance_lock = None
