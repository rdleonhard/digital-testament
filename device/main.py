"""TESTATE node: self-hosted digital-avatar server for ESP32-S3.

Boots WiFi as `testate` (-> http://testate.local via mDNS), serves the chat
site from flash, keeps the corpus on flash, calls Venice for inference, and
speaks through the GPIO4 buzzer: a mood jingle with a rising interrogative
tail when it asks about its own life, and the occasional song.
"""

import json
import random
import time

import network

import avatar
import venice
from tunes import BOOT_CHIRP, Buzzer

ACKS = (
    "I'll keep that one.",
    "so that's how it was.",
    "filed where I can find it again.",
    "the gaps close a little.",
    "I remember it now.",
)

state = {"mood": "curious", "boot": time.time()}
buz = Buzzer()


def load_cfg():
    with open("config.json") as f:
        return json.load(f)


def wifi_up(cfg):
    network.hostname(cfg.get("hostname", "testate"))
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(cfg["wifi_ssid"], cfg["wifi_pass"])
        for _ in range(40):
            if wlan.isconnected():
                break
            time.sleep(0.5)
    if not wlan.isconnected():
        raise OSError("wifi failed")
    print("wifi:", wlan.ifconfig()[0], "-> http://%s.local" % cfg.get("hostname", "testate"))
    return wlan


# ---- HTTP plumbing (single client at a time, deliberately tiny) ----

def read_request(conn):
    conn.settimeout(10)
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = conn.recv(512)
        if not chunk:
            break
        buf += chunk
    head, _, rest = buf.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    method, path = lines[0].split(b" ")[0:2]
    clen = 0
    for ln in lines[1:]:
        if ln.lower().startswith(b"content-length:"):
            clen = int(ln.split(b":")[1])
    body = rest
    while len(body) < clen:
        body += conn.recv(512)
    return method.decode(), path.decode(), body


def send(conn, code, ctype, body):
    if isinstance(body, str):
        body = body.encode()
    conn.send("HTTP/1.0 {} OK\r\nContent-Type: {}\r\nContent-Length: {}\r\n"
              "Connection: close\r\n\r\n".format(code, ctype, len(body)))
    conn.send(body)


def send_json(conn, obj, code=200):
    send(conn, code, "application/json", json.dumps(obj))


def send_file(conn, path, ctype):
    import os
    size = os.stat(path)[6]
    conn.send("HTTP/1.0 200 OK\r\nContent-Type: {}\r\nContent-Length: {}\r\n"
              "Connection: close\r\n\r\n".format(ctype, size))
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            conn.send(chunk)


# ---- endpoints ----

def do_chat(cfg, corpus, prompt, body):
    msg = json.loads(body)["msg"][:2000]
    reply = venice.complete(cfg, [
        {"role": "system", "content": prompt},
        {"role": "user", "content": msg},
    ])
    text, mood, sing = avatar.parse_tags(reply)
    state["mood"] = mood
    buz.mood(mood)
    if sing:
        buz.sing(mood)
    return {"reply": text, "mood": mood, "sang": sing}


def do_interview(cfg, corpus, prompt):
    recent = avatar.recent_questions(corpus)
    ask = ("You feel a gap in your memory. Ask the human exactly ONE short, "
           "specific, warm question about your own life -- past, present, "
           "feelings, or daily texture. Nothing you already know from your "
           "memories, and not similar to these already-asked questions: {}. "
           "Output only the question, then the [mood: X] line."
           ).format("; ".join(recent) if recent else "(none yet)")
    reply = venice.complete(cfg, [
        {"role": "system", "content": prompt},
        {"role": "user", "content": ask},
    ], max_tokens=120)
    text, mood, _ = avatar.parse_tags(reply)
    state["mood"] = mood
    buz.mood(mood, question=True)
    return {"question": text, "mood": mood}


def serve(cfg, corpus):
    import socket
    prompt = avatar.build_prompt(corpus)
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 80))
    s.listen(2)
    print("serving on :80")
    while True:
        conn, _ = s.accept()
        try:
            method, path, body = read_request(conn)
            if method == "GET" and path == "/":
                send_file(conn, "index.html", "text/html")
            elif method == "GET" and path == "/status":
                send_json(conn, {
                    "handle": corpus["identity"].get("preferred_name", "avatar"),
                    "mood": state["mood"],
                    "memories": len(corpus.get("memories", [])),
                    "uptime_s": int(time.time() - state["boot"]),
                })
            elif method == "GET" and path == "/corpus":
                send_file(conn, avatar.CORPUS_PATH, "application/json")
            elif method == "POST" and path == "/chat":
                send_json(conn, do_chat(cfg, corpus, prompt, body))
            elif method == "POST" and path == "/interview":
                send_json(conn, do_interview(cfg, corpus, prompt))
            elif method == "POST" and path == "/answer":
                d = json.loads(body)
                n = avatar.add_memory(corpus, d["question"][:300], d["answer"][:2000])
                prompt = avatar.build_prompt(corpus)  # new memory joins the mind
                buz.mood("cheerful")
                send_json(conn, {"count": n, "ack": random.choice(ACKS)})
            elif method == "POST" and path == "/song":
                name = buz.sing(state["mood"])
                send_json(conn, {"song": name, "mood": state["mood"]})
            else:
                send(conn, 404, "text/plain", "not here")
        except Exception as e:
            print("req error:", repr(e))
            try:
                send_json(conn, {"error": str(e)}, code=500)
            except Exception:
                pass
        finally:
            conn.close()


def run():
    cfg = load_cfg()
    corpus = avatar.load()
    wifi_up(cfg)
    buz.play(BOOT_CHIRP)
    serve(cfg, corpus)


run()
