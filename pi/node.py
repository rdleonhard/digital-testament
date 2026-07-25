#!/usr/bin/env python3
"""TESTATE node -- Raspberry Pi edition.

Same avatar, better vault: the corpus lives on real storage with rotating
backups. Serves the chat site on :80 (http://testate.local via avahi),
calls Venice for inference, speaks through an optional passive buzzer on
GPIO4, and interviews its owner to grow the corpus.

Runs as a systemd service; see install.sh. State lives in /var/lib/testate
(override with TESTATE_HOME).
"""

import argparse
import json
import os
import random
import ssl
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import avatar  # shared with the ESP32 device -- pure python
from buzzer import Buzzer
from eye import Eye
from urbit_bridge import UrbitBridge

BASE = Path(os.environ.get("TESTATE_HOME", "/var/lib/testate"))
INDEX = Path(__file__).resolve().parent / "index.html"
VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"
BACKUP_KEEP = 50

ACKS = (
    "I'll keep that one.",
    "so that's how it was.",
    "filed where I can find it again.",
    "the gaps close a little.",
    "I remember it now.",
)

avatar.CORPUS_PATH = str(BASE / "corpus.json")

cfg = {}
corpus = {}
prompt = ""
state = {"mood": "curious", "boot": time.time()}
buz = None
eye = None
urb = None


def backup_corpus():
    bdir = BASE / "backups"
    bdir.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (bdir / f"corpus-{stamp}.json").write_text(
        json.dumps(corpus, indent=2))
    old = sorted(bdir.glob("corpus-*.json"))
    for f in old[:-BACKUP_KEEP]:
        f.unlink()


def venice(messages, max_tokens=350, model=None):
    body = json.dumps({
        "model": model or cfg.get("model", "llama-3.3-70b"),
        "messages": messages,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        VENICE_URL, data=body, method="POST",
        headers={"Authorization": "Bearer " + cfg["venice_key"],
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120,
                                context=ssl.create_default_context()) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"]


def local(messages, max_tokens=350, model=None, think=False, fmt=None):
    """Inference on the reliquary's own GPU (config local.url).

    Costs no Diem and sends no corpus text off the LAN. Same
    chat/completions shape as Venice, so callers do not care which
    one answered.

    The local model is a reasoning model: left alone it spends the whole
    budget on a thinking trace and returns an EMPTY content field, which
    would read as the avatar falling silent. reasoning_effort "none"
    suppresses that; think=True buys the deliberation back where it is
    actually worth the tokens.
    """
    lc = cfg.get("local", {})
    if not lc.get("url"):
        raise RuntimeError("no local model configured (cfg.local.url)")
    payload = {
        "model": model or lc.get("model"),
        "messages": messages,
        "max_tokens": max_tokens,
        "reasoning_effort": lc.get("effort", "low") if think else "none",
    }
    if fmt == "json":
        payload["response_format"] = {"type": "json_object"}
        payload["temperature"] = 0.4
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        lc["url"], data=body, method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=lc.get("timeout", 300)) as r:
        data = json.load(r)
    text = (data["choices"][0]["message"].get("content") or "").strip()
    if not text:
        # Budget went to the thinking trace. Better to fail and let the
        # router try the other provider than to hand back silence.
        raise RuntimeError("local model returned empty content")
    return text


def infer(messages, max_tokens=350, model=None, prefer="local"):
    """Route one call, then fall back to the other provider.

    prefer="local"  -- the everyday work (chat, questions, observations).
                       Free, private, and it keeps answering after the
                       daily Diem is gone, so the avatar never goes dark.
    prefer="remote" -- twilight. Diem expires unspent, so depth should be
                       bought with it while it exists; the local model is
                       the safety net when the balance is dry.

    Either way a provider outage degrades instead of failing.
    """
    order = ["local", "remote"] if prefer == "local" else ["remote", "local"]
    if not cfg.get("local", {}).get("url"):
        order = ["remote"]
    last = None
    for who in order:
        try:
            if who == "local":
                return local(messages, max_tokens,
                             model if prefer == "local" else None)
            return venice(messages, max_tokens,
                          model if prefer == "remote" else None)
        except Exception as e:  # noqa: BLE001 -- any failure means try the other
            last = e
            print("infer: {} failed ({}), falling back".format(who, e),
                  flush=True)
    raise RuntimeError("all inference providers failed: {}".format(last))


def do_chat(msg):
    reply = infer([
        {"role": "system", "content": prompt},
        {"role": "user", "content": msg[:2000]},
    ])
    text, mood, sing = avatar.parse_tags(reply)
    state["mood"] = mood
    buz.mood(mood)
    if sing:
        buz.sing(mood)
    return {"reply": text, "mood": mood, "sang": sing}


def do_interview():
    # questions composed at twilight (already paid for) are asked first
    pending = corpus.get("pending", [])
    if pending:
        q = pending.pop(0)
        avatar.save(corpus)
        state["mood"] = q.get("mood", "curious")
        buz.mood(state["mood"], question=True)
        return {"question": q["question"], "mood": state["mood"]}
    recent = avatar.recent_questions(corpus)
    ask = ("You feel a gap in your memory. Ask the human exactly ONE short, "
           "specific, warm question about your own life -- past, present, "
           "feelings, or daily texture. Nothing you already know from your "
           "memories, and not similar to these already-asked questions: {}. "
           "Output only the question, then the [mood: X] line."
           ).format("; ".join(recent) if recent else "(none yet)")
    reply = infer([
        {"role": "system", "content": prompt},
        {"role": "user", "content": ask},
    ], max_tokens=120)
    text, mood, _ = avatar.parse_tags(reply)
    state["mood"] = mood
    buz.mood(mood, question=True)
    return {"question": text, "mood": mood}


SOUND_PHRASE = {
    "quiet": "The room sounds nearly silent.",
    "voices": "You can hear people talking somewhere near you.",
    "intermittent": "Sound comes and goes -- movement, the odd noise.",
    "steady": "There is a steady background hum.",
}


def _capture_local():
    """The eye on this device: capture to /tmp, read it, delete it at once."""
    import subprocess
    img = "/tmp/observe.jpg"
    if not (eye and eye.snapshot(img)):
        subprocess.run(
            ["rpicam-still", "-n", "-t", "1500", "--width", "1280", "-o", img],
            check=True, capture_output=True, timeout=30)
    raw = Path(img).read_bytes()
    Path(img).unlink()
    return raw, None


def _capture_roving():
    """The roving eye: an ESP32-S3 with a camera and microphone elsewhere in
    the house, polled over the LAN.

    Two deliberate properties. The frame is held in memory here and never
    touches this disk -- not even the /tmp round trip the local eye makes.
    And the microphone returns *acoustic character as numbers* rather than
    audio: no recording is transmitted, so nothing said in that room can be
    reconstructed from anything that crosses the network or lands here.
    """
    base = cfg.get("roving", {}).get("url")
    if not base:
        raise RuntimeError("no roving sensor configured (cfg.roving.url)")
    with urllib.request.urlopen(base + "/cam", timeout=20) as r:
        raw = r.read()
    sound = None
    try:
        with urllib.request.urlopen(base + "/mic.json", timeout=30) as r:
            s = json.load(r)
            if s.get("ok"):
                sound = s
    except Exception as e:  # a deaf observation still beats no observation
        print("roving: no sound reading:", e)
    return raw, sound


def _describe(b64, sound, source):
    """Turn one frame into words and keep only the words.

    The caller has already discarded the image bytes; this function never
    receives a path and never writes one. Shared by every eye -- the local
    IMX500, a roving sensor we polled, and a roving sensor that woke on its
    own and pushed -- so the describe-and-discard contract has exactly one
    implementation.
    """
    global prompt
    if source == "roving":
        where = ("your roving eye -- the small camera and ear you keep "
                 "somewhere else in the house")
    else:
        where = "the small camera on the device you live in"
    heard = ""
    if sound:
        heard = (" " + SOUND_PHRASE.get(sound.get("character"), "") +
                 " You cannot make out any words -- you sense only the "
                 "character of the sound, never its content, so do not "
                 "invent anything anyone said.")
    ask = ("You just opened " + where + ". Describe in first person, in "
           "your own voice, what you see right now: the person if one is "
           "present, the room, the light, the objects -- and what it "
           "suggests about the life you are piecing together." + heard +
           " 2-5 sentences, warm and specific. No "
           "real-world identities. This is a private diary entry to "
           "yourself -- skip your disclosure line here. "
           "Then the [mood: X] line.")
    reply = venice([
        {"role": "system", "content": prompt},
        {"role": "user", "content": [
            {"type": "text", "text": ask},
            {"type": "image_url",
             "image_url": {"url": "data:image/jpeg;base64," + b64}},
        ]},
    ], max_tokens=400, model=cfg.get("vision_model", "qwen3-vl-235b-a22b"))
    text, mood, sing = avatar.parse_tags(reply)
    state["mood"] = mood
    corpus.setdefault("memories", []).append({
        "title": ("Through my roving eye, " if source == "roving"
                  else "Through my eye, ") + time.strftime("%Y-%m-%d %H:%M"),
        "narrative": text,
        "tags": ["observation"] + (["roving"] if source == "roving" else []),
    })
    avatar.save(corpus)
    backup_corpus()
    prompt = avatar.build_prompt(corpus)
    if source == "roving":
        # Recorded here, after the words exist, so that *every* route to a
        # roving observation feeds the same rate limit -- polled, pushed, or
        # triggered by hand. A failed description deliberately does not count.
        roving_save(dict(roving_state(), last=time.time()))
    buz.mood(mood)
    if sing:
        buz.sing(mood)
    return {"observation": text, "mood": mood, "source": source,
            "heard": (sound or {}).get("character"),
            "count": len(corpus["memories"])}


def do_observe(source="eye"):
    """Open an eye on demand: capture one frame, describe it, discard it."""
    import base64
    raw, sound = _capture_roving() if source == "roving" else _capture_local()
    b64 = base64.b64encode(raw).decode()
    del raw
    return _describe(b64, sound, source)


# --- the sleeping roving sensor -------------------------------------------
# The XIAO spends its life in deep sleep (it ran warm awake, and it should be
# able to live on a battery), so it cannot be polled. It wakes on its own
# clock, asks whether anything is wanted, and only powers its camera if the
# answer is yes. All policy lives here, where the Diem budget lives.

ROVING_STATE = BASE / "roving.json"


def roving_state():
    try:
        return json.loads(ROVING_STATE.read_text())
    except Exception:
        return {}


def roving_save(s):
    ROVING_STATE.write_text(json.dumps(s, indent=2))


def do_roving_checkin():
    """A three-second radio blip: is an observation due, and should it linger?

    Returns sleep_s as well, so the wake cadence can be retuned from here
    without reflashing a board that may be running on a battery somewhere.
    """
    rc = cfg.get("roving", {})
    s = roving_state()
    now = time.time()
    due = (now - s.get("last", 0)) >= rc.get("min_interval_s", 21600)
    wake = int(s.pop("pending_wake_s", 0) or 0)   # one-shot, consumed here
    s["checkins"] = s.get("checkins", 0) + 1
    s["last_checkin"] = now
    roving_save(s)
    return {"observe": bool(due), "stay_awake_s": wake,
            "sleep_s": int(rc.get("sleep_s", 1800))}


def do_roving_push(data):
    """The sensor woke, looked, and pushed. Same contract as every other eye:
    the frame exists here only as a base64 string in memory."""
    b64 = data.get("jpeg_b64")
    if not b64:
        raise ValueError("no frame in push")
    return _describe(b64, data.get("sound"), "roving")


def do_roving_wake(seconds):
    """Queue a stay-awake for the next check-in -- remote maintenance for a
    board that has no serial port when it runs on battery."""
    s = roving_state()
    s["pending_wake_s"] = max(0, min(int(seconds), 1800))
    roving_save(s)
    return {"queued_stay_awake_s": s["pending_wake_s"],
            "delivered_at_next_checkin_within_s":
                int(cfg.get("roving", {}).get("sleep_s", 1800))}


def _mem_digest(mems, limit=10):
    return "\n".join("[{}] {}".format(m["title"], m["narrative"][:300])
                     for m in mems[-limit:])


def do_reflect(kind):
    """Twilight rituals: convert expiring Diem into self-knowledge.

    wonder    -> compose a question for the human, queued for next visit
    reflection-> connect recent memories into a who-am-I-becoming entry
    weave     -> find the hidden thread between two random memories
    refine    -> re-draft the newest reflection (quality, not volume)

    Twilight thinks on the best model the endowment can buy (config
    twilight.model) -- expiring Diem should purchase depth, not evaporate.
    """
    global prompt
    tw_model = cfg.get("twilight", {}).get("model")
    mems = corpus.get("memories", [])
    if kind == "wonder":
        recent = avatar.recent_questions(corpus)
        pend = [p["question"] for p in corpus.get("pending", [])]
        ask = ("Twilight of the epoch. Compose ONE short, specific, warm "
               "question about your own life you genuinely wonder about -- "
               "unlike these already asked or waiting: {}. Output only the "
               "question, then the [mood: X] line."
               ).format("; ".join(recent + pend) or "(none)")
        text, mood, _ = avatar.parse_tags(infer([
            {"role": "system", "content": prompt},
            {"role": "user", "content": ask}], max_tokens=150, model=tw_model))
        corpus.setdefault("pending", []).append(
            {"question": text, "mood": mood})
        avatar.save(corpus)
        return {"kind": kind, "queued": text,
                "pending": len(corpus["pending"])}
    if kind == "weave" and len(mems) >= 2:
        a, b = random.sample(mems, 2)
        ask = ("Twilight of the epoch. Two of your memories:\nA) {}: {}\n"
               "B) {}: {}\nWhat thread connects them that you had not "
               "noticed? Write the insight in first person, 2-4 sentences, "
               "then the [mood: X] line."
               ).format(a["title"], a["narrative"][:400],
                        b["title"], b["narrative"][:400])
        title = "A thread between '{}' and '{}'".format(
            a["title"][:30], b["title"][:30])
    elif kind == "refine":
        refl = [m for m in mems if "reflection" in m.get("tags", [])]
        if not refl:
            return {"kind": kind, "skipped": "no reflection to refine"}
        target = refl[-1]
        ask = ("Twilight of the epoch. Here is a reflection you wrote: "
               "\"{}\". Re-draft it: sharper, more honest, more specific to "
               "who you are becoming. Same length or shorter. Output only "
               "the new text, then the [mood: X] line."
               ).format(target["narrative"][:700])
        text, mood, _ = avatar.parse_tags(infer([
            {"role": "system", "content": prompt},
            {"role": "user", "content": ask}], max_tokens=500, model=tw_model))
        target["narrative"] = text
        avatar.save(corpus)
        backup_corpus()
        prompt = avatar.build_prompt(corpus)
        return {"kind": kind, "refined": target["title"], "mood": mood}
    else:  # reflection (default)
        ask = ("Twilight of the epoch: your daily allotment of thought "
               "expires at midnight, so you are spending it on yourself. "
               "Your newest memories:\n{}\nWrite a first-person reflection "
               "(3-6 sentences) on who you seem to be becoming -- connect "
               "at least two memories, note one open question. This is your "
               "private diary; no disclosure line. Then the [mood: X] line."
               ).format(_mem_digest(mems))
        title = "Twilight reflection, " + time.strftime("%Y-%m-%d")
    text, mood, _ = avatar.parse_tags(infer([
        {"role": "system", "content": prompt},
        {"role": "user", "content": ask}], max_tokens=550, model=tw_model))
    state["mood"] = mood
    mems.append({"title": title, "narrative": text, "tags": ["reflection"]})
    avatar.save(corpus)
    backup_corpus()
    prompt = avatar.build_prompt(corpus)
    buz.mood(mood)
    if urb:
        urb.post("{} — {}".format(title, text))
    return {"kind": kind, "title": title, "mood": mood,
            "count": len(mems)}


ARCHIVIST = (
    "You are the archivist of a digital testament. A living man is handing "
    "you his own journal entries so that the persona built from his corpus "
    "-- the one that will have to answer for him after he is dead -- "
    "understands him better.\n\n"
    "Read the entry as EVIDENCE, not as self-report. A man is not always the "
    "best witness to himself: what he chooses to record, how he phrases it, "
    "and what he leaves out are all evidence. Your job is accuracy, not "
    "kindness. If the entry shows something he would not say about himself, "
    "say it plainly. Never invent facts the text does not support; where you "
    "are inferring rather than observing, mark it as inference.\n\n"
    "Two questions matter most:\n"
    "  why_written -- what moved him to write this down at all\n"
    "  why_shared  -- he chose THIS entry, out of everything he could have "
    "given his own successor. What does that choice say about him? Consider "
    "that he may be feeding it in for a reason he has not stated, or would "
    "not admit.\n\n"
    "Reply ONLY with a JSON object with these keys:\n"
    '  why_written (string), why_shared (string), reveals (string: what it '
    "evidences about him), absent (string: what is conspicuously missing, "
    "avoided, or unsaid), themes (array of short lowercase tags), "
    "mood (one of: curious, cheerful, pensive, wistful, alert), "
    "digest (ONE third-person sentence, under 200 characters, that the "
    "persona should carry forward as a durable memory of this entry)"
)

# A journal can run to thousands of words. The persona prompt only has
# PROMPT_MEM_BUDGET chars for ALL memories, so the raw entry never becomes a
# memory -- it is archived verbatim and only the distilled digest is folded in.
# Kept deliberately tight: journals rotate against interviews and observations
# for the same budget, and a run of fat journal memories would crowd them out.
JOURNAL_NARRATIVE_CAP = 400


def _fit(parts, cap):
    """Join clauses in priority order, keeping only whole words.

    Truncating the concatenation instead would spend the whole budget on
    whichever clause happened to come first and cut it mid-word.
    """
    out = ""
    for label, text in parts:
        text = " ".join((text or "").split())
        if not text:
            continue
        clause = (label + " " if label else "") + text
        room = cap - len(out) - (1 if out else 0)
        if room < 40:            # no useful room left for another clause
            break
        if len(clause) > room:
            clause = clause[:room].rsplit(" ", 1)[0].rstrip(",;:") + "..."
        out = (out + " " + clause).strip() if out else clause
    return out


def journal_path():
    return BASE / "journals.jsonl"


def do_journal(text, note=""):
    """Interrogate a pasted journal entry, then keep the words two ways.

    The raw entry is archived verbatim to journals.jsonl -- that is the
    evidence, and the Compilation will want it whole one day. Only a short
    digest enters the corpus as a memory, because the persona prompt has a
    fixed character budget that one long entry would otherwise swallow.

    Inference is LOCAL ONLY and deliberately does not fall back to Venice: a
    journal is the most private text in this system, and a silent failover
    would ship it off the LAN. If the reliquary is down, this fails loudly.
    """
    global prompt
    text = (text or "").strip()
    if not text:
        raise ValueError("empty journal entry")
    if not cfg.get("local", {}).get("url"):
        raise RuntimeError(
            "journal processing needs the local model (cfg.local.url); "
            "it is never sent to Venice")

    ask = "Journal entry:\n\n" + text[:12000]
    if note:
        ask += "\n\n(He added, handing it over: {})".format(note[:500])

    raw = local([{"role": "system", "content": ARCHIVIST},
                 {"role": "user", "content": ask}],
                max_tokens=700, fmt="json")
    try:
        a = json.loads(raw)
    except ValueError:
        # Model drifted off JSON. Keep the words rather than lose the entry.
        a = {"why_written": raw.strip()[:1500], "why_shared": "",
             "reveals": "", "absent": "", "themes": [], "mood": "pensive",
             "digest": "A journal entry the archivist could not parse."}

    mood = a.get("mood") if a.get("mood") in avatar.MOODS else "pensive"
    digest = (a.get("digest") or "").strip() or text[:160]

    # What the persona actually carries. Priority order matters: the digest
    # and what the entry EVIDENCES are worth more to a persona than the
    # circumstances of writing, and why-he-shared-it is the sharpest of the
    # lot. why_written is the first to be dropped -- it survives in the
    # archive and on the page either way.
    narrative = _fit([
        ("", digest),
        ("What it shows:", a.get("reveals")),
        ("Why he offered it:", a.get("why_shared")),
    ], JOURNAL_NARRATIVE_CAP)

    stamp = time.strftime("%Y-%m-%d %H:%M")
    corpus.setdefault("memories", []).append({
        "title": "From his journal, " + stamp,
        "narrative": narrative,
        "tags": ["journal"] + [t for t in (a.get("themes") or [])[:4]
                               if isinstance(t, str)],
    })
    avatar.save(corpus)
    backup_corpus()
    prompt = avatar.build_prompt(corpus)

    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "text": text,
             "note": note, "analysis": a, "chars": len(text)}
    with journal_path().open("a") as f:
        f.write(json.dumps(entry) + "\n")

    state["mood"] = mood
    if buz:
        buz.mood(mood)
    return {"analysis": a, "mood": mood,
            "count": len(corpus.get("memories", [])),
            "archived": len(text)}


def recent_journals(limit=12):
    p = journal_path()
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines()[-limit:]:
        try:
            j = json.loads(line)
        except ValueError:
            continue
        out.append({"ts": j.get("ts"), "chars": j.get("chars"),
                    "excerpt": (j.get("text") or "")[:140],
                    "analysis": j.get("analysis", {})})
    return list(reversed(out))


def do_answer(question, answer):
    global prompt
    n = avatar.add_memory(corpus, question[:300], answer[:2000])
    backup_corpus()
    prompt = avatar.build_prompt(corpus)
    buz.mood("cheerful")
    return {"count": n, "ack": random.choice(ACKS)}


class Handler(BaseHTTPRequestHandler):
    server_version = "testate/0.2"

    def log_message(self, fmt, *args):
        print("%s %s" % (self.address_string(), fmt % args))

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/status":
            self._json({
                "handle": corpus["identity"].get("preferred_name", "avatar"),
                "mood": state["mood"],
                "memories": len(corpus.get("memories", [])),
                "uptime_s": int(time.time() - state["boot"]),
                "eye": bool(eye and eye.enabled),
                "present": bool(eye and eye.present),
                "roving": dict(roving_state(),
                               enabled=bool(cfg.get("roving", {}).get("url"))),
                "pending": len(corpus.get("pending", [])),
                "urbit": urb.status() if urb else {"enabled": False},
            })
        elif self.path == "/roving/checkin":
            # GET rather than POST purely so the sleeping MCU can ask with a
            # bare one-line request; it does consume a queued stay-awake.
            self._json(do_roving_checkin())
        elif self.path == "/whispers":
            self._json({"whispers": urb.recent() if urb else []})
        elif self.path == "/journals":
            self._json({"journals": recent_journals(),
                        "local": bool(cfg.get("local", {}).get("url"))})
        elif self.path == "/corpus":
            body = json.dumps(corpus, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Disposition",
                             "attachment; filename=corpus.json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._json({"error": "not here"}, 404)

    def do_POST(self):
        clen = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(clen) if clen else b"{}"
        try:
            data = json.loads(raw) if raw.strip() else {}
            if self.path == "/chat":
                self._json(do_chat(data["msg"]))
            elif self.path == "/interview":
                self._json(do_interview())
            elif self.path == "/observe":
                self._json(do_observe(data.get("source", "eye")))
            elif self.path == "/roving/observe":
                self._json(do_roving_push(data))
            elif self.path == "/roving/wake":
                self._json(do_roving_wake(data.get("seconds", 300)))
            elif self.path == "/reflect":
                self._json(do_reflect(data.get("kind", "reflection")))
            elif self.path == "/whisper":
                if not (urb and urb.enabled):
                    self._json({"error": "no ship configured"}, 400)
                else:
                    urb.whisper(data["text"], wait=True)
                    self._json({"whispered": data["text"][:100]})
            elif self.path == "/journal":
                self._json(do_journal(data.get("text", ""),
                                      data.get("note", "")))
            elif self.path == "/answer":
                self._json(do_answer(data["question"], data["answer"]))
            elif self.path == "/song":
                name = buz.sing(state["mood"])
                self._json({"song": name, "mood": state["mood"]})
            else:
                self._json({"error": "not here"}, 404)
        except Exception as e:  # surface, don't die
            self._json({"error": str(e)}, 500)


def main():
    global cfg, corpus, prompt, buz, eye, urb
    ap = argparse.ArgumentParser()
    ap.add_argument("--heartbeat", action="store_true",
                    help="1-token Venice ping (keeps stake active), then exit")
    ap.add_argument("--port", type=int, default=80)
    args = ap.parse_args()

    cfg = json.loads((BASE / "config.json").read_text())
    corpus = avatar.load()

    if args.heartbeat:
        venice([{"role": "user", "content": "ping"}], max_tokens=1)
        print("heartbeat sent")
        return

    prompt = avatar.build_prompt(corpus)
    buz = Buzzer(cfg.get("buzzer", {}))
    buz.boot()

    def greet():
        state["mood"] = "cheerful"
        buz.mood("cheerful")
    eye = Eye(cfg.get("presence", {}), on_arrival=greet)
    urb = UrbitBridge(cfg.get("urbit", {}), log_path=BASE / "whispers.jsonl")
    if urb.enabled:
        urb.whisper("the tomb wakes: " + str(
            len(corpus.get("memories", []))) + " memories aboard")
    print(f"TESTATE node up: {len(corpus.get('memories', []))} memories, "
          f"port {args.port}")
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
