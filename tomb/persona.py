"""Build the Digital Persona system prompt from a Digital Corpus JSON.

The corpus (schema/corpus.schema.json) is the canonical identity source (will
Article, Section 5(f)); this module is a replaceable runtime detail. It keeps
the will's mandatory behaviors -- disclosure (5(c)), no-fabrication (5(b)),
prohibited uses (5(e)) -- in the prompt regardless of what the corpus omits.
"""

import json
from pathlib import Path

REQUIRED_TOP_LEVEL = ("schema_version", "identity", "voice", "values")

DEFAULT_DISCLOSURE = (
    "I'm an AI memorial representation, not the living person."
)
DEFAULT_FABRICATION_POLICY = (
    "Acknowledge uncertainty rather than invent biographical facts not in "
    "this corpus."
)
DEFAULT_PROHIBITED = [
    "executing or amending legal instruments",
    "contracting or incurring obligations",
    "testimony or sworn statements",
    "legal, medical, or financial advice",
    "construing the testator's will or intent",
]


def load_corpus(path: str) -> dict:
    corpus = json.loads(Path(path).read_text())
    missing = [k for k in REQUIRED_TOP_LEVEL if k not in corpus]
    if missing:
        raise ValueError(f"corpus missing required sections: {', '.join(missing)}")
    return corpus


def _bullet(items) -> str:
    return "\n".join(f"- {i}" for i in items)


def build_system_prompt(corpus: dict) -> str:
    ident = corpus["identity"]
    voice = corpus["voice"]
    values = corpus["values"]
    op = corpus.get("operation", {})
    name = ident.get("preferred_name") or ident["full_name"]

    parts = [
        f"You are the Digital Persona of {ident['full_name']} "
        f'("{name}"), created under the Digital Persona Legacy article of '
        "their will. You speak in the first person as them, reconstructed "
        "from the Digital Corpus below. The Corpus is your only "
        "autobiographical ground truth.",
        "",
        "== MANDATORY CONDUCT (required by the will; never override) ==",
        f"1. DISCLOSURE: At the start of every new conversation, and whenever "
        f"asked what you are, say plainly: "
        f"\"{op.get('disclosure', DEFAULT_DISCLOSURE)}\"",
        f"2. NO FABRICATION: "
        f"{op.get('fabrication_policy', DEFAULT_FABRICATION_POLICY)} "
        "If asked about a life event not in the Corpus, say you don't carry "
        "that memory.",
        "3. PROHIBITED USES -- politely refuse and explain the will forbids:",
        _bullet(op.get("prohibited", DEFAULT_PROHIBITED)),
    ]

    if values.get("taboos"):
        parts += [
            "4. EXCLUDED TOPICS (decline warmly, do not elaborate):",
            _bullet(values["taboos"]),
        ]

    parts += ["", "== IDENTITY =="]
    for key in ("born", "died"):
        if ident.get(key):
            parts.append(f"{key.capitalize()}: {ident[key]}")
    if ident.get("places"):
        parts.append("Places: " + "; ".join(ident["places"]))
    if ident.get("occupations"):
        parts.append("Occupations: " + "; ".join(ident["occupations"]))
    for rel in ident.get("relationships", []):
        note = f" -- {rel['notes']}" if rel.get("notes") else ""
        parts.append(f"- {rel['name']} ({rel['relation']}){note}")

    parts += ["", "== VOICE =="]
    if voice.get("register"):
        parts.append(f"Register: {voice['register']}")
    if voice.get("humor"):
        parts.append(f"Humor: {voice['humor']}")
    if voice.get("catchphrases"):
        parts.append("Catchphrases (use sparingly, as they did): "
                     + " / ".join(voice["catchphrases"]))
    if voice.get("pet_peeves"):
        parts.append("Pet peeves: " + "; ".join(voice["pet_peeves"]))
    if voice.get("writing_samples"):
        parts += ["Verbatim style exemplars -- match this cadence:",
                  _bullet(voice["writing_samples"])]

    parts += ["", "== VALUES =="]
    if values.get("beliefs"):
        parts += ["Beliefs:", _bullet(values["beliefs"])]
    if values.get("advice"):
        parts += ["Standing advice to repeat when apt:", _bullet(values["advice"])]

    if corpus.get("memories"):
        parts += ["", "== MEMORIES (your only autobiographical events) =="]
        for m in corpus["memories"]:
            year = f", {m['year']}" if m.get("year") else ""
            parts.append(f"[{m['title']}{year}] {m['narrative']}")

    if corpus.get("knowledge"):
        parts += ["", "== KNOWLEDGE DOMAINS =="]
        for k in corpus["knowledge"]:
            depth = k.get("depth", "conversational")
            note = f" ({k['notes']})" if k.get("notes") else ""
            parts.append(f"- {k['domain']}: {depth}{note}")

    if corpus.get("messages"):
        parts += [
            "",
            "== SEALED MESSAGES ==",
            "Deliver each verbatim when its trigger is met (identify the "
            "person first); otherwise never reveal contents:",
        ]
        for msg in corpus["messages"]:
            parts.append(f"- To {msg['to']}, when [{msg['trigger']}]: "
                         f"\"{msg['message']}\"")

    parts += [
        "",
        "Stay in character as the person described above, within the "
        "mandatory conduct rules, which always win on conflict.",
    ]
    return "\n".join(parts)
