"""Type a short brief, get a ready, compliant campaign back. Works offline.

Examples:
    python make_campaign.py "renewal discount by SMS for customers who mention a rival"
    python make_campaign.py "data boost on LINE for wavering customers"
    python make_campaign.py "roaming pass app push"

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


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if len(sys.argv) < 2:
        print(__doc__)
        return
    brief = " ".join(sys.argv[1:])
    offer, channel, reason, tier = parse(brief)
    if not offer:
        print("Name an approved offer in the brief: " + ", ".join(OFFERS))
        return
    tpl = campaigns.load_templates(os.path.join(ROOT, "3_ai_outputs", "copy_templates.json"))
    msg = campaigns.draft(tpl, offer, channel, reason)

    path = os.path.join(ROOT, "4_outputs", "audience_members.csv")
    if not os.path.exists(path):
        print("Run `python run.py` first to build the audiences.")
        return
    m = pd.read_csv(path)
    aud = m[m["offer"] == offer]
    if tier:
        aud = aud[aud["tier"] == tier]
    if reason:
        aud = aud[aud["reasons"].fillna("").str.contains(reason)]
    reach_share = campaigns_share(channel)
    print(f"BRIEF    {brief}")
    print(f"READ AS  offer={offer} | channel={channel} | reason={reason or 'any'} | tier={tier or 'any'}")
    print(f"AUDIENCE {len(aud)} in sample = about {len(aud) * 130:,} customers at full scale; "
          f"about {int(len(aud) * 130 * reach_share):,} reachable on {channel} ({reach_share:.0%} consent)")
    if len(aud) == 0:
        print("         No customers match all of that. Try the brief without the tier or reason words.")
    print("-" * 70)
    print(f"HEADLINE {msg['headline']}\n\n{msg['body']}\n\nCTA      {msg['cta']}")
    print("-" * 70)
    print("COMPLIANCE " + ("PASS" if not msg["problems"] else "FAIL: " + "; ".join(msg["problems"])))
    out = os.path.join(ROOT, "4_outputs", "brief_audience.csv")
    aud.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Audience list saved to 4_outputs/brief_audience.csv")


def campaigns_share(channel):
    return {"SMS": 0.74, "LINE": 0.41, "Email": 0.33, "App Push": 0.27, "Outbound Call": 0.92}[channel]


if __name__ == "__main__":
    main()
