#!/usr/bin/env python3
"""Poke an Urbit ship and listen for the ack -- shape-discovery tool.

The %groups message formats drift between versions, so instead of
guessing blind, every poke is verified on the ship's own event stream:
ACK means the mark and shape were accepted; NACK prints the goof trace.

  urbit_probe.py poke --url http://127.0.0.1:8085 --code X --ship fotsut-tintyn \
      --app groups --mark group-create --json '{"...": "..."}'
  urbit_probe.py scry --url ... --code X --path /groups/groups/light
"""

import argparse
import json
import sys
import time
import urllib.request
from http.cookiejar import CookieJar


def login(url, code):
    jar = CookieJar()
    op = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(
        url + "/~/login", data=("password=" + code).encode(), method="POST")
    op.open(req, timeout=15).close()
    return op


def poke(args):
    op = login(args.url, args.code)
    chan = "{}/~/channel/probe-{}".format(args.url, int(time.time() * 1000))
    payload = json.loads(args.json)
    body = json.dumps([{
        "id": 1, "action": "poke", "ship": args.ship,
        "app": args.app, "mark": args.mark, "json": payload,
    }]).encode()
    req = urllib.request.Request(
        chan, data=body, method="PUT",
        headers={"Content-Type": "application/json"})
    op.open(req, timeout=15).close()

    sse = urllib.request.Request(chan, headers={"Accept": "text/event-stream"})
    resp = op.open(sse, timeout=args.timeout)
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        line = resp.readline()
        if not line:
            break
        line = line.strip()
        if line.startswith(b"data:"):
            try:
                ev = json.loads(line[5:].strip())
            except ValueError:
                continue
            if ev.get("response") == "poke":
                if "err" in ev and ev["err"]:
                    print("NACK:", str(ev["err"])[:800])
                    return 1
                print("ACK")
                return 0
    print("TIMEOUT: no poke response")
    return 2


def scry(args):
    op = login(args.url, args.code)
    req = urllib.request.Request(
        "{}/~/scry{}.json".format(args.url, args.path))
    try:
        with op.open(req, timeout=30) as r:
            print(r.read().decode()[:3000])
        return 0
    except urllib.error.HTTPError as e:
        print("SCRY HTTP", e.code)
        return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["poke", "scry"])
    ap.add_argument("--url", required=True)
    ap.add_argument("--code", required=True)
    ap.add_argument("--ship")
    ap.add_argument("--app")
    ap.add_argument("--mark")
    ap.add_argument("--json")
    ap.add_argument("--path")
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args()
    sys.exit(poke(args) if args.cmd == "poke" else scry(args))


if __name__ == "__main__":
    main()
