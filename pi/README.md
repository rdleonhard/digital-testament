# TESTATE node — Raspberry Pi edition

The grown-up vault. Same avatar and API as the [ESP32 node](../device/), but
with real storage: the corpus lives in `/var/lib/testate/` with rotating
backups on every new memory, the site is served by a threaded CPython server,
and systemd keeps the node and its staking heartbeat alive across reboots.

## Setup

1. **Flash** Raspberry Pi OS Lite (64-bit) with headless config. GOTCHA:
   the Trixie-based images (Debian 13, 2025+) **ignore `custom.toml`** —
   only the `ssh` marker file and `userconf.txt` still work from the boot
   partition. Plan on password SSH for first contact (Ethernet if WiFi
   isn't configured), then set hostname/WiFi/keys over SSH:
   `hostnamectl set-hostname testate`, `raspi-config nonint do_wifi_country
   US`, `nmcli dev wifi connect <ssid> password <pass>`.
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

## Urbit ships on the node

The Pi comfortably runs the pool's planet and the avatar's moon beside
the node (two piers ≈ 1.4GB resident). Hard-won boot notes:

- vere needs `-t` in EVERY headless context (nohup, systemd) or it dies
  with "unable to initialize terminal"; `-x` wedges at 0% CPU — never
  use it. vere ignores INT/TERM under `-t`; SIGKILL is safe (event log).
- First boot needs the default 2GB loom — `--loom 30` fails with `%meme`
  "unable to parse pill". Delete the partial pier before retrying.
- Re-keying an existing moon is `|moon-cycle-keys ~name` (`|moon` refuses).
- Headless dojo = `expect` over `ssh -tt` with `stty cols 400` so keyfile
  jams print unwrapped. Don't anchor prompt regexes (`dojo> $` never
  matches through the escape-code spam).
- Moon names are shaped exactly like `+code`s (four 6-letter segments) —
  when scraping a code, exclude the ship's own name.
- Kernel updates: if the sponsor star is dark, `|ota ~<galaxy>` walks the
  chain up. Eyre goes down during kelvin rebuilds — whispers auto-retry.

## Why a Pi over the ESP32

Storage (a corpus of a life should not live in 16MB of flash with no
redundancy), TLS with real certificate verification, room for the roadmap
(ElizaOS runtime, local embedding search over memories, voice), and no
USB-write-corruption gremlins at deploy time.
