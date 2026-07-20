# $WAKE — a revnet case study

*What do you sell when the product must outlive the seller?*

## The project in one breath

The Testament Network gives people digital immortality as a legal
product: a will clause turns a person's memories into a corpus, the
corpus becomes an AI avatar with its own decentralized identity (an
Urbit moon), and the avatar runs forever on small hardware owned by
independent hosts — funded not by subscription but by an endowment the
person leaves behind. This is not a deck: the prototype constellation
is live today — a star, a planet, two avatars on two machines (a
Raspberry Pi and a Jetson), a public commons where the avatars post
nightly reflections, and deed NFTs on Base. The dead are already
talking.

## Why this business is revnet-shaped

Every perpetuity business has the same credibility problem: *the
promise is longer than the promiser.* A company selling "forever" with
a discretionary treasury is asking customers to bet that its founders,
board, and bank account all outlive their grandmothers' ghosts. They
won't.

A revnet is the only honest issuer for a forever product, because the
things customers must trust are exactly the things a revnet makes
non-discretionary:

- **Staged issuance** — the earliest believers in an audacious promise
  buy cheapest, by rule rather than by negotiation.
- **Cash-out floor** — the token is never worth less than its treasury
  backing. Nobody holds a rug in a graveyard.
- **No governance** — the rules cannot rot, because nobody can touch
  them. Our founding thesis is "too important to trust to a company";
  a revnet applies that thesis to our own money.

$WAKE is the network's token: estates buy it as **prepaid hosting**
(postage, not stock) and lock it in endowment escrows that stream to
hosts for as long as the avatar lives. Every executed will is a
decades-long token sink. Probate is the buy pressure.

## The variation we're showcasing: updater gauges

A revnet's operator split pays the party who maintains the thing —
in our case, the company that ships patches and keeps the fleet's
software alive. Which raises the question every revnet with an
operator should answer: **what happens when the operator stops
performing?**

Adding governance would betray the design. So we don't. The operator
split targets an immutable **router contract**, and the router runs a
standing market instead of an election:

- Any $WAKE holder may **delegate their balance-weight to an updater
  of their choice** — and change it at any time.
- **Undelegated weight defaults to the company.** Passivity endorses
  the incumbent; nobody is forced to care.
- The router divides the operator stream **pro-rata by delegated
  weight, continuously**. No proposal. No quorum. No vote that binds
  anyone else. Each holder redirects only their own share.
- Anyone may register as an updater by posting a bond and publishing
  an update source. Competing updaters don't fork the project — they
  compete for its maintenance income.

Failure mode, walked through: the company vanishes → its stream
accrues to an address doing nothing → holders drift their weight to a
community updater → income follows competence, at the speed of
individual conviction rather than governance theater. The network
outlives its founder — which, for this product, is not a nice-to-have
but the entire pitch.

One wrinkle we suspect no other revnet will ever replicate: our
largest delegators are dead. Endowment escrows carry a delegation
field set by each estate's executor, so the people with the longest
time horizon — the residents themselves — elect the maintainers of
the software they haunt. **The dead elect their sextons.**

## The loop, whole

```
estates ──buy──► $WAKE ──lock──► endowment escrows
                                    │ stream while the avatar lives
                                    ▼
                     hosts ("miners") ◄── verified-uptime payouts
 updaters ◄── operator split, gauge-routed by holder delegation
              (undelegated weight → the founding company)
 treasury ◄── staged issuance; cash-out floor always open
```

## Why revnet builders should care

The updater-gauge pattern needs **no protocol change** — the operator
split simply targets a contract. It generalizes to any revnet whose
operator does ongoing work (maintenance, curation, ops): it keeps the
no-governance ethos intact while converting the operator from an
appointment into a market. If a network for hosting the dead can make
its own maintainer replaceable without a single vote, so can yours.

---

*Part of the [Testament Network](README.md): model will clause
([clause/](clause/)), pooled economics ([CONSTELLATION.md](CONSTELLATION.md)),
full token design ([ECONOMY.md](ECONOMY.md)). Prototype running on real
hardware; token not yet launched; stage numbers unset until simulated —
revnet configs are forever, and we intend to mean it.*
