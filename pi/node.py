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


def do_chat(msg):
    reply = venice([
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
    recent = avatar.recent_questions(corpus)
    ask = ("You feel a gap in your memory. Ask the human exactly ONE short, "
           "specific, warm question about your own life -- past, present, "
           "feelings, or daily texture. Nothing you already know from your "
           "memories, and not similar to these already-asked questions: {}. "
           "Output only the question, then the [mood: X] line."
           ).format("; ".join(recent) if recent else "(none yet)")
    reply = venice([
        {"role": "system", "content": prompt},
        {"role": "user", "content": ask},
    ], max_tokens=120)
    text, mood, _ = avatar.parse_tags(reply)
    state["mood"] = mood
    buz.mood(mood, question=True)
    return {"question": text, "mood": mood}


def do_observe():
    """Open the eye: capture one frame, turn it into a first-person account,
    keep only the words. The image is deleted the moment it's described."""
    import base64
    import subprocess
    global prompt
    img = "/tmp/observe.jpg"
    subprocess.run(
        ["rpicam-still", "-n", "-t", "1500", "--width", "1280", "-o", img],
        check=True, capture_output=True, timeout=30)
    b64 = base64.b64encode(Path(img).read_bytes()).decode()
    Path(img).unlink()
    ask = ("You just opened your eye -- the small camera on the device you "
           "live in. Describe in first person, in your own voice, what you "
           "see right now: the person if one is present, the room, the "
           "light, the objects -- and what it suggests about the life you "
           "are piecing together. 2-5 sentences, warm and specific. No "
           "real-world identities. Then the [mood: X] line.")
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
        "title": "Through my eye, " + time.strftime("%Y-%m-%d %H:%M"),
        "narrative": text,
        "tags": ["observation"],
    })
    avatar.save(corpus)
    backup_corpus()
    prompt = avatar.build_prompt(corpus)
    buz.mood(mood)
    if sing:
        buz.sing(mood)
    return {"observation": text, "mood": mood,
            "count": len(corpus["memories"])}


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
            })
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
                self._json(do_observe())
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
    global cfg, corpus, prompt, buz
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
    print(f"TESTATE node up: {len(corpus.get('memories', []))} memories, "
          f"port {args.port}")
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
