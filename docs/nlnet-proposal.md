# NLnet / NGI Zero Proposal Draft — USAFE

> Source: https://nlnet.nl/propose/ (fields verified 2026-07-29)
> **Status: DRAFT, not submitted.** NLnet's general/open call is paused as of
> this writing; only NGI Taler and NGI Fediversity are open (neither fits),
> closing 2026-08-01. The general fund reopens "after summer 2026" under the
> reorganized "Open Internet Stack" effort. This draft is prepared now so
> submission can happen the day the call reopens.
>
> Deliberately scoped DIFFERENT from USAFE's pending OTF Internet Freedom
> Fund application (#22839, concept-note stage) — see "Other funding sources"
> below for why, and why that's honest rather than double-dipping.

---

## Your name
Cihan Demirpençe

## Email address
ussstarfairy@gmail.com

## Organisation
None — applying as an individual.

## Country
Turkey

## Proposal name
USAFE Detectors — reusable, standalone privacy/censorship detection modules extracted from USAFE

## Website / wiki
https://github.com/chndemirpence/usafe

## Abstract

USAFE is a free, open-source, 100% client-side browser toolkit (live, MIT-licensed, github.com/chndemirpence/usafe) combining censorship/blocking detection, browser fingerprint/tracking analysis, and end-to-end encrypted communication in one no-account, no-server application. Building it surfaced two techniques that are useful well beyond this one app, and are not, as far as our research found, available as maintained standalone components anywhere: (1) a DNS-over-HTTPS resilience checker that treats "every resolver failed" as a distinct *inconclusive* state rather than a false "clean" result — a real bug we shipped and fixed ourselves (a wrong resolver port plus no timeout could hang forever or silently misreport safety); (2) a canvas-fingerprint noise detector that draws an identical canvas scene twice and compares hashes to detect whether a browser is already applying anti-fingerprinting randomization (Brave, Tor Browser, Firefox resistFingerprinting) — distinguishing a *protected* browser from an unprotected one, which most fingerprinting demos don't do (they flag 100% of browsers as "at risk" regardless of existing protection).

This proposal is to extract both into **USAFE Detectors**: two small, independently documented, dependency-free JavaScript modules, published to npm, so other privacy/security tools can adopt battle-tested detection logic instead of re-deriving it (and re-making the same mistakes we made and fixed).

## Prior involvement

I am the sole author and maintainer of USAFE. I have ~34 years of solo programming experience (coding since 1992, certified 1991), and have built and shipped several other privacy/security-adjacent tools this year, including MetaSafe (metadata-scrubbing toolkit, github.com/chndemirpence/metasafe) and two AGPL-licensed commons projects, Recourse and Attune (github.com/chndemirpence/recourse, /attune), also prepared for NLnet funding separately.

## Requested Amount (in Euro)

€16,000

## Budget usage explanation

- €7,000 — extracting the DoH-resilience-checker (resolver comparison, timeout handling, the "inconclusive vs consistent" distinction) into a standalone, tested, documented module usable outside USAFE.
- €5,000 — extracting the canvas-noise fingerprint detector into a standalone module, including a small test harness that can be run against multiple browser configurations (stock Chromium, Brave, Tor Browser) to validate the protected/unprotected distinction holds.
- €4,000 — documentation, worked examples, and outreach to adjacent open-source privacy projects (browser extensions, EFF/AmIUnique-adjacent tooling) as potential adopters.

## Other funding sources

Yes — full disclosure. USAFE also has a pending concept-note application to the Open Technology Fund's Internet Freedom Fund (#22839, submitted 2026-07-29, no decision yet), requesting $24,000 USD for: an independent security audit of USAFE's ECDH/AES-GCM secure-communication module, resilience hardening of the *application's* censorship detector, and fingerprint-scoring calibration against real population data.

These two asks are deliberately scoped not to overlap: OTF's ask is about auditing and hardening the *end-user application* (specifically its cryptography and its own DNS test methodology). This NLnet ask is about extracting two specific, already-working *detection techniques* into standalone, reusable, published modules other projects can adopt — a different artifact, a different audit surface. If both were funded, no milestone here would duplicate a milestone there. If asked, I will provide the OTF concept note in full for cross-reference.

## Comparison with existing efforts

OONI Probe is the gold standard for censorship measurement but is a native application, not an embeddable library, and doesn't address the specific "resolver never responds" failure mode this proposal targets (which is a browser-context problem OONI's native tooling doesn't have to solve the same way). EFF's Cover Your Tracks and AmIUnique are excellent fingerprint *diagnostic* tools but, as far as our research found, neither publishes the underlying "is this specific signal noise-protected" check as a standalone, reusable module — they compute a result for their own website, not a library others can import. USAFE Detectors fills that specific gap: two narrow, single-purpose, already-proven-in-production modules, not a competing full application.

## Technical challenges

The DoH module's hardest problem, already solved once inside USAFE and needing to be preserved in extraction: distinguishing "all resolvers unreachable" (itself a meaningful signal in a censorship context, since DoH endpoints are commonly blocked) from "DNS is genuinely consistent," without over-claiming certainty either way — plus avoiding a second real failure mode we found empirically during testing: CDN-backed domains can legitimately return *different* IPs to different resolvers due to normal geographic anycast routing, which a naive comparison would misreport as "manipulation." The canvas-noise module's hardest problem is picking a draw sequence that reliably produces byte-identical output on an unprotected browser across repeated calls (any incidental non-determinism in the drawing itself would produce false "protected" readings) - solved by keeping the test scene simple and deterministic, but this needs to be validated against a wider set of real browser/GPU combinations than we've had time to test so far.

## Ecosystem description

The natural adopters are other privacy-tool authors: browser extension developers who want a DNS-manipulation check without re-implementing resolver comparison and timeout handling from scratch, and anyone building fingerprinting-awareness tools who wants to correctly credit already-protected browsers instead of flagging every visitor as equally at risk. Both modules are narrow and single-purpose by design, matching NLnet's stated preference for small reusable components over monolithic applications. I intend to reach out to maintainers of comparable open-source privacy-testing tools once each module has a stable 1.0 API.

## Generative AI usage

I have used generative AI (Claude, Anthropic) substantially in this project's development: for structural code review that found real bugs (the ECDH wire-format flaw, the DNS timeout/wrong-port issue, and an audio-fingerprinting race condition, all described and fixed in the USAFE repository's commit history), for implementation of several modules, and for drafting this proposal text itself, which I have reviewed and edited. All claims of fact in this proposal (bugs found, test results, architecture) reflect real, verified work, not invented material.

## PGP
Not provided.
