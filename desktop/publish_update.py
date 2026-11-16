"""Prepare signed TUF publication files locally; does not upload or generate keys.

Production private keys belong in offline/HSM storage, outside this checkout.
Encrypted PEM signing is supported for a controlled offline release ceremony.
"""
import argparse
from datetime import datetime, timedelta, timezone
from getpass import getpass
from pathlib import Path
import shutil
import tempfile

from cryptography.hazmat.primitives.serialization import load_pem_private_key
from securesystemslib.signer import CryptoSigner
from tuf.api.metadata import Metadata, TargetFile, Targets, Snapshot, Timestamp, MetaFile
from secure_updates import (ENTRY, TARGET, MAX_ARCHIVE, UpdateError, extract_release,
                            verify_authenticode, version_tuple)


def signed_metadata(payload, role, signers, trusted_root):
    metadata = Metadata(payload)
    for signer in signers:
        metadata.sign(signer, append=True)
    trusted_root.verify_delegate(role, metadata)
    return metadata.to_bytes()


def prepare_publication(*, bootstrap, archive, version, sequence, previous_timestamp,
                        signers, output, certificate_pins, signature_verifier=verify_authenticode):
    version_tuple(version)
    root = Metadata.from_bytes(bootstrap)
    root.verify_delegate("root", root)
    now = datetime.now(timezone.utc)
    if root.signed.is_expired(now) or not root.signed.consistent_snapshot or root.signed.roles["root"].threshold < 2:
        raise UpdateError("Use a current, threshold-signed root with consistent snapshots")
    if type(sequence) is not int or sequence < 1:
        raise UpdateError("Metadata sequence must be a positive integer")
    if previous_timestamp:
        previous = Metadata.from_bytes(previous_timestamp)
        root.verify_delegate("timestamp", previous)
        if sequence <= max(previous.signed.version, previous.signed.snapshot_meta.version):
            raise UpdateError("Metadata sequence must increase from the previous publication")
    elif sequence != 1:
        raise UpdateError("First publication must use sequence 1; otherwise provide previous timestamp")
    archive, output = Path(archive), Path(output)
    if not 0 < archive.stat().st_size <= MAX_ARCHIVE:
        raise UpdateError("Archive is outside the release size limit")
    if output.exists():
        raise UpdateError("Choose a new output directory")
    with tempfile.TemporaryDirectory(prefix="usafe-publish-", dir=output.parent) as temporary:
        temporary = Path(temporary)
        package = temporary / "inspect"
        package.mkdir()
        extract_release(archive, package)
        signature_verifier(package / ENTRY, certificate_pins)
        with archive.open("rb") as stream:
            target = TargetFile.from_data(TARGET, stream, ["sha256"])
        target.unrecognized_fields["custom"] = {"product": "usafe-connect", "platform": "windows-x64",
                                                "channel": "stable", "version": version}
        targets = signed_metadata(Targets(version=sequence, expires=now + timedelta(days=30), targets={TARGET:target}),
                                  "targets", signers["targets"], root)
        import hashlib
        snapshot = signed_metadata(Snapshot(version=sequence, expires=now + timedelta(days=7),
                                   meta={"targets.json":MetaFile(sequence,len(targets),{"sha256":hashlib.sha256(targets).hexdigest()})}),
                                   "snapshot", signers["snapshot"], root)
        timestamp = signed_metadata(Timestamp(version=sequence, expires=now + timedelta(days=2),
                                    snapshot_meta=MetaFile(sequence,len(snapshot),{"sha256":hashlib.sha256(snapshot).hexdigest()})),
                                    "timestamp", signers["timestamp"], root)
        publication = temporary / "publication"
        metadata_dir = publication / "metadata"
        target_dir = publication / "targets/windows-x64"
        metadata_dir.mkdir(parents=True)
        target_dir.mkdir(parents=True)
        for name, data in {f"{root.signed.version}.root.json":bootstrap,
                           f"{sequence}.targets.json":targets, f"{sequence}.snapshot.json":snapshot,
                           "timestamp.json":timestamp}.items():
            (metadata_dir/name).write_bytes(data)
        shutil.copyfile(archive, target_dir / (target.hashes["sha256"] + ".stable.zip"))
        (publication / "PUBLISH-ORDER.txt").write_text(
            "Publish target and numbered metadata first; timestamp.json LAST.\n"
            "Retain every earlier numbered root and metadata file on the server.\n"
            "This output is a publication delta, not a replacement for the repository.\n"
            "Refresh timestamp before its 48-hour expiry. If missed, clients fail closed.\n", encoding="utf-8")
        publication.rename(output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "archive", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--sequence", required=True, type=int)
    history = parser.add_mutually_exclusive_group(required=True)
    history.add_argument("--previous-timestamp", type=Path)
    history.add_argument("--initial", action="store_true")
    parser.add_argument("--certificate-thumbprint", required=True, action="append")
    for role in ("targets", "snapshot", "timestamp"):
        parser.add_argument("--" + role + "-key", required=True, type=Path, action="append")
    args = parser.parse_args()
    signers = {}
    checkout = Path(__file__).resolve().parent.parent
    for role in ("targets", "snapshot", "timestamp"):
        signers[role] = []
        for key in getattr(args, role + "_key"):
            if key.resolve().is_relative_to(checkout) or key.resolve().is_relative_to(args.output.resolve()):
                parser.error("Keep private signing keys outside source and publication folders")
            password = getpass(f"Passphrase for {role} signing key ({key.name}): ")
            if not password:
                parser.error("Encrypted private keys with a nonempty passphrase are required")
            private = load_pem_private_key(key.read_bytes(), password=password.encode())
            signers[role].append(CryptoSigner(private))
    prepare_publication(bootstrap=args.root.read_bytes(), archive=args.archive, version=args.version,
                        sequence=args.sequence, previous_timestamp=args.previous_timestamp.read_bytes() if args.previous_timestamp else None,
                        signers=signers, output=args.output, certificate_pins=args.certificate_thumbprint)
    print("Signed publication prepared locally:", args.output)


if __name__ == "__main__":
    main()
