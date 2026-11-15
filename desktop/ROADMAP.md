# USAFE Connect: user-centred internet freedom roadmap

Prepared 15 November 2026. This is an implementation and evidence plan, not an
OTF award or a claim that a funding decision is assured.

## Intended contribution

Help people with limited technical experience establish, understand and recover
a bridge-based Tor browsing session, with English/Turkish guidance available
offline. Reuse maintained Tor components. Measure whether the integration
improves task completion rather than treating extra features as impact.

Tor Browser already has Connection Assist. USAFE must demonstrate an additional
benefit for a defined community: comprehensible recovery, offline onboarding,
and a coherent path from access to USAFE's existing file-sharing preparation
tools. This is a hypothesis to test against Tor Browser, not established novelty.

## Stages and completion gates

| Stage | Deliverables | Completion evidence |
|---|---|---|
| 1. Understand and recover | Localized actionable error states, deliberate alternative-bridge selection, elapsed/last-checked indicators, offline guide, previewable local feedback export | Regression tests; desktop checks in both languages and narrow window; real connection smoke test; explicit failed/stop cases |
| 2. Maintain and distribute | Dependency inventory; regular upstream release review; publisher signing; authenticated update design with rollback/replay protections and signing-key lifecycle | Signed release verified on clean Windows; tampered/expired/older update metadata rejected; interrupted upgrade preserves working install |
| 3. Learn from users | Voluntary small pilot; baseline comparison with Tor Browser; observed connection and recovery tasks; minimized aggregate evidence | Consent, actual task results and denominators, documented improvements; controlled tests separated from field results |
| 4. Review and contribute | External review of launcher/session lifecycle/update channel; reusable tests and translated recovery resources; upstream issues or patches when relevant | Reviewer findings and fixes; public reusable artifacts; no unsupported endorsement claims |
| 5. Android | Tor/Guardian component assessment; lifecycle and network-change prototype; clear app-level routing scope; localized recovery | Physical-phone tests including Wi-Fi/mobile transitions, process death, background restrictions and no direct fallback |

Stages 2–4 overlap. Android follows evidence that the workflow helps users; do
not hold the Windows pilot until Android is complete. Broad distribution should
include the update and review work. Do not silently replace an active connection.

## Stage 1 scope

- Retain the existing bridge implementations and explicit Connect action.
- Show safe, actionable guidance rather than raw exceptions or bridge details.
- Suggest another method only for connection failures, never for changed runtime
  files or competing sessions. Stop the old session before a new attempt.
- Show the last successful verification age. A prior success is not continuous
  proof that the network still works. Recheck remains explicit.
- Include an offline connection guide and local session summary with optional
  fixed-choice feedback. No automatic upload, IP, bridge, URL, account identifier,
  free-text notes, or precise timestamps. Keep attempts in memory, capped at ten.
- Never expand proxy scope or claim device-wide VPN protection.

## Pilot proposal (targets, not existing evidence)

Invite 5–10 consenting adult volunteers. Existing USAFE users may be invited,
but do not count their prior toolkit usage as Connect circumvention evidence.
Start on ordinary networks and controlled restrictions. Field participation in
restrictive environments requires an appropriate local partner and a separate
risk assessment; do not ask volunteers to seek risk for a funding application.

Tasks: find connection entry point; establish a verified session; open Tor
Browser; explain what is routed; recover from a simulated blocked bridge; export
a summary if desired. Compare the same tasks with current Tor Browser and vary
task order to reduce learning bias. Distinguish integration benefit from Tor's
underlying transport performance.

Record aggregate completion rate with denominator, time-to-verified connection,
recovery success, assistance needed and scope comprehension. Suggested usability
target: at least 80% complete the normal connection task without facilitator
intervention. Report actual results even when below target; small samples do not
establish country-level reliability. No invented participants or testimonials.

## OTF evidence package

1. A specific community problem with consented, anonymized examples.
2. A comparison with existing tools and measured incremental benefit.
3. Versioned source/build instructions and repeatable test results.
4. A threat/scope model, external review plan and incident/update owner.
5. Milestones with cost estimates tied to engineering, research and review work.
6. Maintenance and community contribution plan beyond the funding period.

Funding can support unfinished development. Clearly distinguish working features,
locally tested behaviour, planned work and independently validated evidence.

## References

- OTF Internet Freedom Fund: https://www.opentech.fund/funds/internet-freedom-fund/
- OTF evaluation worksheet: https://docs.opentech.fund/otf-application-guidebook/appendix-iii-evaluation-worksheet
- OTF UX & Discovery Lab: https://www.opentech.fund/labs/uxd-lab/
- Tor Connection Assist: https://support.torproject.org/tor-browser/circumvention/connecting-from-censored-regions/
- Tor bridges: https://support.torproject.org/little-t-tor/circumvention/using-bridges/

## Progress

- Stage 1: implemented and locally verified in 0.1.2; see RELEASE-NOTES-0.1.2.md.
- Stage 2: offline release inventory implemented and tested; signing and
  authenticated updates remain planned.
- Stages 3–5: protocols/plans prepared. External reviewers, code-signing identity, participants and
  a physical Android device have not been obtained by writing this plan.
