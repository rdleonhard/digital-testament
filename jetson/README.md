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
