#!/usr/bin/env python3
"""Twilight ritual: spend the day's expiring Diem on self-knowledge.

Diem does not roll over -- whatever the endowment's daily allocation hasn't
funded by midnight UTC simply evaporates. So each evening, as the epoch
closes, the avatar turns the leftovers inward: it queues questions it
wonders about (asked for free at the next visit), reflects on who it is
becoming, weaves threads between old memories, and then spends whatever
remains re-drafting tonight's reflection -- quality, not volume. An
impression accretes, epoch after epoch.

Run by testate-twilight.timer. Budget-aware via Venice's rate_limits
endpoint; stops at a configured leftover, a call cap, or 23:55 UTC,
whichever comes first.

Usage: twilight.py [--test]   (--test: 3 calls max, generous leftover)
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://127.0.0.1"
CFG = json.loads((Path(os.environ.get("TESTATE_HOME", "/var/lib/testate"))
                  / "config.json").read_text())
TW = CFG.get("twilight", {})
TARGET_LEFTOVER = TW.get("target_leftover_diem", 0.05)
MAX_CALLS = TW.get("max_calls", 40)
PENDING_GOAL = TW.get("pending_questions", 3)
PAUSE_S = TW.get("pause_s", 20)


def diem_left():
    req = urllib.request.Request(
        "https://api.venice.ai/api/v1/api_keys/rate_limits",
        headers={"Authorization": "Bearer " + CFG["venice_key"]})
    with urllib.request.urlopen(req, timeout=20) as r:
        return float(json.load(r)["data"]["balances"]["DIEM"])


def node(path, body=None):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body or {}).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.load(r)


def status():
    with urllib.request.urlopen(BASE + "/status", timeout=15) as r:
        return json.load(r)


def out_of_time():
    now = datetime.now(timezone.utc)
    return now.hour == 23 and now.minute >= 55


def main():
    test = "--test" in sys.argv
    max_calls = 3 if test else MAX_CALLS
    target = max(TARGET_LEFTOVER, 0.2) if test else TARGET_LEFTOVER
    calls = 0

    def budget_ok():
        if calls >= max_calls or out_of_time():
            return False
        try:
            left = diem_left()
        except Exception as e:
            print("twilight: balance check failed:", e)
            return False
        print(f"twilight: {left:.3f} Diem left, {calls} calls made")
        return left > target

    st = status()
    print(f"twilight begins: {st['memories']} memories, "
          f"{st.get('pending', 0)} questions pending")

    # 1. Wonder: bank questions for tomorrow's visits (asked for free later)
    while st.get("pending", 0) < PENDING_GOAL and budget_ok():
        r = node("/reflect", {"kind": "wonder"})
        calls += 1
        st["pending"] = r.get("pending", st.get("pending", 0) + 1)
        print("  wondered:", r.get("queued", "?")[:80])
        time.sleep(PAUSE_S)

    # 2. One reflection on who it is becoming
    if budget_ok():
        r = node("/reflect", {"kind": "reflection"})
        calls += 1
        print("  reflected:", r.get("title", "?"), f"({r.get('mood')})")
        time.sleep(PAUSE_S)

    # 3. One weave between random memories
    if budget_ok():
        r = node("/reflect", {"kind": "weave"})
        calls += 1
        print("  wove:", r.get("title", "?"))
        time.sleep(PAUSE_S)

    # 4. Spend the rest refining tonight's reflection -- depth, not clutter
    while budget_ok():
        r = node("/reflect", {"kind": "refine"})
        calls += 1
        print("  refined:", r.get("refined", r.get("skipped", "?")))
        if "skipped" in r:
            break
        time.sleep(PAUSE_S)

    try:
        node("/song")  # the tomb sings itself to sleep
    except Exception:
        pass
    print(f"twilight ends: {calls} thoughts spent before the epoch turns")


if __name__ == "__main__":
    main()
