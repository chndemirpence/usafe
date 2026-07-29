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

USAFE is a free, open-source, 100% client-side browser toolkit (live, MIT-licensed, github.com/chndemirpence/usafe, commit [02237c8](https://github.com/chndemirpence/usafe/commit/02237c8)) combining censorship/blocking detection, browser fingerprint/tracking analysis, and end-to-end encrypted communication in one no-account, no-server application. Building it surfaced two techniques not currently available anywhere as maintained, standalone components:

1. A **DNS-over-HTTPS resilience checker** that treats "every resolver failed" as a distinct *inconclusive* signal rather than a false "clean" result. This closes a real bug we shipped and caught ourselves during structured testing: a wrong resolver port plus no request timeout meant a single unresponsive resolver could hang the entire check forever, or (if it failed fast) silently report "DNS is consistent" when it hadn't actually been checked at all — the worst possible failure mode for a censorship-detection tool, since DoH endpoints are exactly what many censorship regimes block.
2. A **canvas-fingerprint noise detector** that draws an identical scene twice and compares the resulting hashes to detect whether the browser is already applying anti-fingerprinting randomization (Brave, Tor Browser, Firefox `resistFingerprinting`) — correctly distinguishing an *already-protected* browser from an unprotected one, which most fingerprinting demos don't do (they flag effectively every visitor as "high risk" regardless of existing protection, which is what USAFE itself did before this fix).

This proposal extracts both into **USAFE Detectors**: two small, independently documented, dependency-free JavaScript modules published to npm, so other privacy/security tools can adopt already-debugged detection logic instead of independently re-deriving it — and, based on what we found in our own code, re-making the same mistakes.

## Prior involvement

I am the sole author and maintainer of USAFE, with ~34 years of solo programming experience (coding since 1992, certified 1991). I built USAFE's censorship detector, fingerprinting analysis, and ECDH/AES-GCM secure-communication module myself, including the QR-code key exchange and the offline-capable service worker. As with MetaSafe (see below), I do not treat "runs without throwing an error" as proof a security-relevant tool works — a structural review and testing pass on USAFE caught the two issues described above plus two more (an ECDH encryption mode that could be used to encrypt a message but never decrypt it, because the wire format didn't include the sender's public key needed to re-derive the shared secret; and a non-deterministic audio-fingerprinting race condition), all fixed and present in the current codebase (commit [02237c8](https://github.com/chndemirpence/usafe/commit/02237c8)).

I have shipped one other privacy tool this year using the same methodology: MetaSafe (metadata-scrubbing toolkit, github.com/chndemirpence/metasafe), where the identical adversarial-testing approach caught a TIFF metadata bug and an SVG cleaner bug, documented and fixed in that repository's history — also proposed to NLnet separately as MetaSafe Core. I have also prepared two AGPL-licensed commons projects for NLnet funding, Recourse and Attune (github.com/chndemirpence/recourse, /attune).

## Requested Amount (in Euro)

€16,000

## Milestones

**Milestone 1 — DoH-resilience-checker extraction (4–5 weeks, €7,000).**
Extract the resolver-comparison, timeout-handling, and "inconclusive vs. consistent" logic into a standalone, tested module with a stable public API. Include the CDN-anycast false-positive case we found empirically during testing (a domain can legitimately return different IPs to different resolvers due to normal geographic routing, which a naive comparison misreports as "manipulation") as a documented, tested edge case, not an afterthought.
*Deliverable: public alpha on npm; test suite covering the timeout, wrong-response, and CDN-anycast cases specifically.*

**Milestone 2 — Canvas-noise-detector extraction and cross-browser validation (4–5 weeks, €5,000).**
Extract the double-draw/hash-compare detector into a standalone module, and build a small validation harness that runs it against multiple real browser configurations (stock Chromium, Brave, Tor Browser) to confirm the protected/unprotected distinction holds beyond the one environment it was originally verified in.
*Deliverable: public alpha on npm; cross-browser validation results published alongside the release.*

**Milestone 3 — Documentation and outreach (2–3 weeks, €4,000).**
API documentation and worked examples for both modules, plus direct outreach to maintainers of comparable open-source privacy-testing tools (starting with browser-extension developers and fingerprinting-awareness projects) once both modules have a stable 1.0.
*Deliverable: published docs; ≥1 real external adopter or a documented integration attempt if adoption takes longer than the funded period.*

## Other funding sources

Yes — full disclosure. USAFE also has a pending concept-note application to the Open Technology Fund's Internet Freedom Fund (#22839, submitted 2026-07-29, no decision yet), requesting $24,000 USD for: an independent security audit of USAFE's ECDH/AES-GCM secure-communication module, resilience hardening of the *application's* censorship detector, and fingerprint-scoring calibration against real population data.

These two asks are deliberately scoped not to overlap. OTF's ask audits and hardens the *end-user application* — specifically its cryptography and its own DNS test methodology. This NLnet ask extracts two already-working *detection techniques* into standalone, published, reusable modules other projects can adopt — a different artifact, a different audit surface, and no shared milestone between the two. I will provide the OTF concept note in full for cross-reference on request.

## Comparison with existing efforts

OONI Probe is the gold standard for censorship measurement, but it is a native application, not an embeddable library, and does not need to solve the specific "a resolver never responds, from inside a browser tab" failure mode this proposal targets — that is a browser-context problem OONI's native tooling sidesteps entirely by not running in a browser. EFF's Cover Your Tracks and AmIUnique are excellent fingerprint *diagnostic* websites, but as far as our research found, neither publishes the underlying "is this specific signal already noise-protected" check as a standalone, reusable module — they compute a result for their own site, not a library a third party can import and depend on. USAFE Detectors fills that specific, narrow gap: two single-purpose modules already proven inside a working application, not a competing full product.

## Technical challenges

The DoH module's hardest problem, already solved once and the reason Milestone 1 explicitly tests for it: distinguishing "all resolvers unreachable" (itself a meaningful signal in a censorship context, since DoH endpoints are commonly blocked) from "DNS is genuinely consistent," without over-claiming certainty in either direction — and separately, not misreporting normal CDN anycast geographic routing as manipulation, a false positive we hit empirically during our own testing on a major CDN-backed domain. The canvas-noise module's hardest problem is ensuring the draw sequence produces byte-identical output on an unprotected browser across repeated calls — any incidental non-determinism in the drawing itself would produce false "protected" readings — which is why Milestone 2 is scoped as extraction *plus* multi-browser validation, not extraction alone; the technique has so far only been verified in the one environment it was built and tested in.

## Ecosystem description

The natural adopters are other privacy-tool authors: browser-extension developers who want a DNS-manipulation check without re-implementing resolver comparison, timeout handling, and the CDN-anycast false-positive fix from scratch, and anyone building fingerprinting-awareness tools who wants to correctly credit already-protected browsers instead of flagging every visitor as equally at risk (the exact mistake USAFE itself made before this fix). Both modules are narrow and single-purpose by design, matching NLnet's stated preference for small reusable components over monolithic applications. Concrete engagement plan for Milestone 3: named outreach to maintainers of comparable open-source privacy-testing projects once each module has a stable, validated 1.0 — not speculative interest, but outreach backed by a working published package.

## Generative AI usage

I have used generative AI (Claude, Anthropic) substantially in this project's development: for structural code review that directly found the ECDH wire-format flaw, the DNS timeout/wrong-port issue, and the audio-fingerprinting race condition described above, for implementation of several modules, and for drafting this proposal text, which I have reviewed and edited myself. Every factual claim in this proposal — the bugs found, the commit they're fixed in, the architecture — is real and independently checkable in the public repository; nothing here was invented for the purpose of this application.

## PGP
Not provided.
