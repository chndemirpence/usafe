"""Real TUF signatures with ephemeral in-memory test keys; no production keys."""
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch, Mock
import zipfile

from securesystemslib.signer import CryptoSigner
from tuf.api.metadata import Metadata, Root, Targets, TargetFile, Snapshot, Timestamp, MetaFile
from tuf.api.exceptions import DownloadHTTPError
from tuf.ngclient.fetcher import FetcherInterface
from secure_updates import (UpdateClient, UpdateError, RoutedFetcher, TARGET, ENTRY,
                            archive_members, verify_authenticode, MAX_ARCHIVE, store_lock)
from publish_update import prepare_publication

META = "https://updates.example.invalid/metadata/"
FILES = "https://updates.example.invalid/targets/"


def zip_bytes(extra=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(ENTRY, b"synthetic executable - not runnable")
        for name, body in (extra or {}).items():
            archive.writestr(name, body)
    return stream.getvalue()


class MemoryRepository(FetcherInterface):
    def __init__(self):
        self.files = {}
        self.signers = {r: CryptoSigner.generate_ed25519() for r in ("targets", "snapshot", "timestamp")}
        self.root_keys = [CryptoSigner.generate_ed25519() for _ in range(3)]
        root = Root(expires=datetime.now(timezone.utc) + timedelta(days=30), consistent_snapshot=True)
        for signer in self.root_keys:
            root.add_key(signer.public_key, "root")
        root.roles["root"].threshold = 2
        for role, signer in self.signers.items():
            root.add_key(signer.public_key, role)
        self.root = Metadata(root)
        self.root.sign(self.root_keys[0])
        self.root.sign(self.root_keys[1], append=True)
        self.bootstrap = self.root.to_bytes()
        self.files[META + "1.root.json"] = self.bootstrap
        self.publish()

    def publish(self, *, metadata_version=1, release="0.1.3", platform="windows-x64", expired=False, payload=None, length=None):
        body = payload if payload is not None else zip_bytes()
        self.body = body
        expiration = datetime.now(timezone.utc) + timedelta(days=-1 if expired else 7)
        target = TargetFile.from_data(TARGET, body)
        if length is not None:
            target.length = length
        target.unrecognized_fields["custom"] = {"product": "usafe-connect", "platform": platform,
                                                "channel": "stable", "version": release}
        targets = Metadata(Targets(version=metadata_version, expires=expiration, targets={TARGET: target}))
        targets.sign(self.signers["targets"])
        targets_data = targets.to_bytes()
        snapshot = Metadata(Snapshot(version=metadata_version, expires=expiration,
                            meta={"targets.json": MetaFile(metadata_version, len(targets_data), {"sha256": hashlib.sha256(targets_data).hexdigest()})}))
        snapshot.sign(self.signers["snapshot"])
        snapshot_data = snapshot.to_bytes()
        timestamp = Metadata(Timestamp(version=metadata_version, expires=expiration,
                              snapshot_meta=MetaFile(metadata_version, len(snapshot_data), {"sha256": hashlib.sha256(snapshot_data).hexdigest()})))
        timestamp.sign(self.signers["timestamp"])
        self.files.update({META + "timestamp.json": timestamp.to_bytes(),
                           META + f"{metadata_version}.snapshot.json": snapshot_data,
                           META + f"{metadata_version}.targets.json": targets_data,
                           FILES + "windows-x64/" + target.hashes["sha256"] + ".stable.zip": body})

    def _fetch(self, url):
        if url not in self.files:
            raise DownloadHTTPError("not found", 404)
        yield self.files[url]


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Path(self.temp.name) / "updates"
        self.active = Path(self.temp.name) / "current.exe"
        self.active.write_bytes(b"working installation")
        self.repo = MemoryRepository()
        self.verifier = Mock(return_value={"Status": "Valid"})

    def client(self, **kwargs):
        return UpdateClient(bootstrap=self.repo.bootstrap, metadata_url=META, target_url=FILES,
                            store=self.store, current_version="0.1.2", certificate_pins=["A" * 40],
                            fetcher=self.repo, signature_verifier=kwargs.get("verifier", self.verifier))

    def assert_preserved(self):
        self.assertEqual(self.active.read_bytes(), b"working installation")
        self.assertFalse(list(self.store.glob("incoming-*")))

    def test_verified_release_staged_separately(self):
        client = self.client()
        offer = client.check()
        target = client.prepare(offer, connection_active=lambda: False)
        self.assertEqual(target.read_bytes(), b"synthetic executable - not runnable")
        self.verifier.assert_called_once()
        self.assert_preserved()

    def test_changed_archive_rejected(self):
        client = self.client()
        offer = client.check()
        key = next(k for k in self.repo.files if k.startswith(FILES))
        self.repo.files[key] = b"x" * len(self.repo.files[key])
        with self.assertRaises(Exception):
            client.prepare(offer, connection_active=lambda: False)
        self.verifier.assert_not_called()
        self.assert_preserved()

    def test_wrong_platform_oversized_and_downgrade_rejected(self):
        for change in ({"platform": "android"}, {"length": MAX_ARCHIVE + 1}, {"release": "0.1.1"}):
            with self.subTest(change=change):
                self.repo.publish(**change)
                # A fresh cache distinguishes package-policy rejection from TUF rollback.
                self.store = self.store.parent / ("case-" + str(len(list(self.store.parent.iterdir()))))
                with self.assertRaises(UpdateError):
                    self.client().check()

    def test_expired_metadata_rejected(self):
        self.repo.publish(expired=True)
        with self.assertRaises(Exception):
            self.client().check()

    def test_invalid_timestamp_signature_rejected(self):
        metadata = Metadata.from_bytes(self.repo.files[META + "timestamp.json"])
        metadata.sign(CryptoSigner.generate_ed25519())
        self.repo.files[META + "timestamp.json"] = metadata.to_bytes()
        with self.assertRaises(Exception):
            self.client().check()

    def test_cached_newer_metadata_blocks_replay(self):
        original = dict(self.repo.files)
        self.repo.publish(metadata_version=2, release="0.1.4")
        self.client().check()
        self.repo.files = original
        with self.assertRaises(Exception):
            self.client().check()

    def test_offer_changed_requires_new_preview(self):
        client = self.client()
        offer = client.check()
        self.repo.publish(metadata_version=2, release="0.1.4")
        with self.assertRaisesRegex(UpdateError, "preview"):
            client.prepare(offer, connection_active=lambda: False)
        self.assert_preserved()

    def test_active_connection_preserves_current_install(self):
        client = self.client()
        with self.assertRaisesRegex(UpdateError, "Disconnect"):
            client.prepare(client.check(), connection_active=lambda: True)
        self.assert_preserved()

    def test_rejected_windows_signature_never_handed_off(self):
        client = self.client(verifier=Mock(side_effect=UpdateError("unsigned")))
        with self.assertRaisesRegex(UpdateError, "unsigned"):
            client.prepare(client.check(), connection_active=lambda: False)
        self.assert_preserved()
        self.assertFalse((self.store / "releases").exists())

    def test_interrupted_download_preserves_install(self):
        client = self.client()
        offer = client.check()
        original = self.repo._fetch
        def fail(url):
            if url.startswith(FILES):
                yield self.repo.body[:12]
                raise OSError("connection interrupted")
            yield from original(url)
        self.repo._fetch = fail
        with self.assertRaises(Exception):
            client.prepare(offer, connection_active=lambda: False)
        self.assert_preserved()

    def test_root_rotation_requires_old_and_new_thresholds(self):
        rotated = Metadata.from_bytes(self.repo.bootstrap)
        rotated.signed.version = 2
        old = self.repo.root_keys
        new = [CryptoSigner.generate_ed25519() for _ in range(3)]
        for key in old:
            rotated.signed.revoke_key(key.public_key.keyid, "root")
        for key in new:
            rotated.signed.add_key(key.public_key, "root")
        rotated.sign(old[0])
        rotated.sign(old[1], append=True)
        rotated.sign(new[0], append=True)
        self.repo.files[META + "2.root.json"] = rotated.to_bytes()
        with self.assertRaises(Exception):
            self.client().check()
        rotated.sign(new[1], append=True)
        self.repo.files[META + "2.root.json"] = rotated.to_bytes()
        self.assertEqual(self.client().check().version, "0.1.3")

    def test_malicious_zip_paths_and_duplicates_rejected(self):
        for name in ("../escaped.exe", "USAFE Connect/../escape", "USAFE Connect/CON.txt",
                     "USAFE Connect/file:stream", "USAFE Connect/file.", "USAFE Connect/USAFE CONNECT.exe"):
            with self.subTest(name=name), zipfile.ZipFile(io.BytesIO(zip_bytes({name:b"x"}))) as archive:
                with self.assertRaises(UpdateError):
                    archive_members(archive)

    def test_zip_symlink_rejected(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            info = zipfile.ZipInfo(ENTRY)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "elsewhere")
        with zipfile.ZipFile(stream) as archive, self.assertRaises(UpdateError):
            archive_members(archive)

    def test_route_is_explicit_and_proxy_has_no_fallback(self):
        with self.assertRaises(UpdateError):
            RoutedFetcher([META, FILES])
        fetcher = RoutedFetcher([META, FILES], socks_port=9150)
        self.addCleanup(fetcher.close)
        self.assertFalse(fetcher.session.trust_env)
        self.assertEqual(fetcher.session.proxies["https"], "socks5h://127.0.0.1:9150")
        with patch.object(fetcher.session, "get", side_effect=OSError("proxy down")) as get:
            with self.assertRaises(Exception):
                list(fetcher.fetch(META + "timestamp.json"))
            self.assertEqual(get.call_count, 1)

    def test_authenticode_requires_timestamp_and_pinned_identity(self):
        for data in ({"Status":"NotSigned"}, {"Status":"Valid","Thumbprint":"B"*40,"Timestamped":True},
                     {"Status":"Valid","Thumbprint":"A"*40,"Timestamped":False}):
            with patch("secure_updates.inspect_signature", return_value=data), self.assertRaises(UpdateError):
                verify_authenticode(self.active, ["A"*40])

    def publication(self, **changes):
        archive = self.store.parent / "release.zip"
        archive.write_bytes(zip_bytes())
        args = dict(bootstrap=self.repo.bootstrap, archive=archive, version="0.1.3", sequence=1,
                    previous_timestamp=None, signers={k:[s] for k,s in self.repo.signers.items()},
                    output=self.store.parent/"publication", certificate_pins=["A"*40],
                    signature_verifier=self.verifier)
        args.update(changes)
        return prepare_publication(**args)

    def test_publication_output_verifies_with_real_tuf_client(self):
        publication = self.publication()
        self.repo.files = {}
        for file in publication.rglob("*"):
            if file.is_file() and file.name != "PUBLISH-ORDER.txt":
                self.repo.files["https://updates.example.invalid/" + file.relative_to(publication).as_posix()] = file.read_bytes()
        client = self.client()
        destination = client.prepare(client.check(), connection_active=lambda: False)
        self.assertTrue(destination.is_file())
        self.assert_preserved()

    def test_publication_rejects_wrong_signer_and_reused_sequence(self):
        signers = {k:[s] for k,s in self.repo.signers.items()}
        signers["targets"] = [CryptoSigner.generate_ed25519()]
        with self.assertRaises(Exception):
            self.publication(signers=signers)
        self.assertFalse((self.store.parent/"publication").exists())
        with self.assertRaisesRegex(UpdateError, "increase"):
            self.publication(previous_timestamp=self.repo.files[META+"timestamp.json"])

    def test_publication_does_not_replace_prior_output(self):
        self.publication()
        with self.assertRaisesRegex(UpdateError, "new output"):
            self.publication()

    def test_concurrent_cache_write_rejected(self):
        client = self.client()
        with store_lock(self.store), self.assertRaisesRegex(UpdateError, "in progress"):
            client.check()
        self.assertEqual(client.check().version, "0.1.3")

    def test_unexpected_redirect_and_cancel_rejected_without_second_request(self):
        fetcher = RoutedFetcher([META, FILES], allow_direct=True)
        self.addCleanup(fetcher.close)
        response = Mock(status_code=302)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.object(fetcher.session, "get", return_value=response) as get:
            with self.assertRaises(Exception):
                list(fetcher.fetch(META + "timestamp.json"))
            self.assertFalse(get.call_args.kwargs["allow_redirects"])
            self.assertEqual(get.call_count, 1)
        fetcher.cancelled = lambda: True
        with patch.object(fetcher.session, "get") as get, self.assertRaises(Exception):
            list(fetcher.fetch(META + "timestamp.json"))
        get.assert_not_called()

    def test_oversized_download_stopped_by_tuf(self):
        client = self.client()
        offer = client.check()
        key = next(k for k in self.repo.files if k.startswith(FILES))
        self.repo.files[key] += b"extra"
        with self.assertRaises(Exception):
            client.prepare(offer, connection_active=lambda: False)
        self.assert_preserved()


if __name__ == "__main__":
    unittest.main()
