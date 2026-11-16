# USAFE Connect update and signing infrastructure

Implemented 16 November 2026. This is a tested source component, not an enabled
production updater. Public Windows 0.1.2 is unchanged. No production signing keys
or certificates have been created, purchased or enrolled.

## Completed and verified

- `secure_updates.py`: explicit checks using python-tuf 7.0.1 with an embedded
  trusted root, persistent metadata and a Windows process lock. TUF validates
  role signatures, expiry, metadata rollback and threshold root rotation.
- Fixed product/platform/channel and exact signed target; a release must be newer
  than the installed version. Preview exposes version, source, size and digest.
  Preparation refreshes metadata and rejects an offer changed since preview.
- Explicit direct-network opt-in or SOCKS5h over a local Tor port. Environment
  proxies are ignored; redirects, direct fallback and automatic retries are not
  used. Downloads are cancellable, time bounded and size bounded.
- Archive path, duplicate, link and expansion checks. Verified packages are
  extracted separately and renamed into a versioned directory only after checks.
  The current installation is never replaced or launched by this component.
- `windows_signature.py`: WinVerifyTrust with cached-only certificate retrieval,
  revocation checking, pinned signer identity and a verified timestamp. Missing
  cached trust information fails closed. Windows verification does not bypass
  the selected Tor route with automatic certificate-network requests.
- `sign_windows_release.ps1`: signs a fresh output copy via an existing Windows
  certificate/HSM provider and SignTool, SHA-256 and RFC 3161 timestamp. Verifies
  signer/timestamp before promoting the result. No password or private key is
  placed on a command line. This maintainer operation explicitly contacts the
  configured timestamp service and may use Windows online trust checks.
- `publish_update.py`: verifies a signed package, consumes externally held keys,
  checks authorized role signatures and prepares a consistent-snapshot repository
  publication delta. It refuses existing output and reused metadata sequences.
  It neither generates keys nor uploads files. Private PEM inputs must be
  encrypted and outside the checkout/publication directory.

## Reproduce verification

Use Python 3.12 on Windows in a dedicated virtual environment:

```powershell
python -m venv C:\path\to\update-env
C:\path\to\update-env\Scripts\python.exe -m pip install -r requirements-updates.txt
C:\path\to\update-env\Scripts\python.exe -m unittest discover -v
```

Result on the implementation machine: 59 tests passed, including 21 new update
and publication tests. TUF tests use real Ed25519 signatures and ephemeral
in-memory keys; package signature acceptance in fixture tests uses an injected
verifier because their synthetic EXE is not a Windows program. Separately, the
native Windows verifier accepted the existing signed Python/Chrome executables
and rejected the unsigned USAFE 0.1.2 executable. No synthetic certificate was
added to the Windows trust store. Current ZIP's 1,231 paths passed extraction
policy checks. This is internal testing, not independent security certification.

## Release trust setup before enabling users' updates

1. Obtain the publisher signing service/certificate and define the authorized
   signing approver. Only sign our controller, not re-sign upstream Tor binaries.
2. Provision three independent offline root keys with a 2-of-3 threshold. Store
   recovery copies separately from this computer and the public repository.
   Use separate targets/snapshot/timestamp keys; root keys do not belong in CI.
   Prefer hardware-backed signing. The current PEM ceremony adapter is for a
   controlled offline machine, not an always-online signing daemon.
3. Create and independently verify the signed TUF root. Embed its public bytes
   and reviewed certificate pins in a new Authenticode-signed app release.
   Do not download the initial root from the same update server at first launch.
   The portable bundle is user-writable; local malware can replace it. Stronger
   local tamper resistance needs a protected installation location.
4. Configure an HTTPS repository with stable URLs and no redirects. Publish the
   hash-named ZIP and numbered metadata before `timestamp.json`; retain the
   complete numbered root history. Update timestamp metadata before 48 hours.
   Root/targets keys must remain separate from online timestamp renewal. Set up
   operational ownership and expiry monitoring before opening the channel.
5. Wire the desktop EN/TR preview/download flow to this client. Obtain the SOCKS
   port only from a live verified `TorSession`; never silently choose direct.
   Keep UI operations off the Tk thread and serialize session/handoff actions.
6. Implement and test the **next-launch activation helper** and launcher migration
   on a clean Windows machine. Current code returns a verified, separately staged
   EXE; it deliberately does not execute it or switch the current installation.
   No active Tor/browser session may be replaced. Retain the previous working
   folder on failure; never auto-downgrade to a known-vulnerable version.
7. Test a real signed release end to end, including expired trust caches, key and
   certificate rotation, system clock problems, interrupted handoff, browser
   processes still running and disk exhaustion. Request independent review.

## Maintainer commands after credentials are provisioned

Run `sign_windows_release.ps1 -?` for its explicit input/output, SignTool path,
certificate thumbprint and timestamp service parameters. Use the signed output
as the controller EXE before assembling the ZIP/inventory; never alter an already
published ZIP. `assemble_release.py` includes the update tools and dependency
requirements in Source in subsequent packages.

Run `python publish_update.py --help` for publication arguments. Role-key paths
point to encrypted files outside the checkout. Passphrases are requested locally
without echo. Initial publication requires `--initial --sequence 1`; subsequent
publications require the previous signed timestamp and an increasing sequence.
No production example secret or root is bundled.

## Rotation and incident handling

- A new root must satisfy both old and new thresholds and increment by exactly
  one; publish each intermediate root and retain old public metadata. Tests cover
  rejecting a rotation with only one of the new threshold signatures.
- Rotate a Windows certificate by first distributing an authenticated release
  that permits the reviewed replacement certificate, then sign subsequent EXEs
  with it. Do not accept arbitrary new certificates from update-server data.
- A stale/expired timestamp disables installation rather than trusting a mirror.
  Investigate compromised signing roles, rotate with offline root authorization,
  publish an advisory and ship a higher safe application version. If root trust
  itself is compromised, use a separately authenticated recovery distribution.

## Primary references

- https://theupdateframework.readthedocs.io/en/stable/api/tuf.ngclient.updater.html
- https://theupdateframework.github.io/specification/latest/
- https://learn.microsoft.com/en-us/windows/win32/api/wintrust/ns-wintrust-wintrust_data
- https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options

## Signing-provider decision

Microsoft's current individual Artifact Signing onboarding is limited to the US
and Canada, so do not assume availability for a Türkiye-based individual.
SignPath Foundation offers a free OSS route subject to project review; its
certificate identifies SignPath Foundation and its policy has special limits
for security tools. Ask specifically about this Tor bridge controller before
making an eligibility claim. Certum offers individual open-source signing as a
paid alternative subject to identity/project checks. No provider accepted USAFE
and no terms were agreed through this implementation work.

- https://signpath.org/terms
- https://support.certum.eu/en/code-signing-required-documents/
