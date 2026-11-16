"""Maintainer-only upstream review. Reports changes; never installs or changes pins.

This explicit command contacts Tor Project over HTTPS from the build machine.
It is not imported or called by USAFE Connect and is not an authenticated updater.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlsplit

from prepare_runtime import VERSION

FEED = "https://aus1.torproject.org/torbrowser/update_3/release/download-windows-x86_64.json"
EXPERT_PAGE = "https://download.torproject.org/tor/"
MAX_BYTES = 1024 * 1024


def version_parts(version):
    if not isinstance(version, str) or not re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){1,3}", version):
        raise ValueError("Expected a stable numeric release version")
    return tuple(int(part) for part in version.split(".")) + (0,) * (4 - len(version.split(".")))


class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https" or urlsplit(newurl).netloc != urlsplit(req.full_url).netloc:
            raise ValueError("Upstream review redirected outside its HTTPS host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "USAFE-maintainer-release-review/1"})
    with urllib.request.build_opener(RestrictedRedirect()).open(request, timeout=20) as response:
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("Upstream review response exceeds 1 MiB")
        return body.decode("utf-8")


def browser_version(data):
    if not isinstance(data, dict):
        raise ValueError("Browser release feed must be an object")
    version = data.get("version")
    version_parts(version)
    expected = f"https://dist.torproject.org/torbrowser/{version}/tor-browser-windows-x86_64-portable-{version}.exe"
    if data.get("binary") != expected or data.get("sig") != expected + ".asc":
        raise ValueError("Browser artifact/signature does not match official platform/version")
    return version


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.urls.add(href)


def expert_version(html):
    links = Links()
    links.feed(html)
    versions = []
    pattern = r"https://dist\.torproject\.org/torbrowser/(\d{1,3}(?:\.\d{1,3}){1,3})/tor-expert-bundle-windows-x86_64-\1\.tar\.gz"
    for url in links.urls:
        match = re.fullmatch(pattern, url)
        if match and url + ".asc" in links.urls:
            versions.append(match.group(1))
    if not versions:
        raise ValueError("No stable Windows x64 expert bundle with signature link found")
    return max(versions, key=version_parts)


def assess(pinned, browser, expert):
    current = version_parts(pinned)
    published = [version_parts(browser), version_parts(expert)]
    if published[0] != published[1]:
        status = "upstream-inconsistent"
    elif published[0] > current:
        status = "update-review-required"
    elif published[0] < current:
        status = "upstream-older-than-pin"
    else:
        status = "matches-current-pin"
    return {"status": status, "pinned": pinned, "tor_browser": browser,
            "tor_expert_bundle": expert, "publisher_authenticated": False,
            "action": "Review release/security notes. Verify official signatures and independently recorded checksums before changing pins. Do not downgrade based on this report."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional new JSON report; an existing file is never overwritten")
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("Choose a new output filename; prior review evidence is preserved")
    try:
        report = assess(VERSION, browser_version(json.loads(fetch(FEED))), expert_version(fetch(EXPERT_PAGE)))
    except (ValueError, OSError) as error:
        report = {"status": "check-failed", "error": str(error), "pinned": VERSION,
                  "action": "No up-to-date result. Review official release sources manually; nothing was changed."}
    report.update(checked_at_utc=datetime.now(timezone.utc).isoformat(), sources=[FEED, EXPERT_PAGE])
    result = json.dumps(report, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as output:
            output.write(result)
    print(result, end="")
    return 0 if report["status"] == "matches-current-pin" else 2


if __name__ == "__main__":
    raise SystemExit(main())
