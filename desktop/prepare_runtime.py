"""Prepare a pinned, signature-verified official Tor runtime (build machine only)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

VERSION = "16.0.1"
SIGNER = "EF6E286DDA85EA2A4BA7DE684E2C6E8793298290"
ARTIFACT = f"tor-expert-bundle-windows-x86_64-{VERSION}.tar.gz"
ARCHIVE_SHA256 = "9eed3c3ff1fe43df034ce360196c9ec95472560d77ff55614d0cd5120edea27b"
BROWSER = f"tor-browser-windows-x86_64-portable-{VERSION}.exe"
BROWSER_SHA256 = "fbef840ba111409213dec2291e3594a43b82525545cdef0490a5750f24f5f232"
BASE = f"https://dist.torproject.org/torbrowser/{VERSION}/"


def gpg_path(gpg, path):
    """Git's MSYS GPG expects drive mounts for --homedir on hosted Windows."""
    absolute = Path(path).resolve().as_posix()
    if "/git/usr/bin/" in str(gpg).replace("\\", "/").lower() and len(absolute) > 2 and absolute[1] == ":":
        return "/" + absolute[0].lower() + absolute[2:]
    return absolute


def sha256(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def fetch(url, path, limit):
    if path.is_file():
        return
    temporary = path.with_suffix(path.suffix + ".part")
    total = 0
    try:
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as output:
            if not response.url.startswith("https://"):
                raise RuntimeError("Download redirected away from HTTPS.")
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > limit:
                    raise RuntimeError("Download exceeded its size limit.")
                output.write(block)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def verify(gpg, home, artifact):
    result = subprocess.run(
        [gpg, "--homedir", gpg_path(gpg, home), "--batch", "--status-fd", "1", "--verify", gpg_path(gpg, artifact) + ".asc", gpg_path(gpg, artifact)],
        capture_output=True, text=True, timeout=60,
    )
    valid = [line.split() for line in result.stdout.splitlines() if line.startswith("[GNUPG:] VALIDSIG ")]
    if result.returncode != 0 or not any(parts[-1] == SIGNER for parts in valid):
        raise RuntimeError("Tor signature verification failed. Nothing will be extracted or executed. " + result.stderr.strip()[:2000])


def prepare(cache, destination, gpg, browser_dir=None):
    cache.mkdir(parents=True, exist_ok=True)
    key = cache / "tor-browser-signing-key.asc"
    fetch(f"https://keys.openpgp.org/vks/v1/by-fingerprint/{SIGNER}", key, 1024 * 1024)
    artifacts = [(ARTIFACT, ARCHIVE_SHA256, 80 * 1024 * 1024)]
    if browser_dir:
        artifacts.append((BROWSER, BROWSER_SHA256, 200 * 1024 * 1024))
    with tempfile.TemporaryDirectory(prefix="usafe-signature-") as folder:
        home = Path(folder)
        imported = subprocess.run([gpg, "--homedir", gpg_path(gpg, home), "--batch", "--import", gpg_path(gpg, key)], capture_output=True, text=True, timeout=60)
        if imported.returncode:
            raise RuntimeError("Public signing key import failed: " + imported.stderr.strip()[:2000])
        for name, digest, limit in artifacts:
            fetch(BASE + name, cache / name, limit)
            fetch(BASE + name + ".asc", cache / (name + ".asc"), 64 * 1024)
            if sha256(cache / name) != digest:
                raise RuntimeError("The download does not match the pinned release checksum.")
            verify(gpg, home, cache / name)
            print(f"Verified official signature: {name}", flush=True)
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError("Choose an empty runtime destination; existing files are never replaced.")
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(cache / ARTIFACT) as archive:
        archive.extractall(destination, filter="data")
    files = {str(path.relative_to(destination)).replace("\\", "/"): sha256(path)
             for path in sorted(destination.rglob("*")) if path.is_file()}
    (destination / "verified-files.json").write_text(json.dumps({
        "release": VERSION, "source": BASE + ARTIFACT, "archive_sha256": ARCHIVE_SHA256,
        "signing_key": SIGNER, "files": files,
    }, indent=2), encoding="utf-8")
    if browser_dir:
        if browser_dir.exists() and any(browser_dir.iterdir()):
            raise RuntimeError("Choose an empty Tor Browser destination.")
        # NSIS requires /D to be the last, unquoted command-line argument, even with spaces.
        command = '"' + str((cache / BROWSER).resolve()) + '" /S /D=' + str(browser_dir.resolve())
        subprocess.run(command, check=True, timeout=180)
        if not (browser_dir / "Browser/firefox.exe").is_file():
            raise RuntimeError("The verified portable Tor Browser did not extract successfully.")
    print("Verified runtime ready: " + str(destination), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--destination", type=Path, default=Path(__file__).parent / "runtime")
    parser.add_argument("--gpg", default=shutil.which("gpg") or "C:/Program Files/Git/usr/bin/gpg.exe")
    parser.add_argument("--browser-dir", type=Path)
    args = parser.parse_args()
    prepare(args.cache, args.destination, args.gpg, args.browser_dir)
