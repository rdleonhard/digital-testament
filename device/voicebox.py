"""TESTATE voice box: the avatar's body after its mind moved out.

Deployed AS main.py on the ESP32-S3 once the corpus migrates to a bigger
node (see pi/). The S3 keeps the soldered buzzer and becomes a network
peripheral: the Pi posts moods over the LAN, the S3 plays them at
http://testate-voice.local.

Endpoints:
  GET  /status                          role, played count, uptime
  POST /mood  {"mood": m, "question": bool}
  POST /sing  {"mood": m}
  POST /play  {"notes": [[freq_hz, ms], ...]}   (freeform, capped)
"""

import json
import time

import network

from tunes import BOOT_CHIRP, Buzzer

state = {"played": 0, "boot": time.time()}
buz = Buzzer()

MAX_NOTES = 64
MAX_MS = 2000
MAX_HZ = 5000


def load_cfg():
    with open("config.json") as f:
        return json.load(f)


def wifi_up(cfg):
    network.hostname(cfg.get("hostname", "testate-voice"))
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
    print("voicebox:", wlan.ifconfig()[0],
          "-> http://%s.local" % cfg.get("hostname", "testate-voice"))


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


def send_json(conn, obj, code=200):
    body = json.dumps(obj)
    conn.send("HTTP/1.0 {} OK\r\nContent-Type: application/json\r\n"
              "Content-Length: {}\r\nConnection: close\r\n\r\n"
              .format(code, len(body)))
    conn.send(body)


def serve():
    import socket
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 80))
    s.listen(2)
    print("voicebox serving on :80")
    while True:
        conn, _ = s.accept()
        try:
            method, path, body = read_request(conn)
            if method == "GET" and path == "/status":
                send_json(conn, {"role": "voicebox", "played": state["played"],
                                 "uptime_s": int(time.time() - state["boot"])})
            elif method == "POST" and path == "/mood":
                d = json.loads(body) if body else {}
                buz.mood(d.get("mood", "curious"), question=bool(d.get("question")))
                state["played"] += 1
                send_json(conn, {"ok": True})
            elif method == "POST" and path == "/sing":
                d = json.loads(body) if body else {}
                name = buz.sing(d.get("mood", "cheerful"))
                state["played"] += 1
                send_json(conn, {"ok": True, "song": name})
            elif method == "POST" and path == "/play":
                notes = json.loads(body).get("notes", [])[:MAX_NOTES]
                clean = [(min(max(int(f), 0), MAX_HZ), min(int(ms), MAX_MS))
                         for f, ms in notes]
                buz.play(clean)
                state["played"] += 1
                send_json(conn, {"ok": True, "notes": len(clean)})
            else:
                send_json(conn, {"error": "not here"}, 404)
        except Exception as e:
            print("req error:", repr(e))
            try:
                send_json(conn, {"error": str(e)}, 500)
            except Exception:
                pass
        finally:
            conn.close()


def run():
    cfg = load_cfg()
    wifi_up(cfg)
    buz.play(BOOT_CHIRP)
    serve()


run()
