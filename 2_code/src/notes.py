"""Step 2: read support notes with the AI sentence labels.

The AI step ran once, offline: every distinct sentence pattern in the notes was
labelled with a topic and a leave-intent level (0-3). The labels live in
3_ai_outputs/sentence_labels.csv. This module only looks them up, so a rerun
never calls a model. A sentence the labels do not cover marks the ticket
'unknown' and sends it to the review queue.
"""
import re
import pandas as pd

RIVALS = r"(PacificTel|IslandCom|Skyward Mobile)"
TRAIL = r"\s+(this week|for now|as things stand|at this point|today|this month|right now|at the moment|lately|again)\.$"

# Topics that point to a reason a customer may leave, and the offer that answers it.
REASON_GROUP = {
    "bill_shock": "billing", "billing_error": "billing", "payment_issue": "billing",
    "coverage": "network", "data_speed": "network", "roaming_problem": "network",
    "price_value": "price", "wants_cheaper_plan": "price", "competitor": "price",
    "device_fault": "device", "device_upgrade": "device",
    "wants_more_data": "data_need",
    "renewal_doubt": "contract", "cancel": "contract", "port_out": "contract",
}


def normalise(sentence):
    s = re.sub(r"NT\$\s?[\d,]+", "NT$<N>", sentence)
    s = re.sub(RIVALS, "<RIVAL>", s)
    s = re.sub(TRAIL, ".", s)
    return s.strip()


def split_sentences(note):
    if pd.isna(note) or not str(note).strip():
        return []
    return [p.strip() for p in re.split(r"(?<=\.)\s+", str(note).strip()) if p.strip()]


def read_notes(tickets, labels_path):
    lab = pd.read_csv(labels_path)
    lookup = {r.sentence: (r.topic, int(r.leave_intent)) for r in lab.itertuples()}
    rows, queue = [], []
    for t in tickets.itertuples():
        topics, intent, unknown = set(), 0, []
        for s in split_sentences(t.free_text_note):
            key = normalise(s)
            if key in lookup:
                topic, lvl = lookup[key]
                if topic != "filler":
                    topics.add(topic)
                intent = max(intent, lvl)
            else:
                unknown.append(s)
        note = t.free_text_note if isinstance(t.free_text_note, str) else ""
        rival = re.search(RIVALS, note)
        bill = re.search(r"NT\$\s?([\d,]+)", note)
        status = "unknown" if unknown else ("no_note" if not note.strip() else "read")
        if unknown:
            queue.append({"ticket_id": t.ticket_id, "sub_id": t.sub_id, "date": t.date,
                          "unread_sentences": " | ".join(unknown), "status": "unknown"})
        rows.append({
            "ticket_id": t.ticket_id, "sub_id": t.sub_id, "date": t.date,
            "agent_category": t.category, "read_status": status,
            "topics": ";".join(sorted(topics)), "leave_intent": intent,
            "reasons": ";".join(sorted({REASON_GROUP[x] for x in topics if x in REASON_GROUP})),
            "rival_named": rival.group(1) if rival else "",
            "bill_amount_twd": float(bill.group(1).replace(",", "")) if bill else None,
            "no_save": "line_closing_no_save" in topics,
        })
    read = pd.DataFrame(rows)
    read["tag_missed_risk"] = (read["leave_intent"] >= 2) & (read["agent_category"] != "cancel_inquiry")
    return read, pd.DataFrame(queue, columns=["ticket_id", "sub_id", "date", "unread_sentences", "status"])
