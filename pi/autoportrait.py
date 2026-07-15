#!/usr/bin/env python3
"""Daily autoportrait: wait for a human, then open the eye.

Run by testate-observe.timer at a random hour. Polls the node's presence
state and triggers one observation the next time someone is actually in
frame -- the avatar keeps a visual diary of its life without ever
photographing an empty room. If the eye is disabled it observes blind
(rpicam-still fallback) rather than skipping the day.
"""

import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1"
WAIT_S = 11 * 3600
POLL_S = 900


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.load(r)


def observe():
    req = urllib.request.Request(BASE + "/observe", data=b"{}",
                                 method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.load(r)


deadline = time.time() + WAIT_S
while time.time() < deadline:
    try:
        st = get("/status")
        if st.get("present") or not st.get("eye"):
            result = observe()
            print("autoportrait kept as memory",
                  result.get("count"), "-", result.get("mood"))
            sys.exit(0)
        print("autoportrait: nobody in frame; waiting")
    except Exception as e:
        print("autoportrait:", e)
    time.sleep(POLL_S)
print("autoportrait: nobody appeared today; the eye stays shut")
