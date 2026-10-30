"""Step 5: turn audiences into ready-to-send campaigns. Every draft passes compliance.check."""
import json
import pandas as pd
from compliance import check, FOOTER, SHORT_FOOTER, SHORT_OK_CHANNELS

SCALE = 130


def load_templates(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def draft(templates, offer, channel, reason=""):
    """Build one message for an offer on a channel. Returns dict with copy and compliance result."""
    t = templates[offer]
    reason_text = templates["_reason_text"].get(reason, templates["_reason_text"][""])
    if channel == "Outbound Call":
        body = t.get("call_script", t["body"]).format(reason_text=reason_text)
        msg = {"headline": t["headline"], "body": body, "cta": t["cta"]}
        msg["problems"] = []  # scripts are read by agents, not sent; footer read out on request
        return msg
    footer = SHORT_FOOTER if channel in SHORT_OK_CHANNELS else FOOTER
    if channel == "SMS":
        body = f"Formosa: {t['body']} {t['cta']}.\n\n{footer}"
    else:
        body = f"{t['body']}\n\n{footer}"
    msg = {"headline": t["headline"], "body": body, "cta": t["cta"]}
    objective = ("retention" if offer in ("Data boost", "Renewal discount", "Device credit")
                 else {"Plan upgrade": "upsell", "Data add-on": "upsell", "Roaming pass": "roaming",
                       "Welcome gift": "acquire", "In-store new-line gift": "acquire",
                       "Comeback offer": "winback"}.get(offer))
    msg["problems"] = check(msg["headline"], msg["body"], msg["cta"], channel, objective,
                            offer if objective else None)
    return msg


def main_reason(reasons):
    if not isinstance(reasons, str) or not reasons:
        return ""
    for r in ["contract", "price", "device", "billing", "network", "data_need"]:
        if r in reasons.split(";"):
            return r
    return ""


def build_campaigns(members, templates):
    """One campaign per (audience, offer). Picks the first channel of the plan for the draft."""
    rows = []
    m = members.copy()
    m["main_reason"] = m["reasons"].map(main_reason)
    for (aud, offer), g in m.groupby(["audience", "offer"]):
        plan = g["channel_plan"].iloc[0]
        channel = plan.split(" ")[0] if not plan.startswith("Outbound") else "Outbound Call"
        if channel == "App":
            channel = "App Push"
        reason = g["main_reason"].mode().iloc[0] if len(g) else ""
        msg = draft(templates, offer, channel, reason)
        rows.append({
            "campaign": f"{aud} | {offer}", "audience": aud, "who": g["tier_reason"].iloc[0],
            "offer": offer, "channel": channel, "channel_plan": plan,
            "customers_in_sample": len(g), "customers_at_full_scale": len(g) * SCALE,
            "timing": "within 7 days of the note; refresh weekly" if aud.startswith("retention_R1") or aud.startswith("retention_R2")
            else "monthly batch",
            "headline": msg["headline"], "body": msg["body"], "cta": msg["cta"],
            "compliant": not msg["problems"], "problems": "; ".join(msg["problems"]),
        })
    return pd.DataFrame(rows).sort_values("customers_in_sample", ascending=False)
