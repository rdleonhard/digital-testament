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

## Observation dedup

The roving sensor wakes every ~5 minutes (`roving.min_interval_s`) and a
house at night does not change. Measured on the live corpus: **39 of 49
consecutive observations were near-identical, median pairwise similarity
0.98**. Worse, `_memories_block` walks grown memories newest-first, so that
run of duplicates sat at the *front* of the 6500-char budget and suppressed
the interviews and journal memories behind it.

Two layers, both in `_describe()` — the one chokepoint every eye goes
through (local, roving-polled, roving-pushed):

**Frame layer** (before the vision call, so it is the only layer that saves
money). A 12×12 grayscale signature, compared by *largest per-cell change*.
Skips the call when nothing moved. Config: `observe.frame_dedup`,
`observe.frame_delta` (default 10).

**Text layer** (after the call). If the description is ≥0.75 Jaccard-similar
to any of the last 8 observations from the same eye, it is not filed again.
Config: `observe.text_dedup`, `observe.text_similarity`.

Either way the matched memory gets `seen` incremented and `last_seen`
stamped — a scene that holds is recorded as recurring rather than copied.

### Two measurements that changed the design

**Mean absolute difference was the wrong statistic.** A person stepping into
a dark room moves the frame mean by 0.58 — indistinguishable from noise — so
a MAD threshold generous enough to catch duplicates would have *skipped
people walking in*, the exact event the roving eye exists for. The max
per-cell change separates cleanly: identical 0, dim figure 19, phone screen
24, lamp 205.

**Average-hash would also have failed.** aHash thresholds each pixel against
the frame mean, so on a near-black frame it quantises sensor noise and two
identical dark rooms hash far apart.

Signatures are **mean-centred** so the camera's auto-exposure drift cancels:
a uniform +25 brightness shift measures 0.0, while local structure survives.

### Collapsing the backlog

Capture-time dedup only helps future observations. For what is already
stored, **stop the service first**:

    sudo python3 /opt/testate/node.py --dedupe-observations --dry-run   # safe any time
    sudo systemctl stop testate
    sudo python3 /opt/testate/node.py --dedupe-observations
    sudo systemctl start testate

It keeps the earliest of each cluster with a `seen` count, and writes a
rotating backup to `/var/lib/testate/backups/` before touching anything.

**Why the stop matters, and it is not optional.** The running node holds the
entire corpus in memory and rewrites `corpus.json` wholesale on its next
save. Collapse the file underneath it and the change survives only until the
next observation, answer or journal entry — then the stale in-memory copy
lands on top and the duplicates are all back. This happened: the first run
reported 104 → 63, and minutes later the file was 109 again with the
`seen` counters gone. The command now refuses to run against a live service
(exit 1) unless you pass `--force`; `--dry-run` is always allowed.

Any maintenance that edits `corpus.json` out of band has the same hazard —
stop the service, edit, start it.

**Vision is available locally but not yet wired.** `granite` has no vision
(`capabilities: [completion, tools]`); `qwen3.5:4b` does, and was verified
describing a test frame locally in ~23s. The observe path still calls
Venice's `qwen3-vl-235b-a22b`. To move it local, point the vision call at
`infer(..., prefer="local")` with `model="qwen3.5:4b"` — but note that only
one model stays resident at a time, so each observation will swap models
(a few seconds off NVMe). Left as a deliberate choice rather than done
silently, since it trades a 235B vision model for a 4B one.
