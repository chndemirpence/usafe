"""Authenticated update preparation for the Windows desktop distribution.

No background requests and no default trust root: the release must embed the
publisher's reviewed root and certificate pins before enabling this component.
Uses python-tuf for signatures, expiry, metadata rollback and key rotation.
Prepared releases stay separate from the running portable installation.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import time
from urllib.parse import urlsplit
import zipfile

import requests
from tuf.api.exceptions import DownloadHTTPError
from tuf.ngclient import Updater
from tuf.ngclient.config import UpdaterConfig
from tuf.ngclient.fetcher import FetcherInterface
from windows_signature import inspect_signature

TARGET = "windows-x64/stable.zip"
MAX_ARCHIVE = 350 * 1024 * 1024
MAX_EXPANDED = 1024 * 1024 * 1024
ENTRY = "USAFE Connect/USAFE Connect.exe"


class UpdateError(RuntimeError):
    pass


@contextmanager
def store_lock(store):
    """Serialize metadata/cache writes across windows, threads and processes."""
    import msvcrt
    with (store / "update.lock").open("a+b") as lock:
        if lock.seek(0, 2) == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise UpdateError("Another update operation is in progress") from error
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})", value):
        raise UpdateError("Unsupported release version")
    return tuple(map(int, value.split(".")))


def https_base(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise UpdateError("An HTTPS release endpoint without credentials is required")
    return url.rstrip("/") + "/"


class RoutedFetcher(FetcherInterface):
    """Explicit route, remote SOCKS DNS, no redirects or direct fallback."""

    def __init__(self, bases, *, socks_port=None, allow_direct=False, cancelled=lambda: False):
        self.bases = tuple(https_base(base) for base in bases)
        if socks_port is None and not allow_direct:
            raise UpdateError("Choose a verified Tor route or explicitly allow a direct update check")
        if socks_port is not None and (type(socks_port) is not int or not 1 <= socks_port <= 65535):
            raise UpdateError("Invalid local SOCKS port")
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({"User-Agent": "USAFE-Connect-Update/1", "Accept-Encoding": "identity"})
        if socks_port is not None:
            proxy = f"socks5h://127.0.0.1:{socks_port}"
            self.session.proxies = {"http": proxy, "https": proxy}
        self.cancelled = cancelled

    def _fetch(self, url):
        if not any(url.startswith(base) for base in self.bases):
            raise UpdateError("Update request outside the configured repository")
        if self.cancelled():
            raise UpdateError("Update cancelled")
        started = time.monotonic()
        with self.session.get(url, stream=True, timeout=(15, 30), allow_redirects=False) as response:
            if response.status_code != 200:
                raise DownloadHTTPError("Update server did not return a file", response.status_code)
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise UpdateError("Encoded update responses are not accepted")
            for block in response.iter_content(64 * 1024):
                if self.cancelled() or time.monotonic() - started > 1800:
                    raise UpdateError("Update cancelled or download deadline reached")
                if block:
                    yield block

    def close(self):
        self.session.close()


def validate_certificate_pins(pins):
    values = tuple(pin.upper() for pin in pins)
    if not values or any(not re.fullmatch(r"[0-9A-F]{40}", pin) for pin in values):
        raise UpdateError("Reviewed Windows signing certificate thumbprints are required")
    return values


def verify_authenticode(executable, certificate_pins):
    pins = validate_certificate_pins(certificate_pins)
    evidence = inspect_signature(executable)
    if evidence.get("Status") != "Valid" or evidence.get("Thumbprint", "").upper() not in pins or evidence.get("Timestamped") is not True:
        raise UpdateError("Windows publisher signature or timestamp could not be verified")
    return evidence


def archive_members(archive):
    entries = archive.infolist()
    if len(entries) > 6000 or sum(e.file_size for e in entries) > MAX_EXPANDED:
        raise UpdateError("Update expands beyond the package limit")
    seen = set()
    result = []
    for entry in entries:
        name = entry.filename.rstrip("/")
        parts = name.split("/")
        if (not name or len(name) > 220 or len(parts) > 20 or parts[0] != "USAFE Connect"
                or "\\" in name or any(ord(c) < 32 for c in name)
                or any(p in ("", ".", "..") or p.endswith((" ", ".")) or re.search(r'[<>:"|?*]', p)
                       or re.fullmatch(r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", p) for p in parts)):
            raise UpdateError("Unsafe Windows path in release archive")
        kind = stat.S_IFMT(entry.external_attr >> 16)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or entry.flag_bits & 1:
            raise UpdateError("Links and encrypted entries are not accepted")
        normalized = name.casefold()
        if normalized in seen:
            raise UpdateError("Duplicate Windows path in release archive")
        seen.add(normalized)
        result.append(entry)
    if ENTRY.casefold() not in seen:
        raise UpdateError("The release is missing USAFE Connect.exe")
    return result


def extract_release(archive_path, destination):
    # Call only with a newly created, private staging directory. Never extract
    # into a user's active installation or a caller-supplied existing folder.
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive_members(archive)
        total = 0
        for entry in entries:
            target = destination.joinpath(*PurePosixPath(entry.filename).parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open("xb") as output:
                while block := source.read(1024 * 1024):
                    total += len(block)
                    if total > MAX_EXPANDED:
                        raise UpdateError("Expanded release exceeds size limit")
                    output.write(block)


@dataclass(frozen=True)
class Offer:
    version: str
    size: int
    sha256: str
    source: str


class UpdateClient:
    def __init__(self, *, bootstrap, metadata_url, target_url, store, current_version,
                 certificate_pins, fetcher, signature_verifier=verify_authenticode):
        version_tuple(current_version)
        if not isinstance(bootstrap, bytes) or not bootstrap:
            raise UpdateError("An embedded trusted root is required")
        self.bootstrap = bootstrap
        self.metadata_url, self.target_url = https_base(metadata_url), https_base(target_url)
        self.store = Path(store).resolve()
        self.store.mkdir(parents=True, exist_ok=True)
        self.current = current_version
        self.certificate_pins = validate_certificate_pins(certificate_pins)
        self.fetcher, self.signature_verifier = fetcher, signature_verifier

    def _updater(self, target_dir=None):
        return Updater(str(self.store / "metadata"), self.metadata_url,
                       target_dir=str(target_dir) if target_dir else None, target_base_url=self.target_url,
                       bootstrap=self.bootstrap, fetcher=self.fetcher,
                       config=UpdaterConfig(max_root_rotations=32, max_delegations=0,
                                            targets_max_length=128 * 1024, snapshot_max_length=64 * 1024))

    def _offer(self, updater):
        updater.refresh()
        target = updater.get_targetinfo(TARGET)
        if target is None:
            raise UpdateError("No Windows release in signed metadata")
        custom = target.unrecognized_fields.get("custom", {})
        if (custom.get("product"), custom.get("platform"), custom.get("channel")) != ("usafe-connect", "windows-x64", "stable"):
            raise UpdateError("The release is for another product, platform or channel")
        version = custom.get("version")
        if version_tuple(version) <= version_tuple(self.current):
            raise UpdateError("No newer release; older or equal packages are not installed")
        if type(target.length) is not int or not 0 < target.length <= MAX_ARCHIVE:
            raise UpdateError("Release archive exceeds download limit")
        digest = target.hashes.get("sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise UpdateError("Release requires a SHA-256 digest")
        return Offer(version, target.length, digest, self.target_url), target

    def check(self):
        with store_lock(self.store):
            offer, _ = self._offer(self._updater())
            return offer

    def prepare(self, approved_offer, *, connection_active):
        """Stage a user-approved offer. Does not change or launch the current app.

        Downloads can use Tor while it is connected; handoff must wait until
        connection_active() becomes false. Metadata is refreshed after approval.
        """
        with store_lock(self.store), tempfile.TemporaryDirectory(prefix="incoming-", dir=self.store) as temporary:
            work = Path(temporary)
            updater = self._updater(work)
            offer, target = self._offer(updater)
            if offer != approved_offer:
                raise UpdateError("Release changed since preview; review the new offer")
            archive = Path(updater.download_target(target, str(work / "release.zip")))
            package = work / "package"
            package.mkdir()
            extract_release(archive, package)
            self.signature_verifier(package / ENTRY, self.certificate_pins)
            if connection_active():
                raise UpdateError("Disconnect and close the current session before preparing the handoff")
            releases = self.store / "releases"
            releases.mkdir(exist_ok=True)
            destination = releases / (offer.version + "-" + offer.sha256[:16])
            if destination.exists():
                raise UpdateError("This release is already staged; existing files were preserved")
            # Only a complete, verified directory becomes visible. The working
            # installation is never overwritten, even if rename/write fails.
            package.rename(destination)
            return destination / ENTRY


def package_digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
