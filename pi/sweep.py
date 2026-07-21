#!/usr/bin/env python3
"""Sweep-bot: the avatar's purchasing clerk, as an Advisory Signal emitter.

This is the runtime half of clause Section 5(g)
(clause/amendment-advisory-signals.md). The avatar NEVER executes a
trade -- that would be an exercise of legal power the clause voids, and
a financial action no autonomous agent should take. Instead it:

  1. reads its own balances (Venice Diem is real; endowment sleeves are
     read-only on-chain balances),
  2. evaluates STANDING INSTRUCTIONS against executor-set BANDS,
  3. when a band is breached, composes a proposed conversion, SIGNS it
     with the persona's Registered Signing Key (an Advisory Signal),
  4. files it in a veto queue with an N-day timer.

The Digital Executor may `veto` any signal. Unvetoed signals `ripen`
after the window -- and even then, `execute` is a STUB that prints the
authorized action and refuses to broadcast: a human executor moves the
funds. Sensor, not principal.

Signing shells out to foundry `cast wallet sign` (EIP-191). Balances
read via JSON-RPC (Base) and the Venice API. Stdlib only otherwise.

  sweep.py run                    evaluate bands, emit signals
  sweep.py queue                  list signals + veto countdowns
  sweep.py veto <id> [--reason R] executor rejects a signal
  sweep.py execute <id> --i-am-the-executor   (stub) mark done, no broadcast
"""

import argparse
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def _ctx():
    c = ssl.create_default_context()
    if not c.cert_store_stats().get("x509_ca"):
        try:
            import certifi
            c = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            pass
    return c

HOME = Path(os.environ.get("TESTATE_HOME", "."))
CFG = HOME / "sweep.json"
QUEUE = HOME / "sweep_queue.jsonl"
CAST = os.path.expanduser("~/.foundry/bin/cast")
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


# ---- balance sources ------------------------------------------------------

def diem_balance(venice_key):
    req = urllib.request.Request(
        "https://api.venice.ai/api/v1/api_keys/rate_limits",
        headers={"Authorization": "Bearer " + venice_key})
    with urllib.request.urlopen(req, timeout=20, context=_ctx()) as r:
        d = json.load(r)["data"]
    return d["balances"]["DIEM"], d["nextEpochBegins"]


def rpc(url, to, data):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                       "params": [{"to": to, "data": data}, "latest"]}).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20, context=_ctx()) as r:
        return json.load(r).get("result", "0x0")


def erc20_balance(url, token, holder, decimals=6):
    # balanceOf(address) selector 0x70a08231
    data = "0x70a08231" + "0" * 24 + holder.lower().replace("0x", "")
    raw = int(rpc(url, token, data), 16)
    return raw / (10 ** decimals)


# ---- signing (EIP-191 via cast) -------------------------------------------

def sign(message, key_path):
    key = Path(key_path).read_text().strip()
    out = subprocess.run(
        [CAST, "wallet", "sign", "--private-key", key, message],
        capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise SystemExit("sign failed: " + out.stderr[:200])
    return out.stdout.strip()


# ---- queue ----------------------------------------------------------------

def load_queue():
    if not QUEUE.exists():
        return []
    return [json.loads(l) for l in QUEUE.read_text().splitlines() if l.strip()]


def save_queue(sigs):
    QUEUE.write_text("".join(json.dumps(s) + "\n" for s in sigs))


def append_signal(sig):
    with open(QUEUE, "a") as f:
        f.write(json.dumps(sig) + "\n")


# ---- policy ---------------------------------------------------------------

def evaluate(cfg):
    """Return a list of proposed conversions (pre-signature) from bands."""
    proposals = []
    vk = cfg["venice_key"]
    diem, epoch = diem_balance(vk)
    bands = cfg["bands"]

    # Band 1: Diem runway. Diem doesn't roll over, so "runway" is really
    # "is today's allocation large enough". If the daily allocation has
    # fallen below the floor, propose restaking to lift it.
    daily_need = bands["diem_daily_floor"]
    if diem < daily_need:
        deficit = round(daily_need - diem, 4)
        usd = round(deficit * bands["usd_per_diem"], 2)
        usd = min(usd, bands["max_convert_usd"])
        proposals.append({
            "domain": "timing",
            "action": "convert",
            "frm": "stable-yield (USDC sleeve)",
            "to": "restaked VVV",
            "amount_usd": usd,
            "reason": "daily Diem {:.3f} below floor {:.3f}; restake to lift "
                      "allocation".format(diem, daily_need),
        })

    # Band 2: $WAKE hosting reserve (read the USDC sleeve as a stand-in
    # until $WAKE is deployed).
    rpc_url = cfg.get("base_rpc", "https://mainnet.base.org")
    sleeve = cfg.get("usdc_sleeve_address")
    if sleeve:
        try:
            usdc = erc20_balance(rpc_url, USDC_BASE, sleeve)
        except Exception as e:
            print("  (reserve band skipped: RPC unavailable -- {})".format(
                str(e)[:60]))
            usdc = 0
        if usdc >= bands["min_reserve_topup_usd"]:
            top = min(round(usdc * bands["reserve_topup_frac"], 2),
                      bands["max_convert_usd"])
            proposals.append({
                "domain": "timing",
                "action": "convert",
                "frm": "USDC sleeve ({:.2f} available)".format(usdc),
                "to": "$WAKE hosting reserve",
                "amount_usd": top,
                "reason": "quarterly reserve top-up within band",
            })
    return proposals, {"diem": round(diem, 4), "epoch": epoch}


# ---- commands -------------------------------------------------------------

def cmd_run(cfg):
    proposals, snap = evaluate(cfg)
    if not proposals:
        print("bands satisfied; no signal. (Diem {})".format(snap["diem"]))
        return
    existing = load_queue()
    open_keys = {(s["action"], s["to"]) for s in existing
                 if s["status"] in ("pending", "ripe")}
    now = int(time.time())
    veto_s = cfg["veto_days"] * 86400
    for p in proposals:
        if (p["action"], p["to"]) in open_keys:
            print("skip (already queued):", p["to"])
            continue
        sid = "SIG-{}".format(now if not existing else now + len(existing))
        signable = json.dumps({
            "id": sid, "domain": p["domain"], "action": p["action"],
            "from": p["frm"], "to": p["to"], "amount_usd": p["amount_usd"],
            "reason": p["reason"], "snapshot": snap, "sent": now,
        }, sort_keys=True)
        signature = sign(signable, cfg["registered_key_path"])
        sig = {
            "id": sid, "status": "pending", "created": now,
            "ripe_at": now + veto_s, "signer": cfg["registered_key_address"],
            "proposal": p, "snapshot": snap,
            "signable": signable, "signature": signature,
        }
        append_signal(sig)
        print("SIGNAL {}: convert ${} {} -> {}\n  {}\n  signed {} ...{}"
              .format(sid, p["amount_usd"], p["frm"], p["to"], p["reason"],
                      signature[:20], signature[-8:]))
        print("  ripe in {} days unless the Digital Executor vetoes."
              .format(cfg["veto_days"]))


def cmd_queue(cfg):
    sigs = load_queue()
    if not sigs:
        print("queue empty")
        return
    now = int(time.time())
    for s in sigs:
        st = s["status"]
        if st == "pending" and now >= s["ripe_at"]:
            st = "RIPE (veto window closed)"
        elif st == "pending":
            left = (s["ripe_at"] - now) / 86400
            st = "pending ({:.1f}d to ripen)".format(left)
        p = s["proposal"]
        print("{}  [{}]  ${} {} -> {}".format(
            s["id"], st, p["amount_usd"], p["frm"], p["to"]))


def cmd_veto(cfg, sid, reason):
    sigs = load_queue()
    for s in sigs:
        if s["id"] == sid:
            if s["status"] != "pending":
                sys.exit("cannot veto a {} signal".format(s["status"]))
            s["status"] = "vetoed"
            s["veto_reason"] = reason or "(no reason; none required)"
            s["vetoed_at"] = int(time.time())
            save_queue(sigs)
            print("vetoed {} -- the executor's override is absolute.".format(sid))
            return
    sys.exit("no such signal: " + sid)


def cmd_execute(cfg, sid, confirmed):
    if not confirmed:
        sys.exit("refusing: execution is a human executor act. Pass "
                 "--i-am-the-executor to record it (still no broadcast).")
    sigs = load_queue()
    now = int(time.time())
    for s in sigs:
        if s["id"] == sid:
            if s["status"] == "vetoed":
                sys.exit("this signal was vetoed.")
            if now < s["ripe_at"]:
                sys.exit("veto window still open; not ripe.")
            p = s["proposal"]
            print("=== EXECUTOR ACTION (not broadcast by this tool) ===")
            print("Authorized conversion: ${} {} -> {}".format(
                p["amount_usd"], p["frm"], p["to"]))
            print("Advisory Signal {} signed by {}".format(
                sid, s["signer"]))
            print("Move the funds via the trust's own signing flow, then "
                  "this record stands as the ministerial log (5(g)(4)(C)).")
            s["status"] = "executed"
            s["executed_at"] = now
            save_queue(sigs)
            return
    sys.exit("no such signal: " + sid)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("queue")
    v = sub.add_parser("veto")
    v.add_argument("id")
    v.add_argument("--reason", default="")
    e = sub.add_parser("execute")
    e.add_argument("id")
    e.add_argument("--i-am-the-executor", action="store_true", dest="confirmed")
    a = ap.parse_args()

    cfg = json.loads(CFG.read_text())
    if a.cmd == "run":
        cmd_run(cfg)
    elif a.cmd == "queue":
        cmd_queue(cfg)
    elif a.cmd == "veto":
        cmd_veto(cfg, a.id, a.reason)
    elif a.cmd == "execute":
        cmd_execute(cfg, a.id, a.confirmed)


if __name__ == "__main__":
    main()
