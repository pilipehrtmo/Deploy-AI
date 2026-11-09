"""The live AI step: call Claude through the Anthropic API.

Off by default. The rerun never calls it: notes.py reads the saved labels in
3_ai_outputs/sentence_labels.csv and sends any sentence it has not seen to the
review queue as "unknown".

Switch it on in real use:
    set ANTHROPIC_API_KEY=sk-ant-...        (Mac: export ANTHROPIC_API_KEY=sk-ant-...)
    python run.py --use-llm
Every new sentence is labelled with the prompt in 3_ai_outputs/prompts/label_sentences.md
and appended to sentence_labels.csv, so the next run reads it offline like the rest.
Uses only the Python standard library (no extra install).
"""
import json
import os
import urllib.request

API = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("FORMOSA_MODEL", "claude-opus-5-5")
PROMPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                       "3_ai_outputs", "prompts")
TOPICS_FILE = os.path.join(PROMPTS, "label_sentences.md")


def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def ask(prompt, max_tokens=4000):
    """Send one prompt, return the reply text."""
    body = json.dumps({"model": MODEL, "max_tokens": max_tokens, "temperature": 0,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
        "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return "".join(b.get("text", "") for b in json.load(r)["content"])


def _json(text):
    text = text.strip()
    start = min([i for i in (text.find("["), text.find("{")) if i >= 0], default=0)
    return json.loads(text[start:text.rfind("]" if text[start] == "[" else "}") + 1])


def _template(name):
    with open(os.path.join(PROMPTS, name), encoding="utf-8") as f:
        return f.read().split("---", 1)[1].strip()


def label_sentences(sentences, allowed_topics, batch=50):
    """Label normalised sentences. Returns rows {sentence, topic, leave_intent}; skips any invalid answer."""
    rows = []
    for i in range(0, len(sentences), batch):
        part = sentences[i:i + batch]
        reply = _json(ask(_template("label_sentences.md").replace("{sentences}", json.dumps(part, ensure_ascii=False))))
        for s, r in zip(part, reply):
            topic, lvl = r.get("topic"), r.get("leave_intent")
            if topic in allowed_topics and lvl in (0, 1, 2, 3):   # anything else stays in the review queue
                rows.append({"sentence": s, "topic": topic, "leave_intent": int(lvl)})
    return rows


def parse_brief(brief):
    """Read a marketer's brief into offer, channel, reason, tier."""
    r = _json(ask(_template("parse_brief.md").replace("{brief}", brief), max_tokens=300))
    return r.get("offer"), r.get("channel") or "SMS", r.get("reason") or "", r.get("tier")
