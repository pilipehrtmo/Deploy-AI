"""Step 6: put a NT$ range on each objective, and cost the 90-day pilot.

Every assumption is written in the ASSUMPTIONS table and saved with the results.
"""
import pandas as pd

SCALE = 130
MARGIN = 0.60
CREDIT_MONTHS = 6
CALLS_PER_MONTH = 2000
BUDGET = 2_500_000
OFFER_COST = {"Data boost": 300, "Renewal discount": 1200, "Device credit": 3000,
              "Plan upgrade": 400, "Data add-on": 298, "Roaming pass": 499}
CHANNEL_SHARE = {"SMS": 0.74, "LINE": 0.41, "Email": 0.33, "App Push": 0.27, "Outbound Call": 0.92}

ASSUMPTIONS = [
    ("save_rate", "Share of would-be leavers we keep after contact", "10% / 20% / 35%",
     "Unknown (FACT_SHEET). The pilot exists to measure it. Below the break-even rate, stop."),
    ("churn_in_60d_flagged", "Share of flagged customers who leave within 60 days without action",
     "from backtest", "Measured on Mar/Apr/May 2026 cutoffs, notes before cutoff only."),
    ("offer_takers", "Customers who take the offer per customer saved", "1.5",
     "Some customers who would have stayed also take the offer; this cost is counted."),
    ("value_per_save", "Credit for one saved customer", "6 x monthly bill",
     "Finance rule (FACT_SHEET): six months of revenue. Lifetime value is higher; not counted."),
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
        revenue = saves_year * bill * CREDIT_MONTHS
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
    msg_cost = calls * per_msg.get("Outbound Call", 4) + rest * (per_msg.get("SMS", 0.25) + per_msg.get("LINE", 0.2))
    bill = ret["monthly_arpu_twd"].mean()
    offer_cost = ret["offer"].map(OFFER_COST).fillna(0).mean()
    rows = []
    for name, save in [("low", 0.10), ("mid", 0.20), ("high", 0.35)]:
        saves = treated * p_leave * save
        offers = saves * 1.5 * offer_cost
        total = msg_cost + offers + creative * 3
        revenue = saves * bill * CREDIT_MONTHS
        rows.append({"scenario": name, "save_rate": save, "flagged_full_base_90d": flagged_90d,
                     "treated": treated, "held_back_20pct": held_back, "outbound_calls": calls,
                     "messaging_cost": round(msg_cost), "offer_cost": round(offers), "creative_cost": round(creative * 3),
                     "total_cost": round(total), "within_budget": total <= BUDGET,
                     "customers_kept": round(saves), "credited_revenue": round(revenue),
                     "margin_minus_cost": round(revenue * MARGIN - total)})
    df = pd.DataFrame(rows)
    # Break-even save rate: margin from saves = cost.
    fixed = msg_cost + creative * 3
    per_save_margin = bill * CREDIT_MONTHS * MARGIN - 1.5 * offer_cost
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
