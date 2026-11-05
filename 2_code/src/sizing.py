"""Step 6: put a NT$ range on each objective, and cost the 90-day pilot.

Every assumption is written in the ASSUMPTIONS table and saved with the results.
"""
import pandas as pd

SCALE = 130
MARGIN = 0.60
CREDIT_MONTHS = 6
KEPT_MONTHS = 6.0        # set by run.py from the data: months a kept customer pays inside the 6-month credit
MONTHLY_CHURN = 0.018
KEPT_CHURN_M = 0.0    # set by run.py: average postpaid churn per month (for the 24-month view)
PLANNING_SAVE_RATE = 0.20
CALLS_PER_MONTH = 2000
BUDGET = 2_500_000
OFFER_COST = {"Data boost": 300, "Renewal discount": 1200, "Device credit": 3000,
              "Plan upgrade": 400, "Data add-on": 298, "Roaming pass": 499}
CHANNEL_SHARE = {"SMS": 0.74, "LINE": 0.41, "Email": 0.33, "App Push": 0.27, "Outbound Call": 0.92}

ASSUMPTIONS = [
    ("save_rate", "Share of would-be leavers we keep after contact", "20% planning figure; 10% and 35% shown",
     "Unknown (Vivian, round 2). Why 20%: about 4 in 5 reasons flagged customers give (price, rival, renewal) have a "
     "matching approved offer; we assume one in four of those would-be leavers accepts and stays. Below {breakeven} the "
     "pilot loses money; {breakeven}-{mde} makes money but cannot be proven in 90 days; {mde}+ is proven."),
    ("churn_in_60d_flagged", "Share of flagged customers who leave within 60 days without action",
     "from backtest", "Measured on Mar/Apr/May 2026 cutoffs, notes before cutoff only."),
    ("offer_takers", "Customers who take the offer per customer saved", "1.5",
     "Some customers who would have stayed also take the offer; this cost is counted."),
    ("value_per_save", "Credit for one saved customer", "monthly bill x months they keep paying (max 6)",
     "Finance rule, confirmed by Vivian: six months of the full bill, stopping if they cancel. Flagged customers "
     "who are still with us after 60 days leave at about 12% a month (data), so a kept customer pays about "
     "{kept:.1f} of the 6 months on average."),
    ("calls", "Outbound call cost", "NT$2 per number dialled + NT$25 per conversation",
     "Vivian: two charges, per conversation not per minute. Solved exactly from the 6 call campaigns in "
     "campaigns.csv; about 7.5% of dials became conversations. Care call-backs count toward the 2,000 a month."),
    ("lifetime", "Longer view, shown beside the 6-month credit", "24 months at the observed churn rate",
     "Vivian: start with the six-month credit, a lifetime view may sit beside it. New customers: 1.8% monthly "
     "churn (postpaid average). Kept at-risk customers: their own higher rate."),
    ("upsell_take", "Share of customers who asked about it in a note and then buy", "3% / 6% / 10%",
     "Past broad upsell added about 0.16 points over holdout; asked-for offers should do better. Pilot measures it."),
    ("scale", "Sample to full base", "x130", "FACT_SHEET: sample is about 1 in 130."),
    ("flow", "New flagged customers per month", "90-day audience / 3",
     "Audience uses notes from the last 90 days."),
]


def unit_costs(camps):
    owned = camps[camps["channel_type"] == "owned"]
    per_msg = (owned["messaging_twd"] / owned["sent"]).groupby(owned["channel"]).median().to_dict()
    creative = owned["creative_twd"].median()
    return per_msg, creative


def call_charges(camps):
    """Split the call cost into a per-dial and a per-conversation charge (least squares on call campaigns)."""
    import numpy as np
    k = camps[camps["channel"] == "Outbound Call"]
    (per_dial, per_conv), *_ = np.linalg.lstsq(np.c_[k["sent"], k["clicks"]], k["messaging_twd"], rcond=None)
    return float(per_dial), float(per_conv), float(k["clicks"].sum() / k["sent"].sum())


def months_paid(monthly_churn, horizon):
    """Expected months a customer pays in the next `horizon` months at a constant monthly churn."""
    return sum((1 - monthly_churn) ** t for t in range(horizon))


def kept_monthly_churn(two_month_rate):
    return 1 - (1 - two_month_rate) ** 0.5


def churn_rate_from_backtest(bt, tiers):
    x = bt[bt["rule"].isin(tiers)]
    return x["left_next_60d"].sum() / x["customers"].sum()


def retention_value(members, bt):
    ret = members[members["audience"].str.startswith("retention_R1") | members["audience"].str.startswith("retention_R2")]
    p_leave = churn_rate_from_backtest(bt, ["R1_leaving_now", "R2_wavering"])
    per_month = len(ret) * SCALE / 3
    bill = ret["monthly_arpu_twd"].mean()
    offer_cost = ret["offer"].map(OFFER_COST).fillna(0).mean()
    rows = []
    for name, save in [("low", 0.10), ("mid", 0.20), ("high", 0.35)]:
        saves_year = per_month * 12 * p_leave * save
        revenue = saves_year * bill * KEPT_MONTHS
        cost = saves_year * 1.5 * offer_cost
        rows.append({"objective": "1 churn", "scenario": name, "save_rate": save,
                     "flagged_per_month_full_base": round(per_month), "p_leave_60d": round(p_leave, 3),
                     "customers_kept_per_year": round(saves_year), "credited_revenue_twd": round(revenue),
                     "offer_cost_twd": round(cost), "net_margin_twd": round(revenue * MARGIN - cost)})
    return pd.DataFrame(rows)


def upsell_value(members):
    up = members[members["audience"].str.startswith("upsell_")]
    extra = {"Plan upgrade": (950 - 551) * CREDIT_MONTHS, "Data add-on": 149 * (CREDIT_MONTHS - 2), "Roaming pass": 499}
    rows = []
    per_month = up.groupby("offer").size() * SCALE / 3
    for name, take in [("low", 0.03), ("mid", 0.06), ("high", 0.10)]:
        buyers = per_month * 12 * take
        rev = sum(buyers[o] * extra[o] for o in buyers.index)
        cost = sum(buyers[o] * OFFER_COST[o] for o in buyers.index)
        rows.append({"objective": "2 earn more", "scenario": name, "take_rate": take,
                     "audience_per_month_full_base": round(per_month.sum()),
                     "buyers_per_year": round(buyers.sum()), "credited_revenue_twd": round(rev),
                     "offer_cost_twd": round(cost), "net_margin_twd": round(rev * MARGIN - cost)})
    return pd.DataFrame(rows)


def acquisition_value(paid_by_ch):
    best = paid_by_ch.sort_values("cost_per_line").iloc[0]
    worst = paid_by_ch.sort_values("cost_per_line").iloc[-1]
    rows = []
    for spend in [20_000_000, 40_000_000, 60_000_000]:
        lines_best = spend / best["cost_per_line"]
        lines_worst = spend / worst["cost_per_line"]
        bill = paid_by_ch["revenue_6m"].sum() / paid_by_ch["new_lines"].sum() / CREDIT_MONTHS
        rows.append({"objective": "3 win new", "annual_paid_spend_twd": spend,
                     "best_channel": best["channel"], "lines_if_all_best": round(lines_best),
                     "worst_channel": worst["channel"], "lines_if_all_worst": round(lines_worst),
                     "extra_lines_from_shift": round(lines_best - lines_worst),
                     "extra_6m_margin_from_shift_twd": round((lines_best - lines_worst) * bill * CREDIT_MONTHS * MARGIN)})
    return pd.DataFrame(rows)


def pilot(members, bt, camps):
    """Retention pilot on R1 + R2 postpaid customers, 90 days, 20% held back."""
    per_msg, creative = unit_costs(camps)
    ret = members[members["audience"].isin(["retention_R1_leaving_now", "retention_R2_wavering"])].copy()
    p_leave = churn_rate_from_backtest(bt, ["R1_leaving_now", "R2_wavering"])
    flagged_90d = len(ret) * SCALE                      # one 90-day pilot = one 90-day flow
    treated = round(flagged_90d * 0.8)
    held_back = flagged_90d - treated
    calls = min(CALLS_PER_MONTH * 3, treated)
    rest = treated - calls
    per_dial, per_conv, conv_rate = call_charges(camps)
    call_cost = calls * (per_dial + conv_rate * per_conv)
    msg_cost = call_cost + rest * (per_msg.get("SMS", 0.25) + per_msg.get("LINE", 0.2))
    bill = ret["monthly_arpu_twd"].mean()
    offer_cost = ret["offer"].map(OFFER_COST).fillna(0).mean()
    rows = []
    for name, save in [("low", 0.10), ("mid", 0.20), ("high", 0.35)]:
        saves = treated * p_leave * save
        offers = saves * 1.5 * offer_cost
        total = msg_cost + offers + creative * 3
        revenue = saves * bill * KEPT_MONTHS
        rows.append({"scenario": name, "save_rate": save, "flagged_full_base_90d": flagged_90d,
                     "treated": treated, "held_back_20pct": held_back, "outbound_calls": calls,
                     "messaging_cost": round(msg_cost), "offer_cost": round(offers), "creative_cost": round(creative * 3),
                     "total_cost": round(total), "within_budget": total <= BUDGET,
                     "customers_kept": round(saves), "credited_revenue": round(revenue),
                     "margin_minus_cost": round(revenue * MARGIN - total),
                     "margin_minus_cost_24m": round(saves * bill * months_paid(KEPT_CHURN_M, 24) * MARGIN - total)})
    df = pd.DataFrame(rows)
    # Break-even save rate: margin from saves = cost.
    fixed = msg_cost + creative * 3
    per_save_margin = bill * KEPT_MONTHS * MARGIN - 1.5 * offer_cost
    breakeven = fixed / (treated * p_leave * per_save_margin)
    return df, breakeven, per_msg


def pilot_power(pilot_df, bt):
    """What the pilot can prove. Two-group test, 95% confidence, 80% power.

    Smallest churn gap (contacted vs held back) the pilot can reliably detect,
    and the save rate that gap means.
    """
    p = churn_rate_from_backtest(bt, ["R1_leaving_now", "R2_wavering"])
    row = pilot_df.iloc[0]
    n_t, n_h = row["treated"], row["held_back_20pct"]
    se = (p * (1 - p) * (1 / n_t + 1 / n_h)) ** 0.5
    gap = 2.8 * se                      # 1.96 (95%) + 0.84 (80% power)
    se45 = (p * (1 - p) * (2 / n_t + 2 / n_h)) ** 0.5   # day 45: about half the customers
    return {"p_leave": p, "mde_gap": gap, "mde_save": gap / p, "noise_95": 1.96 * se, "noise_95_day45": 1.96 * se45}


def holdout_options(pilot_df, bt, members):
    """What each held-back share costs (customers not reached) and buys (what the pilot can prove)."""
    p = churn_rate_from_backtest(bt, ["R1_leaving_now", "R2_wavering"])
    flagged = pilot_df.iloc[0]["flagged_full_base_90d"]
    ret = members[members["audience"].isin(["retention_R1_leaving_now", "retention_R2_wavering"])]
    per_save = ret["monthly_arpu_twd"].mean() * KEPT_MONTHS * MARGIN - 1.5 * ret["offer"].map(OFFER_COST).fillna(0).mean()
    rows = []
    for h in (0.10, 0.20, 0.30):
        held = flagged * h
        se = (p * (1 - p) * (1 / (flagged - held) + 1 / held)) ** 0.5
        not_kept = held * p * PLANNING_SAVE_RATE
        rows.append({"held_back_share": h, "held_back_customers": round(held),
                     "smallest_provable_save_rate": 2.8 * se / p,
                     "customers_not_kept_because_held_back": round(not_kept),
                     "margin_forgone_twd": round(not_kept * per_save)})
    return pd.DataFrame(rows)


def acquisition_lifetime(paid_by_ch):
    """Per paid channel: margin per new line on the 6-month credit and on a 24-month view."""
    d = paid_by_ch[["channel", "cost_per_line"]].copy()
    bill = paid_by_ch["revenue_6m"] / paid_by_ch["new_lines"] / CREDIT_MONTHS
    d["monthly_bill"] = bill
    d["margin_6m_per_line"] = bill * CREDIT_MONTHS * MARGIN
    d["margin_24m_per_line"] = bill * months_paid(MONTHLY_CHURN, 24) * MARGIN
    d["return_6m"] = d["margin_6m_per_line"] / d["cost_per_line"]
    d["return_24m"] = d["margin_24m_per_line"] / d["cost_per_line"]
    return d.sort_values("cost_per_line")


def assumptions(breakeven, mde_save):
    """The ASSUMPTIONS table with this run's numbers filled in."""
    vals = {"breakeven": f"{breakeven:.1%}", "mde": f"{mde_save:.1%}", "kept": KEPT_MONTHS}
    rows = [(k, w, v, why.format(**vals)) for k, w, v, why in ASSUMPTIONS]
    return pd.DataFrame(rows, columns=["key", "what", "value", "why"])
