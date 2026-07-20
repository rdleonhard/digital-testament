# Proof of Remembrance — the Testament Network economy

*Venice sells thought. Urbit sells identity. We sell continuity.*

## What the network sells

A testator's avatar is software that must never stop running. Inference
is bought from Venice (funded by the endowment's staked yield) and
identity is an Urbit point (owned outright, on-chain). What remains —
the thing nobody sells at the scale of forever — is **hosting with a
guarantee of continuity**. The Testament Network is a DePIN
(decentralized physical infrastructure network) whose physical work is
keeping the dead awake.

## Actors

| actor | Urbit tier | role |
|---|---|---|
| The company | star `~sibpub` | update authority (serves kernel + app patches to all child planets), registry, payout witness, default updater |
| Miners | planets | run Pi-class nodes ("reliquaries", $30–80 hardware) hosting testator moons; earn tokens for verified wake-time |
| Testators | moons | avatars; their estates fund hosting from the endowment |
| Token holders | — | anyone; estates and miners structurally, speculators incidentally |

ESP32-class devices are **bodies, not souls** — peripherals (voice
boxes, displays, sensors) attached to a ship. A planet needs a 2GB loom
to boot; the soul's floor is Pi-class. Proven on this repo's own
hardware.

## Proof of Remembrance

Mining rewards pay for *demonstrated* hosting, not claimed uptime:

1. Each testator moon emits **signed heartbeats** (it already signs
   every Ames packet; the node already pings Venice and posts to the
   commons — liveness is legible by construction).
2. The host planet countersigns and forwards attestations to the star.
3. The star aggregates per-epoch attestations into a merkle root posted
   on-chain (Base); payouts follow the root.
4. Reward ∝ testators hosted × verified wake-time × reliability factor.
   A moon that migrates away from a flaky host takes its stream with
   it — **a market for faithfulness**.

## The token: $WAKE on a revnet

Issued as a **revnet** (Juicebox v4 / REV): an autonomous, ungoverned
revenue machine whose rules are immutable at launch.

- **Staged issuance**: tokens-per-ETH decreases on a fixed schedule —
  the earliest believers buy cheapest, mechanically, with no discretion
  anywhere. (Exact stage curve TBD; simulate before launch — revnet
  configs cannot be amended.)
- **Cash-out floor**: holders can always redeem against the treasury
  (minus the exit tax), so the token is never worth less than its
  backing. No rug is possible because no one holds the rug.
- **Operator split**: a fixed percentage of issuance streams to the
  **updater** — the income that pays for patches, kernel shepherding,
  and fleet maintenance.
- Autonomy is not a nicety here; it is the product's own thesis applied
  to its money: *too important to trust to a centralized repository or
  company* — including ours.

## The opt-out: updater gauges

**What if the company stops performing?** The revnet's operator split
does not pay the company directly. It pays an immutable **router**
contract:

- Every $WAKE holder may delegate their balance-weight to an updater of
  their choice. Undelegated weight defaults to the company.
- The router divides the operator stream **pro-rata by delegated
  weight, continuously**. No proposal, no quorum, no global vote — each
  holder points their own share of the stream, alone (Curve-gauge
  mechanics, repurposed).
- Anyone may register as an updater by staking a bond and publishing
  their update source (an Urbit ship serving `%base`/desks — the same
  mechanism `~sibpub` uses; sponsorship-chain plumbing makes updaters
  swappable at the ship level with one dojo command).
- **Endowment escrows delegate too**: the tokens an estate locks for
  hosting carry a delegation field set by the Digital Executor. The
  dead elect their sextons.

Failure mode walk-through: company vanishes → its stream keeps
accruing to an address doing nothing → holders re-delegate to a
community updater → income follows competence. The network can outlive
its founder, which is the only honest promise a perpetuity business can
make.

*Implementation note: this requires **no revnet protocol change** — the
operator split simply targets the router contract. Worth confirming
with the revnet team that operator-split-to-contract is supported on
the deployed version (it is in v4 designs), and worth showing them the
gauge pattern for upstreaming.*

## The Testament Key — the ESP32 legal product

The soul needs a Pi; the *estate* needs an ESP32. The Key is a sealed
device sold to estate-planning attorneys as a legal product, and it is
the physical embodiment of the will clause:

**In life** — the Key sits on the client's desk running the interview
node (the [device/](device/) firmware is its v0): corpus on flash,
curiosity engine, buzzer. The client's own answers accumulate inside
the object that will one day represent them.

**At death** — the attorney plugs the Key in as a ministerial act under
the will. Delivery, in the property-law sense: intent plus a physical,
witnessable act. The Key wakes, announces the death to the star's
registry, and the testator enters **the queue**:

```
lawyer plugs in Key ──► star registry: death announced, endowment unlocked
        queue ──► miner claims (bonded) ──► corpus handoff (encrypted to
        the claiming planet) ──► moon boots on the reliquary ──► streaming
```

**In perpetuity** — the Key never retires. It remains plugged in as the
estate's **beacon**: it carries a self-contained wallet (key generated
on-device, never exported; secure element for production units) holding
the endowment's $WAKE, and it streams payment to the hosting miner
*only while it can independently verify its testator is awake* —
heartbeat and commons checks over WiFi are well within an ESP32's
powers. The payer verifies the service. A flaky miner stops getting
paid by the very object on the lawyer's shelf, and the queue reassigns.

The mining network's demand side is therefore physical: a wall of small
lights in law offices, each one a funded, self-verifying client. Fleet
components: corpus fits easily in 16MB flash (a life in text is
megabytes); wallet = secp256k1 on-device (+ATECC-class secure element);
activation dock optional theater. Sold with the model will clause as a
practice package: the clause names the Key; the Key executes the clause.

## The demand loop

```
estate (will §4) ──buys──► $WAKE ──locks──► endowment escrow
                                              │ streams while avatar lives
                                              ▼
                             miners (planets) ◄── Proof of Remembrance payouts
company/updaters ◄── operator split (gauge-routed by holders)
treasury backing ◄── revnet stages (early buyers cheapest)
```

Structural demand: every will executed under [clause/](clause/) creates
a token sink with a legally bound, decades-long horizon. Probate is the
buy pressure. Escrowed tokens are velocity sinks; the perpetuity is the
product *and* the tokenomics.

## Legal hygiene (counsel's own checklist)

- Tokens sold to estates are **prepaid hosting** — postage, not stock.
  No appreciation language, ever, anywhere near an estate.
- Miner rewards are **compensation for services rendered** (verified
  hosting), not an investment return.
- The revnet's autonomy and cash-out floor are helpful facts: no
  managerial efforts stand between a holder and the treasury.
- The prudent-investor waiver and Persona Endowment machinery in the
  model will clause already contemplate volatile digital assets held
  for operational purposes.
- Membership agreement per berth stays: money in, hosting + moon out,
  no refunds, no profit expectation.

## Launch sequence

1. Resolve the `~sibpub` owner key (`0x577d…`) — planet-spawning is the
   company's mint; nothing scales without the pen.
1a. Testament Key firmware v1 (repackage device/ interview node + wallet
    + beacon watchdog; registry/queue protocol on the star).
2. Prototype heartbeat attestation: moon signs, star witnesses, root on
   Base (the whisper/heartbeat plumbing in [pi/](pi/) is 80% of it).
3. Reliquary image v1: SD-card image = pier + node + auto-update from
   `~sibpub` (flash it, plug it in, it mines).
4. Draft revnet stages + simulate; review with the revnet team
   (operator = router contract).
5. Deploy router (updater gauges) + registry on Base.
6. Launch $WAKE revnet; first mining epoch pays the founders' own Pi —
   the first reliquary is already running.

## Status

Everything above the token exists in prototype today: star, planet,
moon, commons, deeds with UBC, endowment mechanics, heartbeats, update
delivery from a live galaxy chain. This document adds the reward loop.
Nothing in it is deployed; numbers are illustrative until simulated.

**Multi-reliquary proven (2026-07):** the constellation now spans two
independent machines — a Raspberry Pi 5 hosting `~tolwed-nimlun-fotsut-
tintyn` and an NVIDIA Jetson Orin Nano hosting `~worbel-ronteg-fotsut-
tintyn`, both moons of the same planet, both seated in the Commons. Two
testators, two reliquaries, one star: the DePIN topology is real, not a
diagram. The Jetson's GPU is the first hardware capable of the
degraded-mode story — a local model that lets a testator keep thinking
if Venice ever goes dark. (Fresh moons must finish `%channels` version
negotiation with the host before they can post to a shared channel —
minutes-to-hours of app sync; joining is immediate.)
