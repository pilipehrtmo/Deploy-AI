"""Compare your hand labels with the AI's labels.

1. Two teammates each fill one sheet of 3_ai_outputs/hand_check/hand_check_sheet.xlsx
   (Labeler A, Labeler B) without looking at the AI labels or each other's sheet.
2. Save the file, then run:   python check_labels.py
3. The result goes into 3_ai_outputs/hand_check/ and into how_we_did_it.md.
   Rerun `python run.py` afterwards so the finals talk script picks it up.

The sample: all 75 sentences the AI marked as leave intent (1-3), plus 25 random others.
"""
import json
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECK = os.path.join(ROOT, "3_ai_outputs", "hand_check")
SHEET = os.path.join(CHECK, "hand_check_sheet.xlsx")
HOW = os.path.join(ROOT, "3_ai_outputs", "how_we_did_it.md")
START, END = "<!-- hand-check:start -->", "<!-- hand-check:end -->"


def kappa(a, b):
    """Cohen's kappa for two yes/no lists: agreement beyond chance."""
    a, b = pd.Series(a).astype(bool), pd.Series(b).astype(bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def load(sheet):
    df = pd.read_excel(SHEET, sheet_name=sheet)
    df = df.dropna(subset=["topic", "leave_intent"])
    df["leave_intent"] = df["leave_intent"].astype(int)
    df["topic"] = df["topic"].astype(str).str.strip()
    return df


def compare(human, ai, who):
    m = human.merge(ai, on="sentence", suffixes=("_human", "_ai"))
    return {
        "who": who, "sentences": len(m),
        "intent_exact": (m["leave_intent_human"] == m["leave_intent_ai"]).mean(),
        "flag_agree": ((m["leave_intent_human"] >= 1) == (m["leave_intent_ai"] >= 1)).mean(),
        "flag_kappa": kappa(m["leave_intent_human"] >= 1, m["leave_intent_ai"] >= 1),
        "topic_agree": (m["topic_human"] == m["topic_ai"]).mean(),
    }, m


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ai = pd.read_csv(os.path.join(ROOT, "3_ai_outputs", "sentence_labels.csv"))
    who_path = os.path.join(CHECK, "labelers.json")
    who = json.load(open(who_path, encoding="utf-8")) if os.path.exists(who_path) else {}
    results, disagree = [], []
    filled = {}
    for sheet in ["Labeler A", "Labeler B"]:
        h = load(sheet)
        if len(h):
            filled[sheet] = h
            r, m = compare(h, ai, sheet)
            results.append(r)
            d = m[(m["leave_intent_human"] != m["leave_intent_ai"]) | (m["topic_human"] != m["topic_ai"])]
            disagree.append(d.assign(labeler=sheet)[["labeler", "id", "sentence", "topic_ai", "topic_human",
                                                      "leave_intent_ai", "leave_intent_human"]])
    if not results:
        print("Nothing filled in yet. Open 3_ai_outputs/hand_check/hand_check_sheet.xlsx and label a sheet first.")
        return
    ab = None
    if len(filled) == 2:
        x = filled["Labeler A"].merge(filled["Labeler B"], on="id", suffixes=("_a", "_b"))
        ab = {"sentences": len(x),
              "flag_agree": ((x["leave_intent_a"] >= 1) == (x["leave_intent_b"] >= 1)).mean(),
              "intent_exact": (x["leave_intent_a"] == x["leave_intent_b"]).mean(),
              "topic_agree": (x["topic_a"] == x["topic_b"]).mean()}

    pd.concat(disagree).to_csv(os.path.join(CHECK, "disagreements.csv"), index=False, encoding="utf-8-sig")
    res = pd.DataFrame(results)
    flag = res["flag_agree"].mean()
    for r in results:
        r["description"] = who.get(r["who"], "team member")
    summary = {"labelers": len(results), "sentences": int(res["sentences"].max()),
               "per_labeler": [{k: (float(v) if isinstance(v, float) else v) for k, v in r.items()} for r in results],
               "flag_agree": flag, "intent_exact": res["intent_exact"].mean(),
               "topic_agree": res["topic_agree"].mean(), "flag_kappa": res["flag_kappa"].mean(),
               "human_vs_human": ab}
    with open(os.path.join(CHECK, "result.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=float)

    lines = [START, "", "**Label check.** "
             f"{summary['sentences']} sentences (all 75 the AI marked as leave intent plus 25 random others) were "
             "labelled again from the written definitions in the Guide sheet and compared with the first labels.", "",
             "| Labeler | Who | Sentences | Leave / not leave agrees | Exact intent level agrees | Topic agrees | Kappa (leave / not) |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f"| {r['who']} | {r['description']} | {r['sentences']} | {r['flag_agree']:.0%} | "
                     f"{r['intent_exact']:.0%} | {r['topic_agree']:.0%} | {r['flag_kappa']:.2f} |")
    if ab:
        lines += ["", f"The two team members agreed with each other on leave / not leave for {ab['flag_agree']:.0%} "
                      f"of sentences and on the exact topic for {ab['topic_agree']:.0%}, so the AI is about as consistent "
                      "as a second person." if abs(ab["flag_agree"] - flag) < 0.05 else
                      f"The two team members agreed with each other on leave / not leave for {ab['flag_agree']:.0%} "
                      f"of sentences and on the exact topic for {ab['topic_agree']:.0%}."]
    allm = pd.concat([compare(filled[k], ai, k)[1] for k in filled])
    moved = int(((allm["leave_intent_human"] >= 3) != (allm["leave_intent_ai"] >= 3)).sum()
                + ((allm["leave_intent_human"] >= 1) != (allm["leave_intent_ai"] >= 1)).sum())
    lines += ["", f"Disagreements that would move a customer between tiers (no signal / R2 / R1): {moved}. "
                  "A difference between intent 1 and 2 keeps the customer in R2, so it changes no audience or NT$ figure.",
              "", "Every disagreement is listed in `hand_check/disagreements.csv`.", "", END]
    block = "\n".join(lines)

    with open(HOW, encoding="utf-8") as f:
        how = f.read()
    if START in how:
        how = re.sub(re.escape(START) + r".*?" + re.escape(END), block, how, flags=re.S)
    else:
        how = re.sub(r"\*\*Checks\.\*\* A blind hand check.*?when run\. ", "**Checks.** ", how, flags=re.S)
        how = how.rstrip() + "\n\n" + block + "\n"
    with open(HOW, "w", encoding="utf-8") as f:
        f.write(how)

    print(res.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    if ab:
        print(f"Human vs human: leave/not leave {ab['flag_agree']:.0%}, topic {ab['topic_agree']:.0%}")
    print("Written: 3_ai_outputs/hand_check/result.json, disagreements.csv, and how_we_did_it.md")
    print("Now run `python run.py` so the talk script uses these numbers.")


if __name__ == "__main__":
    main()
