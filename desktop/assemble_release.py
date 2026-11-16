"""Assemble source/notices, check inventory and create a Windows preview archive.

Run after build_windows.py and preparation of a fresh, signature-verified Tor
Browser. The package folder must not have been used for personal browsing.
"""
import argparse
import json
from pathlib import Path
import shutil
import zipfile

from prepare_runtime import ARTIFACT, ARCHIVE_SHA256, BROWSER, BROWSER_SHA256, SIGNER, VERSION as TOR_VERSION, sha256, verify
from release_inventory import create, check


def assemble(package, cache, evidence, version):
    source_root = Path(__file__).parent.resolve()
    package = package.resolve()
    for filename, expected in ((ARTIFACT, ARCHIVE_SHA256), (BROWSER, BROWSER_SHA256)):
        if sha256(cache / filename) != expected:
            raise ValueError("Upstream archive checksum mismatch")
        verify("C:/Program Files/Git/usr/bin/gpg.exe", cache / "gpg", cache / filename)
    source = package / "Source"
    source.mkdir()
    for pattern in ("*.py", "*.md", "*.ps1", "requirements*.txt"):
        for file in source_root.glob(pattern):
            shutil.copy2(file, source / file.name)
    shutil.copytree(source_root / "assets", source / "assets")
    shutil.copy2(source_root.parent / "LICENSE", source / "LICENSE")
    notices = package / "Notices"
    notices.mkdir()
    python = Path("C:/Program Files/Python312")
    shutil.copy2(python / "LICENSE.txt", notices / "Python.txt")
    shutil.copy2(python / "tcl/tk8.6/license.terms", notices / "Tcl-Tk.txt")
    shutil.copy2(cache / "build-env/Lib/site-packages/pyinstaller-6.22.3.dist-info/licenses/COPYING.txt", notices / "PyInstaller.txt")
    for filename in (ARTIFACT, BROWSER):
        shutil.copy2(cache / (filename + ".asc"), notices / (filename + ".asc"))
    (notices / "Upstream.txt").write_text(
        f"Tor Project release {TOR_VERSION}\nhttps://dist.torproject.org/torbrowser/{TOR_VERSION}/\n"
        f"Primary signing fingerprint: {SIGNER}\n\n"
        f"{ARCHIVE_SHA256}  {ARTIFACT}\n{BROWSER_SHA256}  {BROWSER}\n\n"
        "Tor/transport notices: _internal/runtime/docs\nTor Browser notices: Tor Browser/Browser/TorBrowser/Docs\n"
        "Build sources: https://gitlab.torproject.org/tpo/applications/tor-browser-build\n", encoding="utf-8")
    (package / "Start here.txt").write_text(
        f"USAFE Connect {version} for Windows x64\n\nExtract the full folder and open USAFE Connect.exe.\n"
        "English opens by default; choose Türkçe in the upper right for Turkish.\n"
        "Choose a bridge, Connect, then Open Tor Browser after verification.\n"
        "If a connection fails, follow the recovery card. The offline guide works without internet.\n"
        "Review and save your connection summary if you wish. Nothing is sent automatically.\n\n"
        "Enable website launch lets USAFE > Connect > Open Windows app open this version.\n"
        "Enable it again if you move the extracted folder.\n\n"
        "Source includes build instructions, tests, roadmap and license. Notices records upstream verification.\n"
        "release-inventory.json detects changes; it is not a publisher signature.\n", encoding="utf-8-sig")
    test_evidence = {}
    for mode in ("snowflake", "obfs4"):
        report = json.loads((evidence / (mode + ".json")).read_text())
        if not report.get("verified") or not report.get("socks_closed_after_stop"):
            raise ValueError("Missing successful local connection evidence")
        test_evidence[mode] = report
    (package / "Local connection tests.json").write_text(json.dumps(test_evidence, indent=2), encoding="utf-8")
    create(package, version)
    if not check(package)["matches"]:
        raise ValueError("Release inventory verification failed")
    archive = package.parent / f"USAFE-Connect-Windows-x64-{version}.zip"
    partial = archive.with_suffix(".zip.part")
    if archive.exists() or partial.exists():
        raise ValueError("Release archive already exists")
    with zipfile.ZipFile(partial, "x", zipfile.ZIP_DEFLATED, compresslevel=5) as output:
        for file in sorted(package.rglob("*")):
            if file.is_file():
                output.write(file, file.relative_to(package.parent).as_posix())
    with zipfile.ZipFile(partial) as output:
        if output.testzip() is not None:
            raise ValueError("Archive verification failed")
    partial.rename(archive)
    checksum = sha256(archive)
    archive.with_suffix(".zip.sha256").write_text(checksum + "  " + archive.name + "\n", encoding="ascii")
    print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size, "sha256": checksum}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--version", default="0.1.2")
    args = parser.parse_args()
    assemble(args.package, args.cache, args.evidence, args.version)
