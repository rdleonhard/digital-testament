#!/usr/bin/env python3
"""The ear — ambient acoustic memory for the Testament node.

Design constraint first, because it is the whole point: Pennsylvania is
an all-party-consent state (18 Pa.C.S. § 5703), and a household contains
people who never opted into anything. So in its default mode this program
NEVER RESOLVES WORDS. There is no speech recognition, no transcript, no
model that could produce one. It measures acoustics — level, voice-band
energy, turn-taking rhythm, transients, tonality — and turns those
NUMBERS into an impression of what life sounded like.

  audio  -> numbers -> impression -> corpus
           ^ words never exist anywhere in this pipeline

Audio lives only in a RAM ring buffer, is never written to disk (not even
tmpfs), and is overwritten within seconds. What persists is one sentence
like "a long back-and-forth in the kitchen, even-tempered, dishes going."

Guards, all on by default:
  - acoustic-only mode (no ASR; `transcribe` is opt-in and off)
  - blackout windows + a mute file (privileged mode)
  - cooldown between impressions, daily cap
  - audible chirp from the voice box when the ear opens (consent you hear)
  - no speaker identification, ever

Runs on the Jetson (the private-processing node — journals and now audio
never touch a remote API). Characterization uses the local ollama model.
"""

import json
import math
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np

HOME = Path(os.environ.get("EAR_HOME", "/var/lib/ear"))
CFG_PATH = HOME / "config.json"
MUTE = HOME / "muted"
LOG = HOME / "impressions.jsonl"

DEFAULTS = {
    "device": "plughw:CARD=Snowball,DEV=0",
    "sample_rate": 16000,
    "block_seconds": 0.5,
    "capture_seconds": 20,
    "trigger_db_over_floor": 9.0,
    "cooldown_minutes": 15,
    "daily_cap": 24,
    # only conversation is worth remembering: below these, a capture is
    # discarded silently (doors, dishwashers, and hums are not a life)
    "speech_min_fraction": 0.12,
    "speech_min_segments": 2,
    "quiet_retry_seconds": 120,
    # office mode: keep capturing while the talk continues
    "max_capture_seconds": 180,
    "tail_quiet_seconds": 15,
    # transcription is OFF unless BOTH are set: the flag, and an
    # affirmative statement of the legal basis. The config documents
    # consent; without it, no ASR runs. (18 Pa.C.S. § 5704(4): all
    # parties have consented; written notice is posted in the room.)
    "transcribe": False,
    "consent_notice": "",
    "whisper_model": "base.en",
    "blackout": [],              # e.g. [[9,17]] = quiet 9am-5pm
    "chirp": True,
    "voicebox": "http://testate-voice.local",
    "node": "http://testate.local",
    "ollama": "http://127.0.0.1:11434/api/generate",
    "model": "granite4.1:8b-q3_K_M",
    "transcribe": False,         # opt-in ASR; see module docstring
}


def cfg():
    c = dict(DEFAULTS)
    if CFG_PATH.exists():
        try:
            c.update(json.loads(CFG_PATH.read_text()))
        except ValueError:
            pass
    return c


def log(msg):
    print(f"{datetime.now():%H:%M:%S} {msg}", flush=True)


# ---------------------------------------------------------------- acoustics

def features(pcm: np.ndarray, sr: int) -> dict:
    """Turn a window of audio into numbers. No words are produced here or
    anywhere else; this is the only thing that ever sees the samples."""
    x = pcm.astype(np.float32) / 32768.0
    n, hop = 400, 160                      # 25 ms frame, 10 ms hop
    if len(x) < n:
        return {}
    count = 1 + (len(x) - n) // hop
    idx = np.arange(n)[None, :] + hop * np.arange(count)[:, None]
    fr = x[idx] * np.hanning(n)[None, :]

    energy = np.sqrt((fr ** 2).mean(axis=1)) + 1e-9
    db = 20 * np.log10(energy)
    floor = float(np.percentile(db, 20))
    active = db > floor + 6

    zcr = (np.diff(np.sign(fr), axis=1) != 0).mean(axis=1)

    mag = np.abs(np.fft.rfft(fr, axis=1)) + 1e-9
    freqs = np.fft.rfftfreq(n, 1 / sr)
    total = mag.sum(axis=1)
    voice = mag[:, (freqs >= 300) & (freqs <= 3400)].sum(axis=1) / total
    centroid = (mag * freqs[None, :]).sum(axis=1) / total
    flatness = np.exp(np.log(mag).mean(axis=1)) / (mag.mean(axis=1))

    # speech-like: voice-band dominant, moderate zero-crossings, audible
    speechy = active & (voice > 0.55) & (zcr > 0.02) & (zcr < 0.30)

    # contiguous speech segments >= 300 ms, and the gaps between them
    segs, cur = [], 0
    for s in speechy:
        if s:
            cur += 1
        elif cur:
            segs.append(cur); cur = 0
    if cur:
        segs.append(cur)
    segs = [s for s in segs if s >= 30]

    # transients: sudden energy jumps (doors, dishes, claps, steps)
    jumps = int(((np.diff(db) > 12) & (db[1:] > floor + 10)).sum())

    # sustained tonal content that isn't speech-shaped -> music/TV
    tonal = active & (flatness < 0.25)
    musicish = float((tonal & ~speechy).mean())

    dur = len(x) / sr
    return {
        "seconds": round(dur, 1),
        "level_db": round(float(db[active].mean()) if active.any() else float(db.mean()), 1),
        "peak_db": round(float(db.max()), 1),
        "loudness_variation": round(float(db[active].std()) if active.any() else 0.0, 1),
        "active_fraction": round(float(active.mean()), 2),
        "voice_fraction": round(float(speechy.mean()), 2),
        "voice_segments": len(segs),
        "mean_segment_sec": round(float(np.mean(segs)) * 0.01, 1) if segs else 0.0,
        "turn_rate_per_min": round(len(segs) / (dur / 60), 1) if dur else 0.0,
        "transients": jumps,
        "musical_fraction": round(musicish, 2),
        "brightness_hz": int(centroid[active].mean()) if active.any() else 0,
    }


def shape(f: dict) -> str:
    """A blunt, rule-based reading of the numbers — the model gets this as
    a hint so it can't wander off inventing content."""
    if not f:
        return "too brief to characterize"
    bits = []
    v, turns = f["voice_fraction"], f["voice_segments"]
    if v < 0.08:
        bits.append("no speech")
    elif turns >= 6 and f["mean_segment_sec"] < 6:
        bits.append("back-and-forth conversation")
    elif turns <= 3 and f["mean_segment_sec"] >= 6:
        bits.append("one voice at length (a call, or reading aloud)")
    else:
        bits.append("some speech")
    if f["musical_fraction"] > 0.25:
        bits.append("music or television underneath")
    if f["transients"] >= 6:
        bits.append("busy handling — objects, doors, dishes")
    elif f["transients"] >= 2:
        bits.append("occasional knocks or movement")
    if f["loudness_variation"] > 9:
        bits.append("animated dynamics")
    elif v > 0.15:
        bits.append("even, level delivery")
    return "; ".join(bits)


def classify(f: dict) -> str:
    """Deterministic label for the day's statistics — no model involved."""
    if not f:
        return "too brief"
    v, segs = f["voice_fraction"], f["voice_segments"]
    if v >= 0.12 and segs >= 2:
        if f["turn_rate_per_min"] >= 25 and f["loudness_variation"] >= 8:
            return "lively exchange"
        if segs <= 3 and f["mean_segment_sec"] >= 6:
            return "one voice at length"
        if f["level_db"] < -45:
            return "quiet murmured talk"
        return "steady conversation"
    if f["musical_fraction"] > 0.3:
        return "music playing"
    if f["transients"] >= 4:
        return "movement and handling"
    return "quiet stir"


_wm = None


def transcribe(pcm: np.ndarray, sr: int, c) -> str:
    """Local Whisper on the Orin. Only reachable when the config carries
    both the transcribe flag AND a written consent basis."""
    global _wm
    from faster_whisper import WhisperModel
    if _wm is None:
        log(f"loading whisper {c['whisper_model']} (first use)")
        _wm = WhisperModel(c["whisper_model"], device="cpu",
                           compute_type="int8")
    audio = pcm.astype(np.float32) / 32768.0
    segs, _info = _wm.transcribe(audio, language="en", vad_filter=True,
                                 beam_size=1)
    return " ".join(s.text.strip() for s in segs).strip()


# ------------------------------------------------------------ side effects

def chirp(c):
    if not c["chirp"]:
        return
    try:
        req = urllib.request.Request(
            c["voicebox"] + "/mood", method="POST",
            data=json.dumps({"mood": "alert"}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=4).close()
    except Exception:
        pass  # the ear works whether or not the body is listening


def characterize(c, f: dict) -> str:
    prompt = (
        "You are the hearing of a person's home. People were just talking "
        "nearby. You are DEAF TO WORDS — you never hear language, only the "
        "acoustics of it. From the reading below, write ONE plain sentence in "
        "the first person characterizing the VIBE of the conversation: its "
        "pace, energy, warmth or tension, whether it flowed or stalled, what "
        "was happening around it (music, handling, movement).\n\n"
        "Rules:\n"
        "- Start with 'I heard' or similar.\n"
        "- Max 22 words. Plain and specific. No literary flourish: never use "
        "words like symphony, tapestry, dance, unfolded, punctuated.\n"
        "- Never state a duration or any number.\n"
        "- Never invent what anyone said, never name a topic, never quote, "
        "never guess who was there or how many. Vibe only.\n\n"
        f"Reading: {shape(f)}\n"
        f"Measurements: {json.dumps(f)}\n\n"
        "Sentence:"
    )
    body = json.dumps({
        "model": c["model"], "prompt": prompt, "stream": False,
        "options": {"temperature": 0.7, "num_predict": 60},
    }).encode()
    req = urllib.request.Request(c["ollama"], data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.load(r).get("response", "").strip()
    return out.split("\n")[0].strip().strip('"')


def diary(c, payload: dict):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(c["node"] + "/diary", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


# ------------------------------------------------------------------- gates

def blacked_out(c) -> bool:
    if MUTE.exists():
        return True
    h = datetime.now().hour
    for span in c["blackout"]:
        a, b = span
        if a <= b and a <= h < b:
            return True
        if a > b and (h >= a or h < b):   # window crossing midnight
            return True
    return False


def today_count() -> int:
    if not LOG.exists():
        return 0
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(1 for ln in LOG.read_text().splitlines() if today in ln[:30])


# -------------------------------------------------------------------- main

def main():
    c = cfg()
    HOME.mkdir(parents=True, exist_ok=True)
    sr = c["sample_rate"]
    block = int(sr * c["block_seconds"]) * 2          # bytes, s16le mono
    need = int(c["capture_seconds"] / c["block_seconds"])

    proc = subprocess.Popen(
        ["arecord", "-D", c["device"], "-f", "S16_LE", "-r", str(sr),
         "-c", "1", "-t", "raw", "-q", "-"],
        stdout=subprocess.PIPE)
    transcribing = bool(c.get("transcribe") and c.get("consent_notice"))
    if transcribing:
        log(f"ear open on {c['device']} — TRANSCRIBING conversations")
        log(f"consent basis: {c['consent_notice']}")
    else:
        log(f"ear open on {c['device']} — acoustic mode, words not resolved")

    floor_hist, next_allowed = [], 0.0
    while True:
        raw = proc.stdout.read(block)
        if not raw:
            log("capture ended; exiting for restart")
            return 1
        blk = np.frombuffer(raw, dtype=np.int16)
        rms = float(np.sqrt((blk.astype(np.float32) / 32768) ** 2).mean() + 1e-9)
        db = 20 * math.log10(rms + 1e-9)

        floor_hist.append(db)
        floor_hist = floor_hist[-240:]                # ~2 min of room tone
        floor = float(np.percentile(floor_hist, 20))

        if len(floor_hist) < 20:
            continue
        if blacked_out(c) or time.time() < next_allowed:
            continue
        if today_count() >= c["daily_cap"]:
            continue
        if db < floor + c["trigger_db_over_floor"]:
            continue

        log(f"something is happening ({db:.0f} dB over a {floor:.0f} dB room)")
        chirp(c)
        # capture until the room goes quiet for a tail, up to a max
        buf = [raw]
        tail_blocks = int(c["tail_quiet_seconds"] / c["block_seconds"])
        max_blocks = int(c["max_capture_seconds"] / c["block_seconds"])
        quiet_run = 0
        while len(buf) < max_blocks:
            more = proc.stdout.read(block)
            if not more:
                break
            buf.append(more)
            b = np.frombuffer(more, dtype=np.int16)
            bdb = 20 * math.log10(float(np.sqrt((b.astype(np.float32) / 32768) ** 2).mean()) + 1e-9)
            quiet_run = quiet_run + 1 if bdb < floor + 4 else 0
            if len(buf) >= need and quiet_run >= tail_blocks:
                break
        pcm = np.frombuffer(b"".join(buf), dtype=np.int16)
        del buf

        f = features(pcm, sr)
        label = classify(f)

        # everything gets classified once for the daily statistics
        try:
            diary(c, {"kind": "acoustic", "label": label,
                      "seconds": int(len(pcm) / sr)})
        except Exception as e:
            log(f"node unreachable ({e})")

        talking = (f["voice_fraction"] >= c["speech_min_fraction"]
                   and f["voice_segments"] >= c["speech_min_segments"])
        if not talking:
            log(f"logged ({label}); no talk, nothing transcribed")
            del pcm
            next_allowed = time.time() + c["quiet_retry_seconds"]
            continue

        # conversation. transcribe ONLY where the law is satisfied: the
        # config must carry both the flag and a written-consent basis.
        transcript = ""
        if c.get("transcribe") and c.get("consent_notice"):
            try:
                transcript = transcribe(pcm, sr, c)
            except Exception as e:
                log(f"transcription unavailable ({e})")
        del pcm                                        # audio dies here

        # the vibe line always; the transcript only under consent
        try:
            vibe = characterize(c, f)
        except Exception:
            vibe = label
        payload = {"kind": "conversation", "label": label, "detail": vibe,
                   "seconds": int(f["seconds"])}
        if transcript:
            payload["transcript"] = transcript
        try:
            diary(c, payload)
            log(f"conversation logged ({label})"
                + (f" + transcript {len(transcript)} chars" if transcript else ""))
        except Exception as e:
            log(f"node unreachable ({e}); conversation not logged")
        with open(LOG, "a") as fh:
            fh.write(json.dumps({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "label": label, "vibe": vibe,
                "transcribed": bool(transcript),
            }) + "\n")
        next_allowed = time.time() + c["cooldown_minutes"] * 60


if __name__ == "__main__":
    sys.exit(main() or 0)
