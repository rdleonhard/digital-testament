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
import re
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
    "understands him better. It has two jobs, and no others.\n\n"
    "JOB 1 -- LEARN HOW HE WRITES. The persona has to sound like him, and a "
    "journal is the only place he writes with nobody watching. Study the "
    "prose itself, not the content: sentence length and rhythm, where he "
    "runs on and where he clips short, punctuation habits (dashes, "
    "ellipses, sentence fragments, capitalisation), his actual vocabulary, "
    "what he does with contractions and profanity, whether he addresses "
    "himself, how he opens and closes an entry. Quote his real phrases "
    "rather than describing them in the abstract. Do NOT comment on "
    "punctuation -- that is counted separately and is not your job. "
    "You will be given the style profile learned so "
    "far: REVISE it. Keep what the new entry confirms, sharpen what it "
    "clarifies, and only drop something if this entry actively contradicts "
    "it. Do not replace specifics with vaguer wording. If the entry is too "
    "short to tell you anything new about a field, return that field "
    "unchanged. 'register' is shown to you for context only -- it is "
    "curated by hand, so echo it, never rewrite it.\n\n"
    "JOB 2 -- FIND MEMORIES. Pull out the discrete, durable things worth "
    "remembering: what happened, who was there, what he did, decided, made, "
    "felt or noticed. One memory per distinct thing -- do not bundle a whole "
    "entry into one lump, and do not invent a memory to pad the list. A "
    "passing mention with nothing behind it is not a memory.\n\n"
    "Write each memory in HIS WORDS. This is the part people get wrong. Do "
    "not translate him into clean neutral prose -- keep his phrasing, his "
    "rhythm, his repetitions and his asides, first person. Where a line of "
    "his is striking, keep it verbatim. Compare:\n"
    "  BAD  (voice thrown away): 'Solved after two days of troubleshooting; "
    "the cause was the mDNS name rather than the firewall.'\n"
    "  GOOD (voice kept): 'Got the ESP32 talking to the Pi at last -- the "
    "mDNS name all along, not the firewall. Two days on that. Two days! "
    "Always the boring answer.'\n"
    "Titles work the same way: a plain concrete phrase, or one of his own. "
    "Mechanical rule -- a title must NOT be in Title Case and must not read "
    "like a headline. Begin it with a lowercase letter unless the first word "
    "is a proper noun, and use no more than seven words. "
    "'two days on the mDNS name' -- not 'ESP32 Connectivity Triumph'. "
    "Never state as fact anything the entry does not say.\n\n"
    "Reply ONLY with a JSON object:\n"
    '{"style": {"syntax": str, "diction": str, '
    '"tics": [str], "catchphrases": [str]}, '
    '"style_change": str (one short line on what this entry taught you, or '
    '"nothing new"), '
    '"memories": [{"title": str (under 70 chars, his kind of phrase, not a '
    'label), "narrative": str (first person, under 300 chars), '
    '"tags": [str]}], '
    '"mood": one of curious, cheerful, pensive, wistful, alert}'
)

# The persona prompt has PROMPT_MEM_BUDGET (6500) chars for ALL memories, and
# journal memories rotate against interviews and observations for it. An entry
# yielding five fat memories would crowd out the rest, so both the count and
# the length are capped and the raw entry is never itself a memory.
MEM_PER_ENTRY = 5
MEM_NARRATIVE_CAP = 300
MEM_TITLE_CAP = 70
STYLE_FIELD_CAP = 400
STYLE_LIST_CAP = 12

# Journals may only write the mechanical half of the voice. register and
# humor were written by hand and a single thin entry WILL flatten them into
# something vaguer if allowed to -- observed doing exactly that in testing.
# They are shown to the model for context and are structurally unwritable.
STYLE_FIELDS = ("syntax", "diction")
STYLE_LISTS = ("tics", "catchphrases")
STYLE_READONLY = ("register", "humor")
# punctuation is measured from the text, never asked for -- see
# measure_punctuation()


def _clean(s, cap):
    """Collapse whitespace and trim to cap on a word boundary."""
    s = " ".join((s or "").split())
    if len(s) <= cap:
        return s
    return s[:cap].rsplit(" ", 1)[0].rstrip(",;:-") + "..."


PUNCT_WORDS = re.compile(
    r"\b(ellips[ei]s|em-?dash|dash|parenthes[ei]s|semicolon|colon|comma|"
    r"exclamation|question mark|punctuation|capitalis|capitaliz)", re.I)


def _drop_punctuation_talk(s):
    """Remove punctuation claims from a prose style field.

    The model keeps describing punctuation inside 'syntax' even when told not
    to and when the measured profile is withheld from it -- and it gets the
    claims wrong, so the prompt ends up asserting he uses ellipses two
    sentences after the count says he never does. Punctuation has one
    authoritative source (the count); this strips the rival.
    """
    parts = re.split(r"\s*;\s*", s or "")
    kept = [p for p in parts if p and not PUNCT_WORDS.search(p)]
    out = "; ".join(kept).strip(" ;,")
    return out if out else ""


def _detitle(title):
    """Undo headline Title Case, preserving acronyms.

    Fires only when nearly every word is capitalised, which is the headline
    signature -- a sentence-style title ('Two days on the mDNS name') has
    lowercase function words and is left alone. Known cost: a proper noun
    inside a genuinely Title-Cased title loses its capital ('Called Mom' ->
    'called mom'). Judged the lesser evil against 'ESP32 LAN Communication
    Triumph', which two rounds of prompting failed to prevent.
    """
    words = title.split()
    alpha = [w for w in words if w[:1].isalpha()]
    if len(alpha) < 3:
        return title
    capped = [w for w in alpha if w[:1].isupper()]
    if len(capped) / len(alpha) < 0.8:
        return title
    out = []
    for w in words:
        out.append(w if w.isupper() and len(w) > 1 else w[:1].lower() + w[1:])
    return " ".join(out)


def measure_punctuation(text, stats):
    """Count his punctuation habits instead of asking the model about them.

    The model hallucinated ellipses and parentheses that were nowhere in the
    entry, twice, through two rounds of prompt tightening. Marks are
    countable, so they get counted -- accumulated across every entry, which
    also makes the description more truthful the more he pastes.
    """
    s = dict(stats or {})
    s["entries"] = s.get("entries", 0) + 1
    s["words"] = s.get("words", 0) + len(text.split())
    sents = [x for x in re.split(r"[.!?]+\s|\n+", text) if x.strip()]
    s["sentences"] = s.get("sentences", 0) + len(sents)
    for name, pat in (("dash", r"--|—|–"),
                      ("ellipsis", r"\.\.\.|…"),
                      ("paren", r"\("),
                      ("exclaim", r"!"),
                      ("question", r"\?"),
                      ("semicolon", r";"),
                      ("colon", r":"),
                      ("caps", r"\b[A-Z]{3,}\b")):
        s[name] = s.get(name, 0) + len(re.findall(pat, text))
    # sentence fragments: no finite verb is too hard, so use shortness
    s["fragments"] = s.get("fragments", 0) + sum(
        1 for x in sents if 0 < len(x.split()) <= 4)
    return s


def describe_punctuation(s):
    """Turn the counts into one honest sentence for the persona prompt."""
    if not s or not s.get("entries"):
        return ""
    sents = max(s.get("sentences", 0), 1)
    words = max(s.get("words", 0), 1)
    bits = ["averages {:.0f} words a sentence".format(words / sents)]
    per = lambda k: s.get(k, 0) / sents          # noqa: E731
    named = (("dash", "em-dashes"), ("ellipsis", "ellipses"),
             ("paren", "parentheses"), ("exclaim", "exclamation marks"),
             ("semicolon", "semicolons"), ("colon", "colons"))
    used = [(label, per(k)) for k, label in named if s.get(k, 0)]
    used.sort(key=lambda x: -x[1])
    for label, rate in used[:3]:
        if rate >= 0.5:
            bits.append("leans on {} heavily".format(label))
        elif rate >= 0.15:
            bits.append("uses {} regularly".format(label))
        else:
            bits.append("uses {} sparingly".format(label))
    unused = [label for k, label in named if not s.get(k, 0)]
    if unused:
        bits.append("never uses " + ", ".join(unused[:3]))
    if per("fragments") >= 0.2:
        bits.append("writes in fragments often")
    if s.get("caps", 0):
        bits.append("shouts in capitals occasionally")
    return ("Measured across {} entr{}: ".format(
        s["entries"], "y" if s["entries"] == 1 else "ies") + "; ".join(bits)
        + ".")


def learned_style(context=False):
    """The style profile as it stands.

    context=True also includes the hand-curated read-only fields, which the
    model needs to see to stay consistent but must not overwrite.
    """
    v = corpus.get("voice", {})
    out = {f: v.get(f, "") for f in STYLE_FIELDS}
    for f in STYLE_LISTS:
        out[f] = [x for x in (v.get(f) or []) if isinstance(x, str)]
    if context:
        # context=True is the model-facing view. Punctuation is withheld from
        # it on purpose: when the model could see it, it started describing
        # punctuation inside the syntax field and contradicted the count.
        for f in STYLE_READONLY:
            if v.get(f):
                out[f] = v[f]
    elif v.get("punctuation"):
        out["punctuation"] = v["punctuation"]
    return out


def merge_style(new):
    """Fold a revised profile into corpus['voice'].

    Merged rather than assigned: the seed voice block was written by hand and
    is good, so a thin entry must not be able to flatten it. Lists union
    (his phrases accumulate); strings only overwrite when the model actually
    returned something. The pre-journal voice is snapshotted once so the
    hand-written original is always recoverable.
    """
    v = corpus.setdefault("voice", {})
    if "voice_seed" not in corpus:
        corpus["voice_seed"] = json.loads(json.dumps(v))
    changed = []
    for f in STYLE_FIELDS:
        cand = _clean(_drop_punctuation_talk(new.get(f)), STYLE_FIELD_CAP)
        if cand and cand != v.get(f):
            v[f] = cand
            changed.append(f)
    # Phrases and habits need corroboration before they reach the persona
    # prompt. One entry saying a thing once is not a catchphrase -- observed
    # promoting "Got the ESP32 talking..." off a single sighting, which the
    # avatar would then have parroted forever. A candidate must turn up in a
    # second entry to graduate.
    pool = corpus.setdefault("voice_candidates", {})
    for f in STYLE_LISTS:
        have = [x for x in (v.get(f) or []) if isinstance(x, str)]
        seen = {x.strip().lower() for x in have}
        waiting = pool.setdefault(f, {})
        # established entries in EITHER list disqualify a candidate: the model
        # echoes known catchphrases back inside "tics", which would otherwise
        # queue them all over again in the other list's waiting room
        established = set(seen)
        for other in STYLE_LISTS:
            established |= {x.strip().lower()
                            for x in (v.get(other) or [])
                            if isinstance(x, str)}
        promoted, noted = 0, 0
        for cand in (new.get(f) or []):
            if not isinstance(cand, str):
                continue
            cand = _clean(cand, 120)
            key = cand.strip().lower()
            if not cand or key in established:
                continue            # already established somewhere
            if waiting.get(key, {}).get("n", 0) >= 1:
                have.append(cand)   # second sighting: graduate it
                seen.add(key)
                waiting.pop(key, None)
                promoted += 1
            else:
                waiting[key] = {"n": 1, "text": cand}
                noted += 1
        if promoted:
            # keep the newest -- his current voice beats his 2019 voice
            v[f] = have[-STYLE_LIST_CAP:]
            changed.append("{}(+{})".format(f, promoted))
        if noted:
            changed.append("{}?{}".format(f, noted))
        # do not let the waiting room grow without bound
        if len(waiting) > 40:
            pool[f] = dict(list(waiting.items())[-40:])
    return changed


def style_candidates():
    """Phrases seen once, still waiting for a second sighting."""
    pool = corpus.get("voice_candidates", {})
    return {f: [d.get("text", "") for d in (pool.get(f) or {}).values()]
            for f in STYLE_LISTS}


def journal_path():
    return BASE / "journals.jsonl"


def do_journal(text, note=None):
    """Read a pasted journal entry for style, and mine it for memories.

    Two outputs. The style profile in corpus['voice'] gets revised, so the
    persona gradually learns to write like him rather than like a model.
    Discrete memories are lifted out in his own first-person phrasing and
    committed to the corpus -- his words, because the corpus is what teaches
    the persona to talk.

    The raw entry is archived verbatim to journals.jsonl and is never itself
    a memory: the persona prompt has a fixed character budget one long entry
    would swallow, and the Compilation will want the entry whole anyway.

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

    # Nothing but the entry itself goes in the user turn. An earlier version
    # appended a free-text "handing it over" note here and the model duly
    # mined the note for memories and catchphrases, filing the metadata as if
    # he had written it. The note served the old why-did-he-share-this
    # question and is gone with it; anything still sending one is ignored.
    ask = ("Style profile learned so far. Revise 'syntax', 'diction', "
           "'tics' and 'catchphrases' only -- 'register' and 'humor' are "
           "context for you and are maintained by hand:\n"
           + json.dumps(learned_style(context=True), indent=2)
           + "\n\nJournal entry:\n\n" + text[:12000])

    raw = local([{"role": "system", "content": ARCHIVIST},
                 {"role": "user", "content": ask}],
                max_tokens=1400, fmt="json")
    try:
        a = json.loads(raw)
    except ValueError:
        raise RuntimeError(
            "the model did not return usable JSON; entry not filed "
            "(it is still in the box -- try again)")

    mood = a.get("mood") if a.get("mood") in avatar.MOODS else "pensive"

    # --- job 1: style ---
    style_changed = merge_style(a.get("style") or {})
    # punctuation is counted, not inferred, and accumulates over every entry
    corpus["voice_stats"] = measure_punctuation(
        text, corpus.get("voice_stats"))
    desc = describe_punctuation(corpus["voice_stats"])
    if desc:
        corpus.setdefault("voice", {})["punctuation"] = desc
        style_changed.append("punctuation(measured)")

    # --- job 2: memories ---
    have_titles = {(m.get("title") or "").strip().lower()
                   for m in corpus.get("memories", [])}
    added = []
    for cand in (a.get("memories") or [])[:MEM_PER_ENTRY]:
        if not isinstance(cand, dict):
            continue
        title = _detitle(_clean(cand.get("title"), MEM_TITLE_CAP))
        narrative = _clean(cand.get("narrative"), MEM_NARRATIVE_CAP)
        if not narrative:
            continue
        if not title:
            title = narrative[:60]
        if title.strip().lower() in have_titles:
            continue                      # same beat already remembered
        have_titles.add(title.strip().lower())
        tags = ["journal"] + [_clean(t, 24) for t in (cand.get("tags") or [])[:3]
                              if isinstance(t, str)]
        mem = {"title": title, "narrative": narrative, "tags": tags}
        corpus.setdefault("memories", []).append(mem)
        added.append(mem)

    avatar.save(corpus)
    backup_corpus()
    prompt = avatar.build_prompt(corpus)

    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "text": text,
             "note": note, "chars": len(text),
             "style": a.get("style") or {},
             "style_change": a.get("style_change", ""),
             "style_changed": style_changed,
             "memories": added}
    with journal_path().open("a") as f:
        f.write(json.dumps(entry) + "\n")

    state["mood"] = mood
    if buz:
        buz.mood(mood)
    return {"style": learned_style(),
            "candidates": style_candidates(),
            "style_change": a.get("style_change", ""),
            "style_changed": style_changed,
            "memories": added, "mood": mood,
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
                    "style_change": j.get("style_change", ""),
                    "n_memories": len(j.get("memories") or [])})
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
