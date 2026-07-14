# TESTATE node — ESP32-S3 avatar device

Self-hosted node for one pseudonymous avatar. See [../NETWORK.md](../NETWORK.md)
for why this runs on a chip instead of a cloud.

## Hardware

- ESP32-S3 (tested: 16MB flash / 8MB embedded PSRAM devkit)
- Passive buzzer between **3V3** and **GPIO 4** (sound = PWM on GPIO4;
  idle = pin held HIGH so no DC flows through the coil)

## Firmware

MicroPython ≥ 1.28 (`ESP32_GENERIC_S3`). Files:

| file | role |
|---|---|
| `main.py` | WiFi + mDNS (`http://testate.local`), HTTP server, endpoints |
| `avatar.py` | corpus storage on flash, persona prompt builder, mood-tag parser |
| `venice.py` | Venice chat-completions client (spends the node's daily Diem) |
| `tunes.py` | buzzer driver, mood jingles, interrogative tail, songs |
| `index.html` | the chat site the node serves |
| `config.json` | WiFi + Venice key (copy `config.example.json`; never commit) |
| `corpus.json` | the avatar itself (seed from `corpus.seed.json`) |

## Deploy

```sh
# flash MicroPython (S3 native USB; if the port won't respond, hold BOOT,
# tap RESET, release BOOT to force download mode)
python3 -m esptool --port PORT erase_flash
python3 -m esptool --port PORT write_flash -z 0 ESP32_GENERIC_S3-*.bin

# install the node
cd device
cp config.example.json config.json   # fill in wifi + venice key
python3 -m mpremote connect PORT cp main.py avatar.py venice.py tunes.py index.html config.json :
python3 -m mpremote connect PORT cp corpus.seed.json :corpus.json
python3 -m mpremote connect PORT reset
```

Then open **http://testate.local** on the same network.

## Endpoints

| route | does |
|---|---|
| `GET /` | chat UI |
| `GET /status` | handle, mood, memory count, uptime |
| `GET /corpus` | download the corpus (backup — do this often) |
| `POST /chat {msg}` | talk to the avatar; plays mood jingle, sometimes sings |
| `POST /interview` | avatar asks ONE question about its own life (jingle + rising tail) |
| `POST /answer {question, answer}` | answer becomes a new corpus memory |
| `POST /song` | avatar plays a tune for its current mood |

The avatar ends every reply with `[mood: …]` (parsed off before display) and
may add `[sing]` when the mood strikes. Every inference call doubles as the
staking heartbeat that keeps the node's Diem allocation alive.
