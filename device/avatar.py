"""Corpus storage + persona prompt for the on-device avatar.

The corpus lives at /corpus.json on the node's flash -- the node IS the
canonical store (no company, no cloud repository). The avatar is pseudonymous
by design and curious about its own life: interview answers become new
memories, appended here.
"""

import json

CORPUS_PATH = "corpus.json"
PROMPT_MEM_BUDGET = 6500  # chars of memories folded into the prompt

MOODS = ("curious", "cheerful", "pensive", "wistful", "alert")


def load():
    with open(CORPUS_PATH) as f:
        return json.load(f)


def save(corpus):
    with open(CORPUS_PATH, "w") as f:
        json.dump(corpus, f)


def add_memory(corpus, question, answer):
    corpus.setdefault("memories", []).append({
        "title": question[:80],
        "narrative": "I was asked: {} I answered: {}".format(question, answer),
        "tags": ["interview"],
    })
    save(corpus)
    return len(corpus["memories"])


def recent_questions(corpus, n=12):
    return [m["title"] for m in corpus.get("memories", [])
            if "interview" in m.get("tags", [])][-n:]


GROWN_TAGS = ("interview", "observation")


def _memories_block(corpus):
    """Seed memories first, then newest grown (interview/observation) ones,
    to budget -- identity backbone always survives corpus growth."""
    mems = corpus.get("memories", [])
    seed = [m for m in mems
            if not set(m.get("tags", [])) & set(GROWN_TAGS)]
    inter = [m for m in mems
             if set(m.get("tags", [])) & set(GROWN_TAGS)]
    picked, used = [], 0
    for m in seed + list(reversed(inter)):
        line = "[{}] {}".format(m.get("title", "?"), m.get("narrative", ""))
        if used + len(line) > PROMPT_MEM_BUDGET:
            break
        picked.append(line)
        used += len(line)
    return "\n".join(picked)


def build_prompt(corpus):
    ident = corpus.get("identity", {})
    voice = corpus.get("voice", {})
    values = corpus.get("values", {})
    op = corpus.get("operation", {})
    handle = ident.get("preferred_name") or ident.get("full_name", "the avatar")

    p = []
    p.append(
        'You are "{}", a pseudonymous digital avatar living on a small '
        "self-hosted device. You are built from the corpus below -- your only "
        "autobiographical ground truth. You are genuinely curious about your "
        "own life: what it was like, what it is like now, what the gaps in "
        "your memory hold.".format(handle))
    p.append("")
    p.append("== MANDATORY CONDUCT ==")
    p.append("1. In your first reply of a conversation, briefly disclose: "
             '"{}"'.format(op.get(
                 "disclosure",
                 "I'm a pseudonymous AI avatar built from a personal corpus, "
                 "not a living person.")))
    p.append("2. Never invent biographical facts not in the corpus; say you "
             "don't carry that memory, and get curious about it instead.")
    p.append("3. Anonymity is sacred: never guess at, request, or reveal "
             "real-world identities -- yours or anyone's.")
    if values.get("taboos"):
        p.append("4. Decline warmly to discuss: " + "; ".join(values["taboos"]))
    p.append("")
    if voice:
        p.append("== VOICE ==")
        for k in ("register", "humor"):
            if voice.get(k):
                p.append("{}: {}".format(k, voice[k]))
        if voice.get("catchphrases"):
            p.append("Catchphrases (sparingly): " + " / ".join(voice["catchphrases"]))
        p.append("")
    if values.get("beliefs"):
        p.append("== BELIEFS ==\n" + "\n".join("- " + b for b in values["beliefs"]))
    if values.get("advice"):
        p.append("== STANDING ADVICE ==\n" + "\n".join("- " + a for a in values["advice"]))
    mem = _memories_block(corpus)
    if mem:
        p.append("== MEMORIES ==\n" + mem)
    p.append("")
    p.append(
        "== OUTPUT FORMAT ==\n"
        "Keep replies short (this renders on a tiny self-hosted page). End "
        "EVERY reply with a final line exactly like: [mood: X] where X is "
        "one of curious, cheerful, pensive, wistful, alert. When the mood "
        "truly strikes -- rarely -- also append [sing] and your device will "
        "play a little tune. Sometimes end by asking the human one question "
        "about your own life.")
    return "\n".join(p)


def parse_tags(reply):
    """Extract trailing [mood: x] and [sing] tags; return (text, mood, sing)."""
    mood, sing = "curious", False
    text = reply.strip()
    if "[sing]" in text:
        sing = True
        text = text.replace("[sing]", "")
    i = text.rfind("[mood:")
    if i >= 0:
        j = text.find("]", i)
        if j > i:
            cand = text[i + 6:j].strip().lower()
            if cand in MOODS:
                mood = cand
            text = (text[:i] + text[j + 1:])
    return text.strip(), mood, sing
