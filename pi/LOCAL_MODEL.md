# Wiring the testator node to the local model

The Jetson (`192.168.1.174`) now serves an OpenAI-compatible endpoint on the
LAN with no API key. See `/mnt/ssd/README-inference.md` on that box for the
model benchmarks and the memory gotchas.

## Access

    ssh testate@192.168.1.100      # key-based, NOPASSWD sudo, no password

Use the IP, not `testate.local` — the mDNS name resolves slowly enough to
fail short-timeout probes. Live code is `/opt/testate/` (deployed copies,
not this repo path); config `/var/lib/testate/config.json`; service
`testate`.

## Enable it

**Already applied** on the Pi as of 2026-07-24. For reference, this is the
`local` block in `/var/lib/testate/config.json`:

```json
{
  "local": {
    "url": "http://192.168.1.174:11434/v1/chat/completions",
    "model": "granite4.1:8b-q3_K_M",
    "timeout": 300,
    "effort": "low"
  }
}
```

Then `sudo systemctl restart testate`.

Until that block exists, `infer()` sends everything to Venice exactly as
before — the change is inert, not a switchover.

## What routes where

`node.py` grew `local()` and `infer(prefer=...)` alongside the untouched
`venice()`:

| call | prefers | why |
|---|---|---|
| `do_chat` | local | constant, conversational, no reason to pay for it |
| `do_interview` | local | short question generation |
| twilight reflect / weave / wonder | **remote** | Diem expires unspent; buy depth with it while it exists |
| vision / observe | remote (unchanged) | see below |
| `--heartbeat` | **remote, always** | its entire job is keeping the Venice stake active |

Either direction falls back to the other provider on failure, so an outage
degrades instead of breaking. The important consequence: **when the daily
Diem runs dry, the avatar keeps answering** instead of going dark.

## Two things to know

**The local model must not be allowed to think.** `qwen3.5` is a reasoning
model that will spend the entire token budget on a reasoning trace and
return an empty `content` field — which reads as the avatar falling silent.
`local()` sends `reasoning_effort: "none"` by default, and raises on empty
content so the router falls through to Venice rather than returning
silence. Note `reasoning_effort` works only on `/v1/`; the `/api/chat`
equivalent is `"think": false`, and passing `think:false` to `/v1/` is
silently ignored.

## Journal entries (📓 on the local site)

Paste an entry. The Jetson does exactly two things with it.
`POST /journal {text}`, `GET /journals`.

**1. Learns how he writes.** The persona has to sound like him, and a
journal is the only place he writes with nobody watching. Revises
`corpus["voice"]`: `syntax` and `diction` from the model, `punctuation` from
a count, `tics` and `catchphrases` by accumulation.

**2. Finds memories.** Lifts out the discrete durable things and commits
them to the corpus in **his own first-person phrasing**, kept verbatim where
a line is striking. His words, not a summary — the corpus is what teaches
the persona to talk, so a paraphrase throws away the thing being collected.

This path is **local-only and does not fall back to Venice.** A journal is
the most private text in this system, and a silent failover would put it on
someone else's server. If the Jetson is down, submission fails and says so.

The raw entry is archived verbatim to `/var/lib/testate/journals.jsonl` and
is never itself a memory: `PROMPT_MEM_BUDGET` is 6500 chars for *all*
memories, so one long entry would swallow the persona prompt. Extracted
memories are capped at 5 per entry and 300 chars each, tagged `journal`
(in `GROWN_TAGS`, so they rotate rather than posing as identity backbone).

### Guardrails, each one earned in testing

- **`register` and `humor` are structurally unwritable from a journal.**
  They were written by hand and are good; a single thin entry rewrote
  "courtroom precision crossed with maker-bench pragmatism" into "practical
  and concise" when it was allowed to. The model is shown them for context
  and cannot change them. The pre-journal voice is snapshotted once to
  `voice_seed`, so the original is always recoverable.
- **A phrase needs two sightings to reach the prompt.** One entry saying a
  thing once is not a catchphrase — it promoted "Got the ESP32 talking..."
  off a single mention, which the avatar would then have parroted forever.
  Unconfirmed phrases wait in `voice_candidates` and show on the page as
  "heard once".
- **Punctuation is counted, never asked.** The model hallucinated ellipses
  and parentheses that were nowhere in the text, through two rounds of
  prompt tightening. Marks are countable, so `measure_punctuation()` counts
  them and accumulates across every entry. The measured profile is withheld
  from the model, and `_drop_punctuation_talk()` strips punctuation claims
  out of `syntax` — otherwise the prompt asserts he uses ellipses two lines
  after the count says he never does.
- **No free-text note field.** An earlier version had one, and the model
  mined the note itself for memories and catchphrases, filing metadata as
  if he had written it. Anything still POSTing `note` is ignored.

### Known limitation

Titles still come back in headline Title Case perhaps half the time.
`_detitle()` fixes the unambiguous cases ("ESP32 LAN Communication Triumph"
→ "ESP32 LAN communication triumph") but deliberately leaves titles where a
lowercase function word drops the ratio ("Shop Closed by Rain"). Detecting
those too would mean lowercasing proper nouns — "Drive to New York on
Saturday" → "drive to new york on saturday" — which is a worse failure than
an ugly title. Two rounds of prompting did not fix it; an 8B at q3 does not
hold fine-grained style rules reliably.

**Vision is available locally but not yet wired.** `granite` has no vision
(`capabilities: [completion, tools]`); `qwen3.5:4b` does, and was verified
describing a test frame locally in ~23s. The observe path still calls
Venice's `qwen3-vl-235b-a22b`. To move it local, point the vision call at
`infer(..., prefer="local")` with `model="qwen3.5:4b"` — but note that only
one model stays resident at a time, so each observation will swap models
(a few seconds off NVMe). Left as a deliberate choice rather than done
silently, since it trades a 235B vision model for a 4B one.
