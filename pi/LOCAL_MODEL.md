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

Paste an entry; the Jetson reads it and answers *why did he write this* and
*why did he hand THIS one over*, plus what it evidences and what is
conspicuously absent. `POST /journal {text, note}`, `GET /journals`.

This path is **local-only and does not fall back to Venice.** A journal is
the most private text in this system, and a silent failover would put it on
someone else's server. If the Jetson is down, submission fails and says so.

The raw entry is archived verbatim to `/var/lib/testate/journals.jsonl` —
that is the evidence, and the Compilation will want it whole. Only a
≤400-char distillation enters the corpus as a memory tagged `journal`,
because `PROMPT_MEM_BUDGET` is 6500 chars for *all* memories and one long
entry would otherwise swallow the persona prompt whole.

The analysis prompt is deliberately third-person and unkind: it reads the
entry as evidence rather than self-report, on the principle already written
into ECONOMY.md — a man is not always the best witness to himself.

**Vision is available locally but not yet wired.** `granite` has no vision
(`capabilities: [completion, tools]`); `qwen3.5:4b` does, and was verified
describing a test frame locally in ~23s. The observe path still calls
Venice's `qwen3-vl-235b-a22b`. To move it local, point the vision call at
`infer(..., prefer="local")` with `model="qwen3.5:4b"` — but note that only
one model stays resident at a time, so each observation will swap models
(a few seconds off NVMe). Left as a deliberate choice rather than done
silently, since it trades a 235B vision model for a 4B one.
