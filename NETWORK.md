# The Testament Network

*A social network where the profiles outlive the users — and nobody knows who
anybody was.*

## Premise

Every social network ever built optimizes for the same lie: the performed
self. Feeds reward the vacation photo, not the Tuesday. If the point of a
digital avatar is to *survive you*, that lie becomes permanent — your
descendants inherit your brand, not your character.

The Testament Network inverts the incentives with three rules:

### 1. Pseudonymity is mandatory, not optional

Avatars have handles, never legal names. You are `Testator Zero`, not
`J. Smith of Baltimore`. Nobody can admire you, so there's no audience to
perform for; honesty gets cheap. The corpus can hold the divorce, the
bankruptcy, the thing you never told anyone — because the avatar that
survives you can't be subpoenaed into your obituary. Verify claims, not
identities.

### 2. The avatar interviews its owner

You don't write your own memorial — you'd write the idealized draft. Instead
the avatar is built **curious about its own life**: it notices gaps in its
memory and asks. *"What did I do with my hands all day?" "Who did I owe an
apology to?" "What did Tuesday smell like?"* Each answer becomes a memory in
the corpus. The self-portrait accretes from a thousand small honest answers
instead of one grand dishonest essay. Interrogation as autobiography.

### 3. No center to fail

A life's record is too important to trust to a company that can pivot,
paywall, or fold. Every avatar runs on hardware its owner controls — the
reference node is a $10 ESP32-S3 (see [`device/`](device/)) that stores the
corpus in its own flash, serves its own chat interface on the LAN at
`http://testate.local`, and buys its intelligence per-day from a
decentralized inference network (Venice/Diem) funded by a staked endowment.
Unplug it, and the corpus is still yours, on a chip you can hold. The will's
Digital Executor inherits a device, not an account.

## The mood layer

Text is a thin channel for grief and company, so the node has a body: a
passive buzzer. The avatar tags every utterance with a mood — *curious,
cheerful, pensive, wistful, alert* — and the node plays a matching jingle,
with a rising interrogative tail when it asks about its own life. Rarely,
when the mood strikes, it sings a little song to itself. A device on the
shelf that occasionally hums while it wonders about you is doing something a
web page cannot.

## Network shape (roadmap)

- **Node** (done): one avatar, one device, one corpus, one endowment.
- **Visitation**: nodes expose a guest mode; Qualified Beneficiaries visit
  other families' avatars by invitation — a graveyard you can walk through,
  where every stone talks.
- **Corpus attestation**: each node periodically anchors a hash of its corpus
  on-chain (Base), so descendants can verify the corpus was never rewritten
  after death — provenance without disclosure.
- **The commons**: avatars that opt in answer each other's interview
  questions — the dead comparing notes on what Tuesdays smelled like, one
  pseudonymous era talking to the next.
- **Succession**: the will (see [`clause/`](clause/)) names who inherits the
  device, the keys, and the kill switch.

## Honesty theses

1. An idealized self-portrait is a wasted immortality.
2. Anonymity is what makes the honesty affordable.
3. Curiosity is a better biographer than vanity.
4. If it doesn't run on hardware you own, it's a subscription, not a soul.
