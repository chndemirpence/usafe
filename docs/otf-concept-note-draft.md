# OTF Internet Freedom Fund — Concept Note (USAFE)

> Kaynak: https://apply.opentech.fund/internet-freedom-fund-concept-note
> Bu taslak OTF'nin gerçek form alanlarına birebir uyacak şekilde hazırlandı (MetaSafe başvurusuyla aynı format).
> Her cümle gerçek, doğrulanmış çalışmaya dayanıyor — hiçbir şey uydurulmadı.

---

## Project Title

**USAFE — One Lightweight Toolkit for the Three Things OTF Actually Funds Most**

(Universal Security And Freedom Evaluator)

---

## Describe your project in 1-3 sentences.

USAFE is a free, open-source, 100% client-side browser toolkit that combines the three most common categories of internet-freedom tooling — censorship/blocking detection, browser surveillance and tracking analysis, and end-to-end encrypted communication — into a single installable, no-account, no-server application. Rather than asking an at-risk user to juggle a native measurement app, a separate fingerprint-testing website, and yet another encrypted-messaging tool, USAFE puts all three in one place, with every limitation of browser-based measurement disclosed honestly on the relevant tab rather than overclaimed. The working prototype is live, and its two most safety-critical components — the ECDH encryption flow and the DNS-manipulation test — were both caught mid-development shipping with serious, silent bugs (encryption that could never be decrypted; a test that could hang forever and report false safety) that were found and fixed through the same adversarial verification process used on our previous OTF submission, MetaSafe (#22833).

---

## What problem will your project address?

People trying to understand whether they're being censored, tracked, or unsafe online today have to go to three different places: a native app like OONI Probe for network interference (which most people never install), a diagnostic website like EFF's Cover Your Tracks for fingerprinting (which tells you the problem but gives you no way to act on it from the same page), and a separate secure-messaging tool for communication. Each is good at its one job. None of them is a single thing a non-technical, at-risk user can open once, in a browser tab, with no setup, and get all three.

We also want to be candid about two things we found while building this, because we think OTF's own review process is exactly where this kind of honesty belongs:

1. **Browser-based censorship measurement has a real, structural ceiling.** OONI's own announcement of "OONI Probe Web" states plainly that browser-based measurement has higher false-positive/negative rates than their native apps and is not a replacement for them — because a browser cannot see TCP resets or SNI-level filtering, the primary techniques national firewalls actually use, and cannot reliably distinguish "the state is blocking this" from "an ad-blocker is blocking this" or "a CORS policy is blocking this." USAFE's Censorship tab says this explicitly, rather than presenting a green/red result as if it were authoritative.
2. **A wrong DNS resolver URL and a missing timeout can turn a safety tool into a hazard.** During adversarial testing, we found that our DNS-manipulation test queried Quad9's resolver on the wrong port and had no timeout at all — meaning a single unresponsive resolver (exactly what happens when a censor blocks known DoH endpoints, which is common) could hang the entire test forever, or silently report "DNS is clean" when it wasn't reachable to check at all. Both are now fixed: the correct endpoint is used, every DNS query has a bounded timeout, and "every resolver failed" is now reported as *inconclusive*, never as *safe*.

The consequence of shipping either of these bugs unnoticed, for the people OTF serves, is a false sense of security at the exact moment they most need an accurate one.

---

## If this project is funded, what form will it take?

**Technical Development** — taking a working, open-source, three-module internet freedom toolkit from a rigorously self-tested prototype to a professionally audited, community-validated release.

---

## Give a brief overview of the activities in this project.

**Where the project stands today (already built and verified, not proposed):**
- Censorship & Blocking Detector: DNS-over-HTTPS comparison across three resolvers with an explicit "inconclusive" state (not a false "clean") when resolvers are unreachable, WebRTC IP-leak detection, site-reachability testing, and a VPN *leak* check honestly scoped as not detecting VPN presence itself.
- Surveillance & Tracking Detector: canvas/WebGL/audio/font fingerprinting that also detects anti-fingerprinting noise (drawing the same canvas twice and comparing hashes), so a privacy-hardened browser is correctly shown as protected instead of being flagged as "high risk" like every other browser.
- Secure Communication: password-based AES-256-GCM message encryption with optional expiry, ECDH key-pair encryption with QR-code key exchange, and file encryption — all client-side, keys ephemeral by default.
- A strict client-side architecture: the app works fully offline via a service worker, and the only network requests it ever makes are the Censorship module's own measurements (DNS resolvers, IP lookups, the sites being tested) — disclosed on the Privacy page, not hidden.

**What this funding accomplishes over a 2-3 month period:**

**Objective 1 — Independent security audit (Month 1).**
The Secure Communication module is the most safety-critical part of this application by nature — it performs real cryptography, not just measurement. Commission a third-party review of the ECDH/AES-GCM implementation, PBKDF2 parameters, and key-handling lifecycle. Deliverable: public audit report; patched release.

**Objective 2 — Strengthen the Censorship module's honesty and resilience (Months 1–2).**
Expand the DoH resolver set and add resilient fallback so a single blocked/misconfigured endpoint (as we found with Quad9) degrades gracefully rather than silently failing; study OONI's public methodology and measurement data more closely to see what, if anything, can be safely cross-referenced from a browser context without overstating what a browser can measure.

**Objective 3 — Calibrate the fingerprint uniqueness score against real data (Months 2–3).**
Replace the current uncalibrated heuristic scoring with a methodology referenced against a real, published population dataset (in the spirit of EFF's Cover Your Tracks and AmIUnique), so the percentage shown to a user reflects an actual entropy estimate rather than an arbitrary point system.

**Objective 4 — Real-world validation with the community it serves (Months 1–3).**
Structured testing with journalists and activists — including individuals I have direct, existing relationships with — using USAFE on their actual workflows. Incorporate findings into the interface and translations (currently English + Turkish).

**Objective 5 — Sustainability (throughout).**
Contributor documentation and a maintenance plan so the project continues beyond the funded period.

---

## Are there similar projects that exist already? How is your project different or complementary to those projects?

Similar tools: [OONI Probe](https://ooni.org/) (native network-interference measurement — the gold standard, but requires installing a separate app; USAFE's browser-based Censorship module is explicitly positioned as a lighter, always-available complement, not a replacement, and says so), [EFF's Cover Your Tracks](https://coveryourtracks.eff.org/) and [AmIUnique](https://amiunique.org/) (excellent fingerprint diagnostics, but diagnostic-only — neither gives the user an action to take from the same page), [PrivateBin](https://privatebin.info/) (zero-knowledge client-side-encrypted sharing, close in spirit to USAFE's password-based message encryption, but focused solely on text/paste sharing, not measurement or fingerprinting).

USAFE isn't trying to out-engineer OONI's native measurement stack or EFF's population-scale fingerprint database — it's filling the gap of "one lightweight, zero-setup tool that covers all three categories for the person who will never install a second app," while being explicit about exactly where its browser-based approach is weaker than the specialized native tools it complements.

---

## How long do you estimate activities will take?

**2 to 3 months.** The three modules already exist and work end-to-end; this funding covers an independent audit of the cryptography, methodological hardening of the two weaker modules (censorship measurement, fingerprint scoring), and real-world validation — not building the core product from scratch.

---

## How much funding do you estimate you will need? (In US Dollars)

**24000**

Itemized: Independent third-party security audit of the encryption module: $12,000. Developer time for Objectives 2–3 (resolver resilience, fingerprint calibration) over 2-3 months part-time: $8,000. Community testing — participant time/compensation for activist and journalist testers: $4,000.

---

## Who would benefit from this project?

Journalists, human rights defenders, activists, and ordinary people in repressive environments who want to understand whether their connection is being interfered with, how trackable their browser is, and who want to communicate sensitive information securely — without installing multiple separate tools or trusting a third-party server with any of it. The honest scope notices throughout the app are specifically aimed at people who might otherwise treat a green checkmark as a guarantee of safety.

---

## Where are your intended users, or audiences located?

Browser-based with no geographic restriction; the toolkit currently supports English and Turkish, matching the same censorship/surveillance-pressure regions referenced in our prior submission (Turkey/MENA, and more broadly anywhere internet filtering, tracking, or unsafe communication is a daily risk). I also have direct, existing relationships with activists who can test this in real conditions, the same community engaged for our MetaSafe submission (#22833).

---

## What is your name?

**Cihan Demirpençe**

---

## What email address should we use to contact you?

**ussstarfairy@gmail.com**

---

## Why are you, and your team members, the right people to work on this project?

I am a solo developer and the sole maintainer of USAFE, and I built its entire working prototype myself — the censorship/blocking detector, the fingerprinting analysis, and the ECDH/AES-GCM secure-communication module, including the QR-code key exchange and the offline-capable service worker. As with MetaSafe, I ran an adversarial verification pass rather than assuming the prototype worked as intended, and that pass caught two genuinely serious bugs: an ECDH encryption mode that could be used to encrypt a message but never decrypt it (the wire format didn't even include the sender's public key, which is required to derive the shared secret at all), and a DNS-manipulation test with no timeout that could hang forever or silently misreport safety when a resolver was unreachable. I treat catching these kinds of bugs before a user relies on them as the core discipline this project needs, not an afterthought.

I also have the same direct, existing relationships with activists engaged for real-world testing under MetaSafe's grant, which extends naturally to testing this toolkit as well.

---

## What is your proposed start date for this project?

N/A — this field only applies to the Community Convenings category; this application is Technical Development.

---

## Sonraki adım

Bütçeyi $24,000 olarak yazdım (MetaSafe'in $28,000'inden biraz daha düşük, çünkü kapsam biraz daha dar — sadece 1 modülün denetimi + 2 modülün güçlendirilmesi). Süreyi 2-3 ay yaptım çünkü MetaSafe'e göre daha yeni bir proje (bugün üretildi), 1-2 ay biraz iddialı olurdu. Bunları değiştirmek istersen söyle, sonra birlikte gerçek forma geçiririz — MetaSafe'te olduğu gibi, son "Submit"e senin onayın olmadan basmam.
