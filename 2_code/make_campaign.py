"""Type a short brief, get a ready, compliant campaign back. Works offline.

Examples:
    python make_campaign.py "renewal discount by SMS for customers who mention a rival"
    python make_campaign.py "data boost on LINE for wavering customers"
    python make_campaign.py "roaming pass app push"
    python make_campaign.py --use-llm "..."   # real use: Claude reads the brief (needs ANTHROPIC_API_KEY)

Run `python run.py` first: this tool reads 4_outputs/audience_members.csv.
"""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
import campaigns  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # hand-in folder: 1_report, 2_code, 3_ai_outputs, 4_outputs, 5_finals
OFFERS = ["Renewal discount", "Data boost", "Device credit", "Plan upgrade", "Data add-on", "Roaming pass"]
CHANNELS = {"sms": "SMS", "line": "LINE", "email": "Email", "push": "App Push", "app": "App Push",
            "call": "Outbound Call", "phone": "Outbound Call"}
REASONS = {"rival": "price", "competitor": "price", "price": "price", "expensive": "price",
           "renew": "contract", "contract": "contract", "cancel": "contract",
           "bill": "billing", "signal": "network", "coverage": "network", "network": "network",
           "phone": "device", "device": "device", "data": "data_need"}
TIERS = {"leaving": "R1_leaving_now", "wavering": "R2_wavering", "new": "R3_new_and_fragile",
         "unhappy": "R4_unhappy_quiet"}


def parse(brief):
    b = brief.lower()
    offer = next((o for o in OFFERS if o.lower() in b), None)
    channel = next((v for k, v in CHANNELS.items() if re.search(rf"\b{k}\b", b)), "SMS")
    words = b.replace(offer.lower(), "") if offer else b
    reason = next((v for k, v in REASONS.items() if re.search(rf"\b{k}", words)), "")
    tier = next((v for k, v in TIERS.items() if re.search(rf"\b{k}\b", words)), None)
    return offer, channel, reason, tier


EXAMPLE = "renewal discount by SMS for customers who mention a rival"


def make(brief, quiet=False, use_llm=False):
    """Brief -> audience + message + compliance. Saves 4_outputs/brief_campaign.md and brief_audience.csv."""
    if use_llm:
        import llm
        if not llm.available():
            print("--use-llm given but ANTHROPIC_API_KEY is not set: reading the brief with keyword rules")
            use_llm = False
    offer, channel, reason, tier = llm.parse_brief(brief) if use_llm else parse(brief)
    if offer not in OFFERS:
        print("Name an approved offer in the brief: " + ", ".join(OFFERS))
        return None
    tpl = campaigns.load_templates(os.path.join(ROOT, "3_ai_outputs", "copy_templates.json"))
    msg = campaigns.draft(tpl, offer, channel, reason)

    path = os.path.join(ROOT, "4_outputs", "audience_members.csv")
    if not os.path.exists(path):
        print("Run `python run.py` first to build the audiences.")
        return None
    m = pd.read_csv(path)
    aud = m[m["offer"] == offer]
    if tier:
        aud = aud[aud["tier"] == tier]
    if reason:
        aud = aud[aud["reasons"].fillna("").str.contains(reason)]
    reach_share = campaigns_share(channel)
    lines = [f"BRIEF    {brief}",
             f"READ AS  offer={offer} | channel={channel} | reason={reason or 'any'} | tier={tier or 'any'}",
             f"AUDIENCE {len(aud)} in sample = about {len(aud) * 130:,} customers at full scale; "
             f"about {int(len(aud) * 130 * reach_share):,} reachable on {channel} ({reach_share:.0%} consent)"]
    if len(aud) == 0:
        lines.append("         No customers match all of that. Try the brief without the tier or reason words.")
    lines += ["-" * 70, f"HEADLINE {msg['headline']}\n\n{msg['body']}\n\nCTA      {msg['cta']}", "-" * 70,
              "COMPLIANCE " + ("PASS" if not msg["problems"] else "FAIL: " + "; ".join(msg["problems"]))]
    text = "\n".join(lines)
    out = os.path.join(ROOT, "4_outputs")
    aud.to_csv(os.path.join(out, "brief_audience.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(out, "brief_campaign.md"), "w", encoding="utf-8") as f:
        f.write("# Campaign made from a brief by make_campaign.py\n\n```\n" + text + "\n```\n\n"
                "Customer list: `brief_audience.csv`.\n")
    if not quiet:
        print(text)
        print("Saved to 4_outputs/brief_campaign.md and 4_outputs/brief_audience.csv")
    return text


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = [x for x in sys.argv[1:] if x != "--use-llm"]
    if not args:
        print(__doc__)
        return
    make(" ".join(args), use_llm="--use-llm" in sys.argv)


def campaigns_share(channel):
    return {"SMS": 0.74, "LINE": 0.41, "Email": 0.33, "App Push": 0.27, "Outbound Call": 0.92}[channel]


if __name__ == "__main__":
    main()
