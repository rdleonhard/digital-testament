# Drafting Notes — Digital Persona Legacy Article

Attorney-to-attorney notes on the model language. Adapt per jurisdiction; this
is a checklist, not advice.

## 1. Structure: why a testamentary trust, not a bare bequest

A direct bequest ("I give $X to run my AI") fails for want of a beneficiary who
can enforce it — software cannot hold property or enforce a promise. The Article
therefore routes everything through a **trust for the benefit of living persons**
(the Qualified Beneficiaries), with persona operation framed as a *purpose of
administration* (§9). This dodges two classic attacks:

- **Honorary / purpose-trust doctrine.** Trusts "for a purpose" with no human
  beneficiary are void in most states outside statutory carve-outs (pets,
  graves — e.g. UPC §2-907, UTC §409, which cap purpose trusts at 21 years in
  many enactments). Framing beneficiaries as the descendants who converse with
  the persona gives you enforceable equitable interests. If you prefer the
  purpose-trust route, cite your state's UTC §409 analogue and accept the
  21-year cap.
- **Rule against perpetuities.** §8(a) uses a lives-in-being + 21 savings
  formula; in abolition states (SD, DE, etc.) you may extend or make it
  perpetual. The §10 reformation clause is the backstop.

## 2. Fiduciary access — RUFADAA

The corpus is assembled from emails, messages, and cloud accounts. Under
RUFADAA (enacted in ~47 states), a custodian discloses **content** of
electronic communications only with the user's express consent in a will,
trust, POA, or online tool. §3(d) supplies that consent and invokes the SCA
exception, 18 U.S.C. §2702(b)(3). Two practice points:

- **Online tools trump the will.** Google Inactive Account Manager and Apple
  Legacy Contact settings override testamentary language under RUFADAA's
  priority tiers. Have the client set them *consistently* with the will.
- Name the Digital Executor in those tools where possible.

## 3. The crypto problem — prudent investor exposure

Holding a single volatile token forever is a textbook diversification breach
under UPIA §3. §4(c) waives it expressly (UPIA §1(b) permits override by the
governing instrument). Belt-and-suspenders: the §6(c) exculpation. Consider a
directed-trust statute (e.g. UDTA) if your state has one — make the Digital
Executor a "trust director" over the endowment and insulate the corporate
trustee.

## 4. Key custody

The wallet seed and API keys are bearer assets. §4(d) requires a written
succession protocol. In practice: multisig or social-recovery wallet with the
Digital Executor + successor + institutional co-holder; seed shards in
separate safe deposits; never in the probate inventory (public record).

## 5. Evidentiary firewall

§5(e) matters more than it looks. Without it, expect litigants to depose the
chatbot: "the AI trained on Dad's emails says he *meant* the lake house for
me." The clause makes persona output inadmissible-by-direction for construing
the instrument and voids any purported exercise of legal power. Pair with a
standard no-contest clause if the family situation warrants.

## 6. Publicity / right-of-publicity

Post-mortem right of publicity is statutory and state-specific (e.g. Cal. Civ.
Code §3344.1 — 70 years; Tennessee; NY EPTL 50-f). If the testator is a public
figure, add an express license from the estate's publicity rights to the trust
and address third-party commercialization. Some states are adopting
digital-replica statutes (e.g. Tennessee ELVIS Act) aimed at unauthorized AI
replicas — an *authorized* replica clause is exactly what those regimes
anticipate.

## 7. Venice/DIEM mechanics as drafted-around facts

The clause deliberately defines Protocol, Token, and Diem **functionally**
(recurring capacity from staking) rather than freezing today's parameters,
because:

- Diem allocation = (your staked VVV ÷ total *active* stakers' VVV) × network
  daily capacity; the ratio floats as stakers enter/exit and capacity grows.
- "Active staker" currently means an API call within 7 days — so §5(a)'s
  continuous operation also *preserves the allocation*. A dormant persona
  could fall out of the active set; the tooling in this repo includes a
  heartbeat for exactly that reason.
- If Venice dies, §7(b)/(d) migrates. The corpus (JSON) is the durable asset;
  the protocol is fungible.

## 8. What this clause does NOT do

- Confer personhood, standing, or rights on the persona (§9 disclaims).
- Guarantee fidelity — a model conditioned on a corpus approximates a persona;
  manage family expectations in the counseling session.
- Solve taxes. The endowment is a completed transfer to a non-charitable
  trust; token appreciation inside the trust is taxable to the trust
  (compressed brackets). Get the client's CPA involved.

## 9. Companion documents checklist

- [ ] Memorandum of Digital Assets (corpus location, schema version, keys,
      exclusion list, beneficiary designations)
- [ ] RUFADAA-consistent settings in Google/Apple/Meta online tools
- [ ] Wallet succession protocol (§4(d))
- [ ] Letter of wishes to the Digital Executor (tone, taboo topics,
      access philosophy)
- [ ] Digital Corpus itself (see `schema/corpus.schema.json` and
      `examples/corpus.example.json` in this repository)
