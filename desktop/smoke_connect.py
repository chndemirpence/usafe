"""Explicit opt-in live connection test; does not export IP addresses or bridge lines."""
import argparse
import json
from pathlib import Path
import socket
import time

from connect_core import TorSession


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["snowflake", "obfs4"], default="snowflake")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    session = TorSession(Path(__file__).parent / "runtime", args.state)
    start = time.monotonic()
    report = {"transport": args.mode, "verified": False, "test": "local-network integration", "disconnected": False}
    port = None
    try:
        session.start(args.mode, timeout=args.timeout, notify=lambda event: print(json.dumps(event), flush=True))
        port = session.socks_port
        report["verified"] = session.verified
        report["elapsed_seconds"] = round(time.monotonic() - start, 1)
        report["loopback_listener"] = '"127.0.0.1:' in session.control("GETINFO net/listeners/socks")
    except Exception as error:
        report["failure"] = str(error)
        report["last_bootstrap_percent"] = session.progress
    finally:
        session.stop()
        report["disconnected"] = session.process is None
        if port:
            with socket.socket() as probe:
                probe.settimeout(3)
                report["socks_closed_after_stop"] = probe.connect_ex(("127.0.0.1", port)) != 0
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report), flush=True)
    return 0 if report["verified"] and report.get("socks_closed_after_stop") else 1


if __name__ == "__main__":
    raise SystemExit(main())
