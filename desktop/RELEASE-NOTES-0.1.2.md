# USAFE Connect 0.1.2 — guided connection recovery

Local Windows preview, 15 November 2026. Public 0.1.1 download remains unchanged
until a separate release publication. This release adds usability and local
evidence features; it does not claim an OTF award or independent security audit.

## Changes

- English default and Turkish option retained, with localized recovery guidance.
- Elapsed connection time, meaningful progress stages and last verification age.
- Deliberate alternate-method action after a timeout/route failure. The previous
  session stops before the next starts. Custom bridges wait for user input.
- Distinct guidance for incomplete/changed runtime, profile already in use,
  invalid bridge input and failed route verification. Raw exceptions are not
  shown as connection guidance or exported.
- Bundled offline guide covering first connection, troubleshooting, scope and
  data handling. No network requests when opening the guide.
- Readable local summary preview with fixed-choice optional feedback, saved as
  the exact displayed text. Up to ten attempts in memory. No automatic upload.
- Updated status if the managed Tor process exits. A former verification cannot
  keep the Open Tor Browser button enabled after process death.
- Release inventory creation/checking for changed/missing/extra files, runtime
  integrity and accidental personal browser state. This is unsigned integrity
  evidence; it does not replace publisher signing or authenticated updates.

## Verification performed

- 31 automated regression tests passed (core, recovery/data minimization,
  Tk lifecycle and release inventory).
- Real Snowflake connection: HTTPS Tor verification succeeded in 15.7 seconds.
- Real obfs4 connection: HTTPS Tor verification succeeded in 16.3 seconds.
- Both smoke tests verified loopback listening and closed SOCKS port after stop.
- Packaged Windows app: actual connection verified; disconnect returned to
  disconnected state and disabled browser launch.
- Visual review: English and Turkish main screens, compact stacked layout,
  offline guide and readable summary preview. The final summary was inspected
  in English; translated recovery and dialog lifecycle were tested automatically.
- Official upstream Tor Expert Bundle and Tor Browser signatures and pinned
  archive checksums verified during package preparation. A fresh browser was
  extracted, not copied from a used profile.

These are local-network results, not restricted-country field evidence.
No external review or user pilot has been conducted for this release.

## Next stages

See ROADMAP.md, PILOT.md and MAINTENANCE.md. Publisher identity/code signing,
authenticated updates, consented user evidence and independent review remain
planned work. Android follows Windows recovery/usability validation.
