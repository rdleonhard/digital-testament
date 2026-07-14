"""Minimal Venice chat-completions client for MicroPython (uses bundled
`requests`). Spends the node's daily Diem; every call also keeps the stake
in the active-staker set."""

import json

import requests

API_URL = "https://api.venice.ai/api/v1/chat/completions"


def complete(cfg, messages, max_tokens=350):
    r = requests.post(
        API_URL,
        headers={
            "Authorization": "Bearer " + cfg["venice_key"],
            "Content-Type": "application/json",
        },
        # encode: Content-Length must count UTF-8 bytes, not chars
        data=json.dumps({
            "model": cfg.get("model", "llama-3.3-70b"),
            "messages": messages,
            "max_tokens": max_tokens,
        }).encode(),
    )
    try:
        if r.status_code != 200:
            raise OSError("Venice HTTP {}: {}".format(r.status_code, r.text[:200]))
        return r.json()["choices"][0]["message"]["content"]
    finally:
        r.close()
