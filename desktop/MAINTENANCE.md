# Maintenance, distribution and external review plan

Status: build preparation verifies pinned upstream signatures and checksums.
Publisher Authenticode signing and an authenticated automatic update channel
are planned, not delivered by the 0.1.2 usability release.

16 November implementation: authenticated update verification, safe separate
staging, Windows cache-only signature checks and signed publication tooling are
implemented in source. See UPDATE-SECURITY.md for test evidence and activation
gates. A production root/certificate, live repository, desktop flow and next-launch
activation helper remain to be provisioned/integrated; the public app is unchanged.

## Current trust boundary

The controller starts upstream Tor and an unmodified Tor Browser. Tor SOCKS and
control listeners bind to loopback. The route check uses remote DNS via SOCKS
and certificate-checked HTTPS. No automatic direct-network retry is provided.
This protects only traffic sent through this managed route, not every Windows
app. Local malware, device forensics and signed-in website identity are outside
the controller's protection. In-memory summaries are minimized, not anonymous.

## Release checklist and owner

### Run the upstream version review before release preparation

From `desktop/`, run `python check_upstream.py --output review-YYYYMMDD.json`.
The command contacts the official Windows x64 release feed and expert-bundle
download page on the maintainer's machine. It never runs inside the user app,
downloads executables, modifies runtime pins or interrupts a connection. It
preserves prior reports by refusing to overwrite an output file.

Exit 0 means both published stable versions match the current pin. Exit 2 means
review is required: a newer version, inconsistent upstream versions, metadata
older than the current pin, or an unsuccessful check. A failed lookup is never
reported as current. Version comparison does not replace security-advisory
review or signature/checksum verification in `prepare_runtime.py`.

The 16 November 2026 review matched Tor Browser and Tor Expert Bundle 16.0.1.
Seven fixture tests cover version/platform validation, signature-link presence,
numeric sorting, alpha exclusion, unexpected origins and redirect boundaries.
This is maintainer tooling, not an automatic or authenticated update channel.

The ArgoDelta/USAFE maintainer owns release review. Review upstream Tor Browser
release/security announcements at least weekly and on each release preparation;
record the version and date reviewed. Prioritize security fixes rather than
waiting for a new feature release. Replace runtime pins only after checking the
official detached signature and independently recorded release checksum.

- Build in an isolated environment with pinned build dependencies.
- Run unit/lifecycle tests and both actual transport smoke tests.
- Check English/Turkish, narrow layout, failure guidance, cancellation and export.
- Extract a fresh verified browser; never package a used browser profile.
- Preserve upstream license notices, source version, versioned release notes and
  an inventory of bundled files. A checksum alone is not publisher authentication.
- Keep previous releases available for diagnosis; never recommend rollback to a
  known-vulnerable dependency. Write a migration note for changed state formats.
- Record independent findings and fixes in a public advisory without private
  participant details or bridge addresses.

## Authenticated update design (stage 2)

Use a reviewed update framework rather than inventing a signature protocol.
Evaluate The Update Framework (TUF) for signed metadata, expiry, delegated trust,
key rotation and rollback/freeze resistance. Establish the publisher identity
and obtain a suitable code-signing certificate before claiming signed Windows
releases. Do not create a signing key and imply an independent trust identity.

The app should show the update version, source and download size before the user
initiates retrieval. Route update requests through a verified Tor connection
when available; never silently fetch directly after failure. Keep the current
runtime in use until the session ends. Stage an update separately, verify its
metadata and files before execution, and use an atomic switch on next launch.
If validation or installation fails, preserve the existing installation.

Required tests: invalid signature, wrong platform, changed artifact, expired
metadata, replayed/older metadata, key rotation, oversized download, interrupted
download/install, active-session update attempt, and unreachable update source.
Review Tor Browser's own update lifecycle separately from the bundled Tor Expert
Bundle; the browser updating does not update the controller's runtime.

## External review brief (stage 4)

Review bridge input parsing; generated torrc; file permissions and crash residue;
control-cookie handling; process ownership and cancellation races; inherited
environment; runtime integrity boundary; custom URI launcher argument handling;
update design; no-direct-fallback behaviour; and UX claims about protection.

Ask reviewers for reproducible findings, severity and remediation verification.
Do not label internal unit tests an independent audit. Budget for external review
and re-testing in a funding proposal; no reviewer has been commissioned yet.

## References

- https://support.torproject.org/tor-browser/getting-started/verifying-tor-browser/
- https://aus1.torproject.org/torbrowser/update_3/release/download-windows-x86_64.json
- https://download.torproject.org/tor/
- https://theupdateframework.io/
