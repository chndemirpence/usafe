"""Create/check an offline release inventory. This is not publisher authentication.

Run from a trusted checkout. The inventory detects changed/missing/extra package
files; an attacker replacing both files and inventory can bypass these hashes.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

MANIFEST = "release-inventory.json"


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def package_files(root):
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Release packages must not contain symbolic links")
        if path.is_file() and path != root / MANIFEST:
            name = path.relative_to(root).as_posix()
            files[name] = {"sha256": digest(path), "bytes": path.stat().st_size}
    return files


def verify_runtime(root):
    runtime = root / "_internal/runtime"
    manifest = json.loads((runtime / "verified-files.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        path = safe_path(runtime, name)
        if not path.is_file() or digest(path) != expected:
            raise ValueError("Bundled runtime differs from verified upstream inventory: " + name)
    return manifest


def safe_path(root, name):
    part = PurePosixPath(name)
    if not name or "\\" in name or ":" in name or part.is_absolute() or ".." in part.parts:
        raise ValueError("Invalid inventory path")
    path = root.joinpath(*part.parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Inventory path escapes package")
    return path


def create(root, version):
    root = root.resolve()
    if (root / MANIFEST).exists():
        raise ValueError("Inventory already exists; do not overwrite release evidence")
    for name in ("USAFE Connect.exe", "Tor Browser/Browser/firefox.exe", "Source/connect_app.py", "Source/LICENSE"):
        if not (root / name).is_file():
            raise ValueError("Required release file missing: " + name)
    upstream = verify_runtime(root)
    files = package_files(root)
    # A release must contain a freshly extracted browser, not a personal profile.
    for name in files:
        if PurePosixPath(name).name.lower() in {"places.sqlite", "cookies.sqlite", "logins.json", "sessionstore.jsonlz4", "control.cookie", "control.port"}:
            raise ValueError("Private runtime/browser state found in release: " + name)
    manifest = {"schema": 1, "application": "USAFE Connect", "version": version,
                "platform": "windows-x64", "authentication": "Unsigned inventory; hashes detect changes only",
                "upstream": {key: upstream[key] for key in ("release", "source", "archive_sha256", "signing_key")},
                "files": files}
    with (root / MANIFEST).open("x", encoding="utf-8") as output:
        json.dump(manifest, output, indent=2)
        output.write("\n")
    return len(files)


def check(root):
    root = root.resolve()
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("schema") != 1 or not isinstance(manifest.get("files"), dict):
        raise ValueError("Unsupported inventory schema")
    expected = manifest["files"]
    for name in expected:
        safe_path(root, name)
    actual = package_files(root)
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(name for name in set(actual) & set(expected) if actual[name] != expected[name])
    return {"matches": not (missing or extra or changed), "file_count": len(actual),
            "missing": missing, "extra": extra, "changed": changed,
            "publisher_authenticated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "check"))
    parser.add_argument("package", type=Path)
    parser.add_argument("--version", default="0.1.2")
    args = parser.parse_args()
    if args.action == "create":
        print(json.dumps({"inventoried_files": create(args.package, args.version)}))
        return 0
    report = check(args.package)
    print(json.dumps(report, indent=2))
    return 0 if report["matches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
