"""Step 4: what past campaigns really earned, measured against the held-back control group."""
import pandas as pd
from compliance import check

MARGIN = 0.60


def holdout_lift(contacts, camps):
    """Owned campaigns with a 20% holdout and a finished 30-day window.

    Incremental revenue per contacted customer = treated revenue per head - holdout revenue per head.
    Scaled to the whole campaign with `sent` from campaigns.csv (whole base).
    """
    o = contacts[contacts["group"].isin(["treatment", "holdout"]) & contacts["window_complete"]]
    o = o.merge(camps[["campaign_id", "objective", "channel", "offer", "holdout_pct"]], on="campaign_id",
                suffixes=("", "_c"))
    o = o[o["holdout_pct"] == 20]

    def summarise(keys):
        g = o.groupby(keys + ["group"]).agg(n=("sub_id", "size"), conv=("converted", "sum"),
                                             rev=("revenue_twd", "sum")).unstack("group").fillna(0)
        out = pd.DataFrame({
            "treated_n": g[("n", "treatment")], "holdout_n": g[("n", "holdout")],
            "treated_conv_rate": g[("conv", "treatment")] / g[("n", "treatment")],
            "holdout_conv_rate": g[("conv", "holdout")] / g[("n", "holdout")],
            "treated_rev_per_head": g[("rev", "treatment")] / g[("n", "treatment")],
            "holdout_rev_per_head": g[("rev", "holdout")] / g[("n", "holdout")],
        })
        out["incremental_rev_per_head"] = out["treated_rev_per_head"] - out["holdout_rev_per_head"]
        out["share_of_reported_that_is_real"] = (out["incremental_rev_per_head"] / out["treated_rev_per_head"]).clip(lower=0)
        return out.reset_index()

    by_obj = summarise(["objective"])
    by_obj_ch = summarise(["objective", "channel"])

    # Whole-base view per objective: reported vs incremental ROAS on campaigns that had a holdout.
    held = camps[(camps["channel_type"] == "owned") & (camps["holdout_pct"] == 20)]
    agg = held.groupby("objective").agg(campaigns=("campaign_id", "size"), spend=("spend_twd", "sum"),
                                        reported_revenue=("revenue_twd", "sum")).reset_index()
    agg = agg.merge(by_obj[["objective", "share_of_reported_that_is_real"]], on="objective", how="left")
    agg["incremental_revenue_est"] = agg["reported_revenue"] * agg["share_of_reported_that_is_real"]
    agg["reported_roas"] = agg["reported_revenue"] / agg["spend"]
    agg["incremental_roas"] = agg["incremental_revenue_est"] / agg["spend"]
    agg["incremental_margin_roas"] = agg["incremental_roas"] * MARGIN
    return by_obj, by_obj_ch, agg


def paid_economics(camps):
    p = camps[camps["channel_type"] == "paid"].copy()
    p["cost_per_new_line"] = p["spend_twd"] / p["conversions"]
    p["monthly_bill_per_new_line"] = p["revenue_twd"] / p["conversions"] / 6
    p["payback_months_on_margin"] = p["cost_per_new_line"] / (p["monthly_bill_per_new_line"] * MARGIN)
    p["margin_roas_6m"] = p["revenue_twd"] * MARGIN / p["spend_twd"]
    p["year"] = p["month"].dt.year
    by_ch = p.groupby("channel").agg(campaigns=("campaign_id", "size"), spend=("spend_twd", "sum"),
                                     new_lines=("conversions", "sum"), revenue_6m=("revenue_twd", "sum"),
                                     median_cost_per_line=("cost_per_new_line", "median"),
                                     median_payback_months=("payback_months_on_margin", "median")).reset_index()
    by_ch["cost_per_line"] = by_ch["spend"] / by_ch["new_lines"]
    by_ch["margin_roas_6m"] = by_ch["revenue_6m"] * MARGIN / by_ch["spend"]
    by_seg = p.groupby("target_segment").agg(campaigns=("campaign_id", "size"), spend=("spend_twd", "sum"),
                                             new_lines=("conversions", "sum"),
                                             median_payback_months=("payback_months_on_margin", "median")
                                             ).reset_index().sort_values("median_payback_months")
    by_year = p.groupby(["year", "channel"])["payback_months_on_margin"].median().unstack().round(2).reset_index()
    return p, by_ch, by_seg, by_year


def copy_audit(camps, copy):
    m = camps[["campaign_id", "month", "objective", "channel", "offer", "target_segment"]].merge(copy, on="campaign_id", how="left")
    m["problems"] = m.apply(lambda r: "; ".join(check(r["headline"], r["body"], r["cta"], r["channel"],
                                                      r["objective"], r["offer"])), axis=1)
    m["compliant"] = m["problems"] == ""
    m["vague_target"] = m["target_segment"].str.lower().isin(
        ["tbd", "not yet defined", "everyone", "all subscribers", "broad target", "general customer base", "not recorded"])
    return m[["campaign_id", "month", "objective", "channel", "offer", "target_segment", "vague_target",
              "compliant", "problems", "headline"]]
