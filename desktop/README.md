# USAFE Connect — Windows preview 0.1.2

USAFE Connect adds an actual bridge-based Tor connection to the USAFE toolkit.
It starts the official Tor client, verifies HTTPS egress, and opens the official
Tor Browser with that connection. The browser opens the Tor connection checker
and the existing USAFE web toolkit in separate tabs.

## Use the Windows package

1. Extract the complete folder; keep `_internal` beside `USAFE Connect.exe`.
2. Open `USAFE Connect.exe`. It starts in English. Choose **Türkçe** in the upper right to switch languages.
3. Leave **Snowflake** selected and click **Connect**. Initial connections can take
   several minutes. **Tor connection verified** means both Tor bootstrap and an
   HTTPS request through its SOCKS endpoint succeeded.
4. Click **Open Tor Browser**. The included, unmodified portable Tor Browser is
   selected automatically. Close an already running Tor Browser before this step.
5. Browse inside that window. **Disconnect** closes the managed Tor connection.

If a connection needs attention, the status card explains the next step in your
chosen language. **Try obfs4 instead** finishes the old session before starting
the alternative. **Set up a fresh bridge** switches to Custom and waits for your
input. Runtime integrity or profile ownership problems do not trigger transport
switching. The status shows elapsed time and the age of the last successful
route check; verification is a point-in-time check, not continuous monitoring.

**Offline connection guide** is bundled in English and Turkish and works without
internet access. **Save connection summary** first opens an exact preview with
optional fixed-choice feedback. Saving never sends it to ArgoDelta or anyone else.

To open the desktop window from [USAFE](https://www.argodelta.com/tools/usafe/#connect),
click **Enable website launch** in the desktop app once. Then use **Open Windows app**
under **Connect** on the website. If you move the extracted folder, enable website launch
again from the new location. You choose when to connect in the desktop window.

If Snowflake cannot connect on a particular network, choose **obfs4** or **Custom**
after disconnecting. Custom accepts one to eight obfs4/WebTunnel bridge lines
obtained through a trusted distributor. It does not accept Tor configuration
directives. Default bridges come from the signed Tor Expert Bundle, rather than
an independently maintained USAFE bridge list.

The connection serves the Tor Browser launched here. It does not change the
Windows system proxy, route Chrome or other apps, or create a system VPN.
No direct-network fallback is implemented. Connection verification contacts
`check.torproject.org` over Tor; opening the browser also loads the USAFE toolkit.

## Data on the device

The controller uses `%LOCALAPPDATA%\USAFE\Connect` for Tor state and a per-profile
process lock. Tor's guard/directory state is retained between sessions. Private
bridge configuration and the control cookie are removed on a normal disconnect;
an abrupt power loss can leave temporary files behind. This is not a disk
forensics protection feature. A private bridge address must still be contacted
to establish a connection.

Raw Tor/transport logs are discarded. The app keeps up to ten attempt summaries
in memory until exit. The export contains version, platform, method, progress,
rounded elapsed seconds, a fixed issue/outcome category, verification state,
scope and optional fixed-choice feedback. It excludes IP addresses, bridge lines,
browsing URLs, control cookies, raw exceptions and precise timestamps. There is
no background telemetry. A saved summary still reveals use of USAFE; review it
and choose whether to share it. No participant recruitment or field results are
implied by adding this export.

## Build from source

Build on Windows 10/11 x64 with Python 3.12+, Windows `curl.exe`, GnuPG and an
isolated Python build environment. Run commands from this directory:

```powershell
python prepare_runtime.py --cache C:\build-cache\usafe
python -m unittest discover -v
python -m pip install -r requirements-build.txt
python build_windows.py --dist dist\windows-0.1.2-x64
```

`prepare_runtime.py` pins Tor Expert Bundle 16.0.1, its SHA-256 digest and the Tor
Browser Developers primary signing fingerprint. It verifies the detached
signature before extraction, refuses a nonempty destination, and records file
digests. The controller checks critical executable/configuration digests before
each connection. These digests detect unexpected file changes; they do not make
an unsigned USAFE build into a publisher-signed release.

The executable is generated in `dist/windows-0.1.2-x64/USAFE Connect/`. Put the
verified portable Tor Browser beside the executable in `Tor Browser/`, with
`Browser/firefox.exe` inside. The preparation script can verify and extract it
with `--browser-dir` while preparing a fresh runtime.

Live tests are explicit and use the actual network:

```powershell
python smoke_connect.py --mode snowflake --state C:\test-state\snowflake --report C:\test-state\snowflake.json
python smoke_connect.py --mode obfs4 --state C:\test-state\obfs4 --report C:\test-state\obfs4.json
```

These tests verify HTTPS Tor egress, the loopback listener and port closure on
disconnect. Local-network success does not establish availability under every
censorship regime. A new session should be used after stopping a TorSession.

## Integration and next release

The implementation/evidence stages are in [ROADMAP.md](ROADMAP.md), the voluntary
user study in [PILOT.md](PILOT.md), and the update/review plan in
[MAINTENANCE.md](MAINTENANCE.md). These distinguish completed development from
work requiring participants, a signing identity or an independent reviewer.

The MIT-licensed controller is separate from the existing browser-only USAFE
modules, which remain intact. Tor/transport implementations are upstream projects;
the controller does not introduce its own encryption or camouflage protocol.
The runtime's upstream notices are preserved under `_internal/runtime/docs/`.
Tor Browser remains a separate, unmodified upstream distribution.

Android is the next platform. The initial Android architecture should reuse Tor
Project/Guardian Project components, preserve the distinction between Tor Browser
and device/app VPN routing, and test network changes and Android service lifetime
on a physical phone. Do not label an Android build connected solely because a
service started; require an actual route check.

Before a broad public launch: add publisher code signing, an authenticated update
channel for the controller/runtime, independent review of the launcher/lifecycle,
and tests on restricted networks with consenting participants. The embedded Tor
Expert Bundle is pinned and does not auto-update itself. Refresh it through a new
signature-verified build when upstream security updates are released. Tor Browser
retains its own upstream update mechanism.

## Primary references

- [Tor bridges and pluggable transports](https://support.torproject.org/little-t-tor/circumvention/using-bridges/)
- [Snowflake](https://snowflake.torproject.org/)
- [Verify Tor signatures](https://support.torproject.org/tor-browser/getting-started/verifying-tor-browser/)
- [Official Tor release artifacts](https://dist.torproject.org/torbrowser/16.0.1/)
- [Tor external process environment](https://tpo.pages.torproject.net/core/doc/rust/arti/)
- [PyInstaller external process environment](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html)

USAFE Connect is an ArgoDelta/USAFE integration, not an official Tor Project product.
