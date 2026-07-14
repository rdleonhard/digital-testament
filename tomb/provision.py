"""Provision the estate's inference credential (will Article, Section 4(d)).

If a Venice ADMIN key is present (VENICE_ADMIN_KEY), creates a real INFERENCE
API key registered to the trust via Venice's /api_keys endpoint and records it.
Otherwise writes a pending key record with instructions, so the Digital
Executor's checklist still moves forward.

Key records land in estate_keys.json next to the corpus -- treat that file
like a bearer asset (see drafting notes: never in the probate inventory).
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import VENICE_API_BASE, ssl_context

KEY_STORE = "estate_keys.json"


def _load_store(path: Path) -> list:
    if path.exists():
        return json.loads(path.read_text())
    return []


def _save_store(path: Path, records: list) -> None:
    path.write_text(json.dumps(records, indent=2) + "\n")
    os.chmod(path, 0o600)


def create_venice_key(admin_key: str, description: str, timeout: float = 15.0) -> dict:
    """Create an INFERENCE key via the Venice API using an admin key."""
    body = json.dumps(
        {"apiKeyType": "INFERENCE", "description": description}
    ).encode()
    req = urllib.request.Request(
        f"{VENICE_API_BASE}/api_keys",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {admin_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout,
                                context=ssl_context()) as resp:
        return json.load(resp)


def provision(owner: str, store_dir: str = ".") -> dict:
    """Provision (or record the need for) the estate's inference key."""
    store_path = Path(store_dir) / KEY_STORE
    records = _load_store(store_path)
    description = f"Digital Persona Legacy - {owner}"
    record = {
        "owner": owner,
        "description": description,
        "created": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "api_key": None,
        "note": None,
    }

    admin_key = os.environ.get("VENICE_ADMIN_KEY")
    if admin_key:
        try:
            result = create_venice_key(admin_key, description)
            data = result.get("data", result)
            record["status"] = "issued"
            record["api_key"] = data.get("apiKey") or data.get("key")
            record["venice_key_id"] = data.get("id")
        except urllib.error.HTTPError as e:
            record["note"] = (
                f"Venice API refused key creation (HTTP {e.code}). "
                "Verify the admin key and create the key in the Venice "
                "dashboard if needed."
            )
        except OSError as e:
            record["note"] = f"Network error reaching Venice: {e}"
    else:
        record["note"] = (
            "No VENICE_ADMIN_KEY in environment. Digital Executor: stake the "
            "endowment VVV, then create an INFERENCE key at "
            "https://venice.ai (API settings) or re-run with the admin key "
            "exported. Store the key per the wallet succession protocol."
        )

    records.append(record)
    _save_store(store_path, records)
    return record
