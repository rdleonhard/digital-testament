# digital-testament

**A will clause for digital immortality, and the tooling to execute it.**

A testator endows a *Digital Persona* — an interactive AI memorial built from
their own data — and funds it in perpetuity by staking [Venice](https://venice.ai)'s
VVV token. Staking yields **Diem**, a daily-refreshing allocation of AI
inference capacity, so the persona runs forever off the endowment's *yield*
while the principal sits untouched in a trust wallet. The digital tomb pays
its own light bill.

```
USD  ──buy──►  VVV  ──stake──►  Diem/day  ──runs──►  Digital Persona
(endowment)   (principal,      (refreshes           (corpus.json +
               never spent)     midnight UTC)         Venice API)
```

## The legal layer

- [`clause/digital-immortality-clause.md`](clause/digital-immortality-clause.md) —
  model testamentary article: definitions (Digital Corpus, Protocol Token,
  Diem, Persona Endowment), RUFADAA fiduciary-access consent, prudent-investor
  waiver for holding VVV, a Digital Executor office, mandatory AI disclosure,
  an evidentiary firewall (persona output can never construe the will), a
  kill switch, perpetuities savings, and an express no-personhood section.
- [`clause/drafting-notes.md`](clause/drafting-notes.md) — attorney notes:
  why a testamentary trust rather than a bare bequest, purpose-trust and RAP
  traps, key custody, publicity rights, tax flags, companion-document
  checklist.

**Model language for attorney adaptation. Not legal advice.**

## The technical layer

Stdlib-only Python (3.9+), no install needed:

```sh
# 1. Size the endowment: what does $25,000 buy in perpetual daily inference?
python3 -m tomb convert 25000
python3 -m tomb convert 25000 --vvv-price 3.10 --total-staked 12500000 --capacity 20000

# 2. Provision the estate's inference credential
#    (creates a real Venice INFERENCE key if VENICE_ADMIN_KEY is exported;
#     otherwise records a pending-key checklist item in estate_keys.json)
python3 -m tomb provision --owner "Estate of Arthur R. Vale, Digital Persona Trust"

# 3. Build the persona from the Digital Corpus
python3 -m tomb build examples/corpus.example.json -o persona_prompt.txt

# 4. Converse with the deceased (spends the daily Diem)
export VENICE_API_KEY=...
python3 -m tomb chat examples/corpus.example.json

# 5. Keep the funding alive: Venice only allocates Diem to stakers with an
#    API call in the trailing 7 days. Cron this.
python3 -m tomb heartbeat
```

### The Digital Corpus

The persona's identity lives in one versioned JSON file — the **Digital
Corpus** — referenced by name in the will and validated against
[`schema/corpus.schema.json`](schema/corpus.schema.json). It holds identity,
voice (with verbatim writing samples — the highest-leverage fidelity input),
values, first-person memories, knowledge domains with honest depth ratings,
sealed messages with delivery triggers, and runtime directives that mirror the
will's mandatory-conduct sections. See the worked example:
[`examples/corpus.example.json`](examples/corpus.example.json) (Art Vale,
Chesapeake harbor pilot, 1948–2026).

Three behaviors are enforced in the prompt because the will requires them:

1. **Disclosure** — the persona opens every conversation identifying itself
   as an AI memorial (will §5(c));
2. **No fabrication** — biographical claims come from the corpus or the
   persona admits it doesn't carry that memory (§5(b));
3. **Prohibited uses** — no contracts, no testimony, no advice, and no
   opining on the will (§5(e)).

## Why the heartbeat matters

Diem allocation = *(your staked VVV ÷ total **active** stakers' VVV) × network
capacity*, and "active" means an API call within 7 days. An unvisited persona
would fall out of the active set and defund itself. `tomb heartbeat` is the
1-token cron job that keeps the tomb lit — arguably the most gothic line item
in the whole project.

## Roadmap

- [ ] Persona runtime on an open agent framework ([ElizaOS](https://github.com/elizaOS/eliza)
      character files map cleanly onto the corpus schema) for memory,
      multi-channel access, and richer behavior
- [ ] Corpus ingestion helpers (mbox/email export → memories & writing samples)
- [ ] On-chain endowment attestation (Base) linking the trust wallet, the
      corpus hash, and the will's memorandum — kin to
      [open-esquire-verifier](https://github.com/rdleonhard/open-esquire-verifier)
- [ ] Voice layer (TTS conditioned on recorded speech)
- [ ] Multi-testator hosting: one staked pool, many tombs

## Repository layout

```
clause/     model will language + drafting notes
schema/     Digital Corpus JSON Schema
examples/   worked example corpus
tomb/       Python package: convert | provision | build | chat | heartbeat
```

## License

MIT. The model clause may be freely adapted for client work.
