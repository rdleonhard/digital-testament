"""Converse with the Digital Persona over Venice's OpenAI-compatible API.

Spends the Persona Endowment's daily Diem allocation. Also provides the
heartbeat: Venice counts a staker as "active" (and thus allocates Diem) only
if an API call was made in the trailing 7 days, so a persona nobody visits
must still ping the API to keep its own funding alive.
"""

import json
import os
import urllib.error
import urllib.request

from . import VENICE_API_BASE, ssl_context

DEFAULT_MODEL = "llama-3.3-70b"


def _api_key() -> str:
    key = os.environ.get("VENICE_API_KEY")
    if not key:
        raise SystemExit(
            "VENICE_API_KEY not set. Export the estate's inference key "
            "(see `tomb provision` / estate_keys.json)."
        )
    return key


def complete(messages: list, model: str = DEFAULT_MODEL,
             max_tokens: int = 700, timeout: float = 120.0) -> str:
    body = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        f"{VENICE_API_BASE}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl_context()) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise SystemExit(f"Venice API error {e.code}: {detail}")
    return data["choices"][0]["message"]["content"]


def heartbeat(model: str = DEFAULT_MODEL) -> str:
    """Minimal Diem spend to stay in the active-staker set (7-day window)."""
    return complete(
        [{"role": "user", "content": "ping"}], model=model, max_tokens=1
    )


def repl(system_prompt: str, model: str = DEFAULT_MODEL) -> None:
    messages = [{"role": "system", "content": system_prompt}]
    print("Digital Persona session. Ctrl-D or 'exit' to end.\n")
    # Open with the will-mandated disclosure by letting the persona speak first.
    messages.append({"role": "user", "content": "Hello?"})
    opening = complete(messages, model=model)
    messages.append({"role": "assistant", "content": opening})
    print(opening + "\n")
    while True:
        try:
            user = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user or user.lower() in {"exit", "quit"}:
            break
        messages.append({"role": "user", "content": user})
        reply = complete(messages, model=model)
        messages.append({"role": "assistant", "content": reply})
        print("\n" + reply + "\n")
