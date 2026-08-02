# Production Readiness

Sophisticated investors diligence the gaps. This document exists so that
when they look, they find that we looked first. It separates what is
**proven** from what is **prototype** from what is **designed**, and
states plainly what each production milestone requires.

## Maturity map

| Layer | State | What "production" needs |
|---|---|---|
| Corpus format & schema | **Proven** — open, versioned, 200+ real memories | Formal v1 freeze + migration policy |
| Self-hosted node | **Proven** — 19-day uptime, autonomous rituals | Watchdog, signed OTA updates, remote health telemetry |
| iOS app (Testator Zero) | **Working build** — runs on device | App Store review, backend key proxy, paid-account distribution |
| Local-first privacy (journal, ear) | **Proven** — on-device model, no cloud | Security audit, documented data-flow guarantees |
| Urbit constellation & commons | **Proven** — live, multi-machine, public | Managed hosting story, key-custody hardening |
| Base contracts (pool, deeds) | **Deployed & verified** on mainnet | Third-party audit before any real funds |
| $WAKE / Proof of Remembrance | **Designed & documented** | Legal opinion, revnet simulation, audit — *pre-launch* |
| Testament Key (hardware) | **Firmware prototype** (ESP32) | Secure element, manufacturing, cert |
| Model will clause | **Drafted** by attorney-founder | Per-jurisdiction review; it is model language, not advice |

## The three things to fix before a public app build

These are known, scoped, and small relative to what's already built.

1. **Backend inference proxy.** Today the app can carry a Venice key; a
   bundled key in a shipped binary is extractable. Production routes all
   default-tier inference through a thin server that holds the key and
   meters by subscription entitlement. *~1 week; standard pattern.*
2. **Apple Developer Program + distribution.** Free-tier signing expires
   weekly and can't reach TestFlight. Enroll ($99/yr), wire CI signing,
   ship to TestFlight. *Days.*
3. **App Review posture for AI + memorial content.** Clear AI-content
   disclosure, data-handling labels, and a human-in-the-loop statement.
   Our privacy architecture is an asset here, not a liability. *Days.*

## Security & privacy commitments (already architectural)

- **Local-first for sensitive data.** Journals and ambient audio are
  processed by a model on the family's own GPU and never leave the LAN.
- **The ear cannot transcribe.** No speech-recognition code exists in
  the ambient pipeline; it measures acoustics and discards audio from a
  RAM buffer. Built to satisfy all-party-consent law by construction,
  not by policy.
- **Images are described, then deleted.** The camera keeps impressions,
  never frames.
- **The corpus is the user's property**, exportable as one open file.
  No lock-in is the promise *and* the retention mechanism.
- **Secrets never in the repo.** Keys, wallets, and personal corpora are
  gitignored; the public repo ships schema, software, and model clause.

Open items for a formal audit: node OTA signing, Urbit key custody at
scale, contract audit before real funds, app data-handling review.

## Reliability (measured on the live system)

- Node uptime: **9+ days continuous** at last reading; systemd restarts
  on failure.
- Autonomous rituals (twilight reflection, ambient sensing, camera) run
  unattended on timers; inference has **automatic local↔cloud fallback**
  so a provider outage degrades instead of failing.
- Corpus is backed up on every write (rotating, on-device) and pulled
  nightly to a second machine.

## What we are NOT claiming

- No revenue yet. The metrics are traction of a working system.
- $WAKE is a design; no token exists or is offered.
- The will clause is model language requiring licensed adaptation.
- The hardware Key is a firmware prototype, not a manufactured product.

Stating these is the point. A memory business asks families to trust it
with the most intimate data they will ever leave behind; that trust is
earned by being precise about what is real.
