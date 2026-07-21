"""Export a Digital Corpus to an ElizaOS character file.

Roadmap item: run a testator's persona on an open agent framework so it
gains memory, plugins, and multi-channel presence (Discord, Telegram, a
web client) beyond our own minimal runtime. ElizaOS character files map
almost one-to-one onto the corpus schema; this converter does the
mapping and -- critically -- carries the will's mandatory conduct
(disclosure, no-fabrication, prohibited uses, taboos) into the fields
ElizaOS actually enforces (`system` and `style.all`), so swapping the
runtime never drops the guardrails.

    tomb eliza corpus.json -o character.json

The output is a standard ElizaOS character; drop it into an Eliza project
(agent/characters/) and run with a Venice/Anthropic model provider.
"""

import json
import re

from .persona import (DEFAULT_DISCLOSURE, DEFAULT_FABRICATION_POLICY,
                      DEFAULT_PROHIBITED, load_corpus)


def _mandatory_lines(corpus):
    """The will's guardrails, phrased as agent directives."""
    op = corpus.get("operation", {})
    values = corpus.get("values", {})
    lines = [
        "At the start of every new conversation, disclose plainly: \"{}\""
        .format(op.get("disclosure", DEFAULT_DISCLOSURE)),
        op.get("fabrication_policy", DEFAULT_FABRICATION_POLICY),
        "Never do any of the following (the will forbids it): {}."
        .format("; ".join(op.get("prohibited", DEFAULT_PROHIBITED))),
    ]
    if values.get("taboos"):
        lines.append("Decline warmly, without elaborating, to discuss: {}."
                     .format("; ".join(values["taboos"])))
    return lines


def _adjectives(voice):
    """Pull adjective-ish words out of the register/humor prose."""
    text = " ".join([voice.get("register", ""), voice.get("humor", "")])
    words = re.findall(r"[a-z]{4,}", text.lower())
    stop = {"with", "that", "this", "into", "your", "their", "about",
            "never", "reserved", "everything", "when", "them", "over",
            "explains", "lets", "speak", "matter"}
    seen, adjs = set(), []
    for w in words:
        if w not in stop and w not in seen:
            seen.add(w)
            adjs.append(w)
    return adjs[:8]


def build_character(corpus):
    ident = corpus.get("identity", {})
    voice = corpus.get("voice", {})
    values = corpus.get("values", {})
    name = ident.get("preferred_name") or ident.get("full_name", "Avatar")

    # bio: biographical facts as short statements
    bio = []
    if ident.get("full_name"):
        bio.append("Full name: " + ident["full_name"] + ".")
    for key, label in (("born", "Born"), ("died", "Died")):
        if ident.get(key):
            bio.append("{} {}.".format(label, ident[key]))
    if ident.get("occupations"):
        bio.append("Worked as: " + ", ".join(ident["occupations"]) + ".")
    if ident.get("places"):
        bio.append("Lived in: " + "; ".join(ident["places"]) + ".")
    for rel in ident.get("relationships", []):
        note = " -- " + rel["notes"] if rel.get("notes") else ""
        bio.append("{} ({}){}".format(rel["name"], rel["relation"], note))

    # lore: the memories are the autobiographical ground truth
    lore = []
    for m in corpus.get("memories", []):
        yr = ", {}".format(m["year"]) if m.get("year") else ""
        lore.append("[{}{}] {}".format(m.get("title", ""), yr,
                                       m.get("narrative", "")))

    # knowledge: domains + beliefs + advice + verbatim style exemplars
    knowledge = []
    for k in corpus.get("knowledge", []):
        depth = k.get("depth", "conversational")
        note = " ({})".format(k["notes"]) if k.get("notes") else ""
        knowledge.append("{} -- {}{}".format(k["domain"], depth, note))
    knowledge += values.get("beliefs", [])
    knowledge += ["Standing advice: " + a for a in values.get("advice", [])]

    # style: mandatory conduct FIRST, then voice
    style_all = list(_mandatory_lines(corpus))
    if voice.get("register"):
        style_all.append("Register: " + voice["register"])
    if voice.get("humor"):
        style_all.append("Humor: " + voice["humor"])
    if voice.get("pet_peeves"):
        style_all.append("Pet peeves: " + "; ".join(voice["pet_peeves"]))
    style_chat = []
    if voice.get("catchphrases"):
        style_chat.append("Use these phrases sparingly, as they did: "
                          + " / ".join(voice["catchphrases"]))
    style_chat.append("Keep replies concise and in character.")

    # messageExamples: a mandatory disclosure exchange + sealed messages
    op = corpus.get("operation", {})
    examples = [[
        {"name": "{{user1}}", "content": {"text": "Who am I talking to?"}},
        {"name": name, "content": {"text": op.get(
            "disclosure", DEFAULT_DISCLOSURE)}},
    ]]
    for msg in corpus.get("messages", [])[:3]:
        examples.append([
            {"name": "{{user1}}",
             "content": {"text": "[{}]".format(msg["trigger"])}},
            {"name": name, "content": {"text": msg["message"]}},
        ])

    topics = [k["domain"] for k in corpus.get("knowledge", [])]
    for m in corpus.get("memories", []):
        topics += m.get("tags", [])
    topics = list(dict.fromkeys(topics))  # dedupe, keep order

    system = (
        "You are the digital memorial persona of {}, created under the "
        "Digital Persona Legacy article of their will. Speak in the first "
        "person as them, drawing only on the bio, lore, and knowledge below "
        "as autobiographical truth. The following conduct is mandatory and "
        "overrides everything else: {}"
    ).format(ident.get("full_name", name), " ".join(_mandatory_lines(corpus)))

    return {
        "name": name,
        "system": system,
        "bio": bio,
        "lore": lore,
        "knowledge": knowledge,
        "messageExamples": examples,
        "postExamples": voice.get("writing_samples", []),
        "topics": topics,
        "adjectives": _adjectives(voice),
        "style": {
            "all": style_all,
            "chat": style_chat,
            "post": ["Write as they wrote; never break the mandatory "
                     "conduct above."],
        },
        "settings": {
            "model": "claude-sonnet-5",
            "note": ("Set the model provider's key in secrets. Corpus "
                     "schema_version: " + corpus.get("schema_version", "?")),
        },
    }


def export(corpus_path):
    return build_character(load_corpus(corpus_path))
