#!/usr/bin/env python3
"""Carve the Constellation's Diem into per-member inference keys.

The pool is one Venice account (one staked VVV position, one admin key).
Each member avatar gets its own INFERENCE key with a consumption limit --
its share of the pool's daily Diem. Requires VENICE_ADMIN_KEY in the
environment (the steward's, never a member's).

  pool/keys.py issue --moon "~fotsut-tintyn-ridlur-figbud" --daily-diem 0.5
  pool/keys.py list
  pool/keys.py balance

The consumptionLimit field mirrors Venice's dashboard per-key limits; if
the API rejects it (schema drift), the key is still created unlimited and
a warning is printed -- set the limit in the dashboard until updated.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.venice.ai/api/v1"


def call(method, path, body=None):
    key = os.environ.get("VENICE_ADMIN_KEY")
    if not key:
        sys.exit("VENICE_ADMIN_KEY not set (steward only)")
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode() if body else None,
        method=method,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def issue(moon, daily_diem):
    desc = f"Constellation berth {moon}"
    body = {"apiKeyType": "INFERENCE", "description": desc}
    if daily_diem:
        body["consumptionLimit"] = {"diem": daily_diem}
    try:
        data = call("POST", "/api_keys", body).get("data", {})
    except urllib.error.HTTPError as e:
        if daily_diem:
            print(f"warning: limited-key creation refused (HTTP {e.code}); "
                  "retrying unlimited -- set the limit in the dashboard")
            body.pop("consumptionLimit")
            data = call("POST", "/api_keys", body).get("data", {})
        else:
            raise
    print(json.dumps({
        "moon": moon,
        "api_key": data.get("apiKey") or data.get("key"),
        "key_id": data.get("id"),
        "daily_diem": daily_diem,
    }, indent=2))
    print("\nHand the api_key to the member's node config.json. "
          "It is shown once; store it like a bearer asset.", file=sys.stderr)


def list_keys():
    for k in call("GET", "/api_keys").get("data", []):
        print(f"{k.get('id')}  {k.get('description', '')[:50]:50}  "
              f"last6={k.get('last6Chars', '?')}")


def balance():
    d = call("GET", "/api_keys/rate_limits")["data"]
    print(f"pool Diem remaining today: {d['balances']['DIEM']:.3f}")
    print(f"next epoch: {d['nextEpochBegins']}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("issue")
    i.add_argument("--moon", required=True)
    i.add_argument("--daily-diem", type=float, default=None)
    sub.add_parser("list")
    sub.add_parser("balance")
    a = p.parse_args()
    if a.cmd == "issue":
        issue(a.moon, a.daily_diem)
    elif a.cmd == "list":
        list_keys()
    else:
        balance()


if __name__ == "__main__":
    main()
