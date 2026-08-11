# The ear — ambient acoustic memory

The avatar has an eye ([pi/eye.py](../pi/eye.py)) that looks and keeps only
its impression. This is the ear. It listens to the texture of a life —
voices coming and going, dishes, music, the quiet of an empty house — and
keeps one sentence about how it sounded.

Runs on the Jetson, the private-processing node: like the journal reader,
nothing it hears ever reaches a remote API.

## The constraint that shaped it

Pennsylvania is an **all-party-consent** state (18 Pa.C.S. § 5703), and a
house contains people who never agreed to anything — family, guests,
whoever is on the other end of a phone call.

So the ear, in its default and only enabled mode, **never resolves words.**
There is no speech recognition in the pipeline. No transcript is produced,
because nothing in the chain is capable of producing one. It measures
acoustics and turns those *numbers* into an impression:

```
audio → numbers → impression → corpus
        ↑ words never exist anywhere in this pipeline
```

Audio lives in a RAM buffer for the length of one capture and is discarded
— never written to disk, not even tmpfs. What persists is a line like
*"I heard a back-and-forth in the kitchen, even-tempered, dishes going."*

It cannot capture the contents of a communication, which is the thing the
statute protects. `transcribe` exists in the config as an opt-in path and
ships **off**; turning it on is a decision about consent, not a setting.

## What it measures

Per 25 ms frame: level, zero-crossing rate, spectral centroid, spectral
flatness, and voice-band (300–3400 Hz) energy ratio. Aggregated into:
speech presence, number and length of voice segments, turn-taking rate,
transient count (doors, dishes, footsteps), musical fraction, brightness,
loudness variation. A rule-based reading turns those into a blunt summary
("back-and-forth conversation; busy handling; animated dynamics"), and the
local model writes it up as one first-person diary line.

No speaker identification, ever.

## Guards

| guard | default |
|---|---|
| acoustic-only (no ASR) | on, and the only supported mode |
| audio to disk | never |
| cooldown between impressions | 20 min |
| daily cap | 20 |
| blackout windows | configurable hours, e.g. `[[9,17]]` |
| privileged mute | `ear off [hours]` |
| audible chirp when the ear opens | on — consent you can hear |

**Keep it out of any room where clients are met.** Rule 1.6 doesn't care
that the recording was discarded.

## Office mode — the Room Diary

The ear can serve a specific room as a **witness**, feeding a diary that
is separate from the avatar's corpus. Movement (from the Pi's eye),
conversation, and acoustic classifications all log to the node's diary
(`/var/lib/testate/diary.jsonl`); **raw events and transcripts never
sync to the phone and never reach the commons.** Once a day the digest
(`testate-diary.timer`) distills them into ONE corpus memory:

> *What my office sensed on 2026-08-11: 40% quiet murmured talk, 20%
> lively exchange, 20% steady conversation, 20% quiet stir. 1 arrival,
> ~90 minutes of presence, 1 conversation documented. [2–3 sentence
> summary of what was discussed, from the transcripts].*

**Transcription** (Whisper on the Orin) is the one place words are
resolved, and it is gated hard: it runs **only** when the config carries
both `transcribe: true` **and** a non-empty `consent_notice` stating the
legal basis. This is a deliberate friction — turning it on is an
assertion that all speakers have consented and written notice is posted
(18 Pa.C.S. § 5704(4) for a PA office). Without both, the ear stays
word-deaf and only the acoustic diary (statistics + vibe) accrues.
Transcripts live in the diary; the corpus only ever sees the digest.

`ear status` states plainly whether transcription is on. Needs
`faster-whisper` and its model on first use.

## Control

```sh
ear status         # listening? what did it last keep?
ear off 3          # privileged mode for three hours
ear on
ear last 10        # recent impressions
ear test           # one real capture through the whole chain
```

## Install

```sh
sudo mkdir -p /opt/ear /var/lib/ear && sudo chown $USER /var/lib/ear
sudo cp ear.py /opt/ear/ && sudo cp earctl /usr/local/bin/ear && sudo chmod +x /usr/local/bin/ear
sudo cp ear.service /etc/systemd/system/ && sudo systemctl enable --now ear
```

Needs `numpy`, `arecord` (alsa-utils), a local ollama, and `libnss-mdns`
+ a running `avahi-daemon` if you want `.local` names to resolve.

Impressions are committed to the node's corpus via `POST /ambient`, tagged
`ambient`, and appear in the corpus reader at `http://testate.local`.
