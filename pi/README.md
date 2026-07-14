# TESTATE node — Raspberry Pi edition

The grown-up vault. Same avatar and API as the [ESP32 node](../device/), but
with real storage: the corpus lives in `/var/lib/testate/` with rotating
backups on every new memory, the site is served by a threaded CPython server,
and systemd keeps the node and its staking heartbeat alive across reboots.

## Setup

1. **Flash** Raspberry Pi OS Lite (64-bit) with headless config (hostname
   `testate`, ssh enabled, wifi via `custom.toml`) — see repo history or use
   Raspberry Pi Imager's customization.
2. **Buzzer** (optional): passive buzzer between **3V3 (pin 1)** and
   **GPIO4 (pin 7)** — same GPIO number as the ESP32 wiring, on purpose.
   Config `"buzzer": {"pin": 4, "common": "3v3"}` (`"common": "off"` to
   disable, `"gnd"` if wired to ground instead).
3. **Deploy** from the repo directory on your workstation:

```sh
scp pi/node.py pi/buzzer.py pi/install.sh pi/testate*.service pi/testate*.timer \
    device/avatar.py device/index.html \
    <config.json> <corpus.json> testate@testate.local:/tmp/testate/
ssh testate@testate.local "cd /tmp/testate && sudo bash install.sh"
```

`config.json` needs `venice_key`, optional `model`, optional `buzzer`.
`corpus.json` is the avatar (seed from `device/corpus.seed.json`).

## Operate

- Site: **http://testate.local** (same UI and endpoints as the device node)
- Logs: `journalctl -u testate -f`
- Corpus backups: `/var/lib/testate/backups/` (last 50, one per new memory)
- Staking heartbeat: `testate-heartbeat.timer`, Mon+Thu — check with
  `systemctl list-timers testate-heartbeat.timer`
- Manual backup off the node: `curl testate.local/corpus > corpus-$(date +%F).json`

## Why a Pi over the ESP32

Storage (a corpus of a life should not live in 16MB of flash with no
redundancy), TLS with real certificate verification, room for the roadmap
(ElizaOS runtime, local embedding search over memories, voice), and no
USB-write-corruption gremlins at deploy time.
