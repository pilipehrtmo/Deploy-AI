"""Step 3: turn read notes into customer signals, test the rules on the past, pick audiences.

Every rule only uses what was known on the day it is applied (the cutoff):
notes dated before the cutoff, and tenure counted up to the cutoff.
"""
import pandas as pd

LOOKBACK_DAYS = 90
SCALE = 130  # the sample is about 1 in 130 customers


def customer_signals(read, asof):
    """One row per customer: what their notes said in the 90 days before `asof`."""
    win = read[(read["date"] < asof) & (read["date"] >= asof - pd.Timedelta(days=LOOKBACK_DAYS))]
    if win.empty:
        return pd.DataFrame(columns=["sub_id"])
    g = win.groupby("sub_id")
    out = pd.DataFrame({
        "max_intent": g["leave_intent"].max(),
        "n_tickets": g["ticket_id"].size(),
        "reasons": g["reasons"].agg(lambda x: ";".join(sorted({r for v in x for r in v.split(";") if r}))),
        "topics": g["topics"].agg(lambda x: ";".join(sorted({r for v in x for r in v.split(";") if r}))),
        "no_save": g["no_save"].any(),
        "last_note": g["date"].max(),
        "rival_named": g["rival_named"].agg(lambda x: next((v for v in x if v), "")),
        "any_unknown": g["read_status"].agg(lambda x: (x == "unknown").any()),
    }).reset_index()
    return out


def risk_tier(row):
    """Written rules, in priority order. Returns (tier, why)."""
    if row.get("no_save") is True:
        return "X_no_save", "line closing for a reason an offer cannot change"
    if row.get("any_unknown") is True and pd.isna(row.get("max_intent")):
        return "U_unknown", "note not yet read; waiting in review queue"
    mi = row.get("max_intent")
    if pd.notna(mi) and mi >= 3:
        return "R1_leaving_now", "note says they are cancelling, porting or signing elsewhere"
    if pd.notna(mi) and mi >= 1:
        return "R2_wavering", "note says they are considering leaving or doubt renewal"
    if row["tenure_at_asof"] <= 6:
        return "R3_new_and_fragile", "joined in the last 6 months"
    reasons = row.get("reasons") if isinstance(row.get("reasons"), str) else ""
    if "billing" in reasons or "network" in reasons:
        return "R4_unhappy_quiet", "complained about billing or network, no leave talk yet"
    return "R0_no_signal", ""


def population(subs, asof, postpaid_only=True):
    p = subs[(subs["join_date"] < asof) & (subs["churn_date"].isna() | (subs["churn_date"] >= asof))].copy()
    if postpaid_only:
        p = p[p["is_postpaid"]]
    p["tenure_at_asof"] = ((asof - p["join_date"]).dt.days / 30.44).round(1)
    p["months_to_contract_end"] = ((p["contract_end"] - asof).dt.days / 30.44).round(1)
    return p


def score(subs, read, asof, postpaid_only=True):
    p = population(subs, asof, postpaid_only)
    p = p.merge(customer_signals(read, asof), on="sub_id", how="left")
    tiers = p.apply(lambda r: risk_tier(r.to_dict()), axis=1, result_type="expand")
    p["tier"], p["tier_reason"] = tiers[0], tiers[1]
    return p


def backtest(subs, read, cutoffs, horizon_days=60):
    """Flag customers using notes before each cutoff, then check who left in the next 60 days."""
    rows = []
    for c in cutoffs:
        asof = pd.Timestamp(c)
        p = score(subs, read, asof)
        p["left"] = (p["churn_date"] >= asof) & (p["churn_date"] < asof + pd.Timedelta(days=horizon_days))
        base = p["left"].mean()
        total_left = p["left"].sum()
        for tier, g in p.groupby("tier"):
            rows.append({"cutoff": asof.date(), "rule": tier, "customers": len(g),
                         "left_next_60d": int(g["left"].sum()), "churn_rate": round(g["left"].mean(), 4),
                         "lift_vs_all": round(g["left"].mean() / base, 2),
                         "share_of_all_leavers": round(g["left"].sum() / total_left, 3)})
        # Formosa's current approach: renewal push to contracts ending within 4 months.
        ce = p["months_to_contract_end"].le(4)
        rows.append({"cutoff": asof.date(), "rule": "BASELINE_contract_ends_<=4m", "customers": int(ce.sum()),
                     "left_next_60d": int(p.loc[ce, "left"].sum()), "churn_rate": round(p.loc[ce, "left"].mean(), 4),
                     "lift_vs_all": round(p.loc[ce, "left"].mean() / base, 2),
                     "share_of_all_leavers": round(p.loc[ce, "left"].sum() / total_left, 3)})
        rows.append({"cutoff": asof.date(), "rule": "ALL_postpaid", "customers": len(p),
                     "left_next_60d": int(total_left), "churn_rate": round(base, 4), "lift_vs_all": 1.0,
                     "share_of_all_leavers": 1.0})
    return pd.DataFrame(rows)


# ---------- Offer rules (approved offers only, see FACT_SHEET) ----------

def retention_offer(r):
    """Pick the one approved retention offer that answers the customer's reason."""
    reasons = r["reasons"] if isinstance(r["reasons"], str) else ""
    # Paid offers go only to customers who said they may leave (R1/R2).
    if r["tier"] == "R3_new_and_fragile":
        return "No offer: welcome check-in"
    if r["tier"] == "R4_unhappy_quiet":
        return "No offer: fix the bill and call back" if "billing" in reasons else "No offer: network care call"
    eligible_renewal = pd.isna(r["contract_end"]) or r["months_to_contract_end"] <= 4
    premium = r["plan_type"] == "postpaid_premium"
    if "device" in reasons and premium:
        return "Device credit"
    if ("contract" in reasons or "price" in reasons) and eligible_renewal:
        return "Renewal discount"
    if ("price" in reasons or "data_need" in reasons or "contract" in reasons) and not r["unlimited_data"]:
        return "Data boost"
    if "billing" in reasons:
        return "No offer: fix the bill and call back"
    if "network" in reasons:
        return "No offer: network care call"
    if eligible_renewal:
        return "Renewal discount"
    if not r["unlimited_data"]:
        return "Data boost"
    return "No offer: care call"


def upsell_offer(r):
    topics = r["topics"] if isinstance(r["topics"], str) else ""
    if "roaming_interest" in topics and r["is_postpaid"]:
        return "Roaming pass"
    if r["plan_type"] == "postpaid_basic" and ("wants_more_data" in topics or "plan_question" in topics):
        return "Plan upgrade"
    if r["is_postpaid"] and not r["unlimited_data"] and ("wants_more_data" in topics or "data_speed" in topics):
        return "Data add-on"
    return None


def audiences(subs, read, asof):
    """Audiences for the next campaign, as of `asof` (1 July 2026 for the real run)."""
    allp = score(subs, read, asof, postpaid_only=False)
    allp["other_team"] = allp["plan_type"].isin(["family", "business"])

    ret = allp[allp["is_postpaid"] & allp["tier"].isin(["R1_leaving_now", "R2_wavering", "R3_new_and_fragile", "R4_unhappy_quiet"])].copy()
    ret["offer"] = ret.apply(retention_offer, axis=1)
    ret["channel_plan"] = ret["tier"].map({
        "R1_leaving_now": "Outbound Call (priority by bill size), else SMS",
        "R2_wavering": "Outbound Call if capacity, else LINE/SMS",
        "R3_new_and_fragile": "App Push / LINE welcome check-in",
        "R4_unhappy_quiet": "SMS / LINE care message"})
    ret["audience"] = "retention_" + ret["tier"]

    calm = allp[~allp["tier"].isin(["R1_leaving_now", "R2_wavering", "X_no_save"]) & ~allp["other_team"]].copy()
    calm["offer"] = calm.apply(upsell_offer, axis=1)
    up = calm[calm["offer"].notna()].copy()
    up["audience"] = "upsell_" + up["offer"].str.lower().str.replace(" ", "_")
    up["channel_plan"] = up["offer"].map({"Roaming pass": "App Push / Email",
                                          "Plan upgrade": "App Push / LINE",
                                          "Data add-on": "App Push / LINE"})
    up["tier_reason"] = "asked about it in a support note in the last 90 days"

    cols = ["sub_id", "audience", "plan_type", "monthly_arpu_twd", "tenure_at_asof", "months_to_contract_end",
            "unlimited_data", "tier", "tier_reason", "reasons", "topics", "rival_named", "offer", "channel_plan"]
    members = pd.concat([ret[cols], up[cols]], ignore_index=True)
    flagged = allp[allp["other_team"] & allp["tier"].isin(["R1_leaving_now", "R2_wavering"])][
        ["sub_id", "plan_type", "tier", "tier_reason", "reasons"]]
    return members, flagged, allp
