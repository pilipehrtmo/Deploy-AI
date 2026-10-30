"""Brand and legal checks, used on past campaigns (audit) and on every new draft."""
import re

FOOTER = ("Plan details are governed by the formal contract and the latest published notice. "
          "Actual rates, offers, and terms of use are subject to the official website or in-store notice "
          "and may change without prior notification. For details, call 0800-XXX-XXX or visit a Formosa Telecom store.")
SHORT_FOOTER = "Terms and conditions: formosa-telecom.example/terms"
SHORT_OK_CHANNELS = {"SMS", "LINE"}

# Banned claims and close paraphrases (brand_guidelines.md).
BANNED = {
    "cheapest guarantee": r"guarantee\w*\s+(the\s+)?cheapest|cheapest\s+in\s+taiwan",
    "never drops": r"never\s+drops?|never\s+lose\s+(a\s+)?connection|no\s+dropped\s+calls\s+ever",
    "strongest signal guarantee": r"guarantee\w*\s+(the\s+)?strongest|strongest\s+signal",
    "only one in the industry": r"only\s+one\s+in\s+the\s+industry|industry'?s\s+only",
    "guaranteed win/rebate": r"guarantee\w*\s+(to\s+win|rebate)",
    "fastest network (unqualified)": r"fastest\s+network",
    "never raise prices": r"never\s+(to\s+)?raise\s+(our\s+)?prices|guarantee\w*\s+never",
}

APPROVED_USE = {
    "acquire": {"Welcome gift", "In-store new-line gift"},
    "winback": {"Comeback offer"},
    "upsell": {"Plan upgrade", "Data add-on"},
    "roaming": {"Roaming pass"},
    "retention": {"Data boost", "Renewal discount", "Device credit"},
}


def check(headline, body, cta, channel, objective=None, offer=None):
    """Return a list of problems. Empty list = compliant."""
    problems = []
    text = " ".join(str(x) for x in (headline, body, cta) if isinstance(x, str))
    body = body if isinstance(body, str) else ""
    end = body.strip()
    if end.endswith(FOOTER):
        pass
    elif channel in SHORT_OK_CHANNELS and end.endswith(SHORT_FOOTER):
        pass
    elif "Plan details are governed" in body or "Terms and conditions" in body:
        problems.append("legal footer altered, shortened or not at the end")
    else:
        problems.append("legal footer missing")
    for name, pat in BANNED.items():
        if name == "fastest network (unqualified)":
            if re.search(pat, text, re.I) and not re.search(r"independent|test(ed)?\s+in|\b20\d\d\b", text, re.I):
                problems.append(f"banned claim: {name}")
        elif re.search(pat, text, re.I):
            problems.append(f"banned claim: {name}")
    if text.count("!") >= 2:
        problems.append("tone: stacked exclamation marks")
    if objective and offer and objective in APPROVED_USE and offer not in APPROVED_USE[objective]:
        problems.append(f"offer '{offer}' is not approved for {objective}")
    return problems
