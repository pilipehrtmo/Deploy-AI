"""Rebuild everything from the raw files with one command.

    python run.py                       # uses data/raw/
    python run.py --data path/to/DATA   # other data folder
    python run.py --new-notes new.csv   # add a new support-notes file and refresh every audience
"""
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
import clean, notes, signals, audit, campaigns, sizing, report  # noqa: E402
import re  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # hand-in folder: 1_report, 2_code, 3_ai_outputs, 4_outputs, 5_finals
AS_OF = pd.Timestamp("2026-07-01")
CUTOFFS = ["2026-03-01", "2026-04-01", "2026-05-01"]


def save(df, name, out):
    df = df.copy()
    for c in df.select_dtypes("float").columns:
        df[c] = df[c].round(4 if df[c].abs().max() < 10 else 0 if df[c].abs().max() > 1000 else 2)
    df.to_csv(os.path.join(out, name), index=False, encoding="utf-8-sig")  # Excel-friendly
    print(f"  wrote 4_outputs/{name} ({len(df)} rows)")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "data", "raw"))
    ap.add_argument("--new-notes", default=None, help="extra support_tickets-style CSV")
    ap.add_argument("--asof", default=str(AS_OF.date()))
    a = ap.parse_args()
    out = os.path.join(ROOT, "4_outputs")
    os.makedirs(out, exist_ok=True)
    asof = pd.Timestamp(a.asof)

    print("1/6 cleaning raw files")
    subs, tickets, camps, contacts, copy, log = clean.run(a.data)
    if a.new_notes:
        extra = clean.clean_tickets(a.new_notes, subs)
        tickets = pd.concat([tickets, extra]).drop_duplicates("ticket_id", keep="last")
        log = pd.DataFrame(clean.LOG)
        print(f"  added new notes file: {len(extra)} tickets")
    save(log, "cleaning_log.csv", out)
    save(subs, "customers_clean.csv", out)

    print("2/6 reading support notes with the AI sentence labels")
    read, queue = notes.read_notes(tickets, os.path.join(ROOT, "3_ai_outputs", "sentence_labels.csv"))
    save(read, "notes_read.csv", out)
    save(queue, "review_queue.csv", out)
    missed = read[read["tag_missed_risk"]]
    print(f"  {len(missed)} notes say the customer may leave but were not tagged cancel_inquiry")

    print("3/6 testing the rules on past cutoffs (notes before cutoff only)")
    bt = signals.backtest(subs, read, CUTOFFS)
    save(bt, "backtest.csv", out)

    print(f"4/6 picking audiences as of {asof.date()}")
    members, flagged, scored = signals.audiences(subs, read, asof)
    save(members, "audience_members.csv", out)
    save(flagged, "flagged_family_business.csv", out)
    seg = scored.groupby(["plan_type", "tier"]).agg(customers=("sub_id", "size"),
                                                     avg_bill=("monthly_arpu_twd", "mean")).reset_index()
    seg["customers_full_base"] = seg["customers"] * sizing.SCALE
    save(seg, "segments.csv", out)
    aud = members.groupby(["audience", "offer"]).size().reset_index(name="customers_in_sample")
    aud["customers_full_base"] = aud["customers_in_sample"] * sizing.SCALE
    save(aud, "audiences_summary.csv", out)

    print("5/6 auditing past campaigns")
    by_obj, by_obj_ch, roas = audit.holdout_lift(contacts, camps)
    save(by_obj, "audit_holdout_by_objective.csv", out)
    save(by_obj_ch, "audit_holdout_by_channel.csv", out)
    save(roas, "audit_reported_vs_incremental_roas.csv", out)
    paid, by_ch, by_seg, by_year = audit.paid_economics(camps)
    save(by_ch, "audit_paid_by_channel.csv", out)
    save(by_seg, "audit_paid_by_segment.csv", out)
    save(by_year, "audit_paid_payback_by_year.csv", out)
    ca = audit.copy_audit(camps, copy)
    save(ca, "audit_copy_compliance.csv", out)

    print("6/6 drafting campaigns and sizing the pilot")
    tpl = campaigns.load_templates(os.path.join(ROOT, "3_ai_outputs", "copy_templates.json"))
    camp = campaigns.build_campaigns(members, tpl)
    save(camp, "new_campaigns.csv", out)
    val = pd.concat([sizing.retention_value(members, bt), sizing.upsell_value(members)], ignore_index=True)
    save(val, "value_ranges.csv", out)
    save(sizing.acquisition_value(by_ch), "acquisition_scenarios.csv", out)
    pilot, breakeven, per_msg = sizing.pilot(members, bt, camps)
    save(pilot, "pilot_scenarios.csv", out)
    save(pd.DataFrame(sizing.ASSUMPTIONS, columns=["key", "what", "value", "why"]), "assumptions.csv", out)

    print("7/7 writing the readable report, workbook and slides")
    R = collect(subs, read, bt, members, flagged, scored, by_obj, roas, by_ch, ca, camp, val, pilot, breakeven,
                log, camps, contacts, aud, seg)
    report.build(R, ROOT)
    print("  wrote 4_outputs/RESULTS.xlsx, 1_report/report.html, 5_finals/slides.html")

    print("\nHeadlines")
    b = bt[bt["rule"].isin(["R1_leaving_now", "R2_wavering", "BASELINE_contract_ends_<=4m", "ALL_postpaid"])]
    print(b.groupby("rule")[["customers", "left_next_60d"]].sum().assign(
        churn_rate=lambda d: (d.left_next_60d / d.customers).round(3)).to_string())
    print(f"  past campaigns failing compliance: {(~ca['compliant']).sum()} of {len(ca)}")
    print(f"  pilot break-even save rate: {breakeven:.1%}")
    print(f"  new campaigns drafted: {len(camp)}, all compliant: {bool(camp['compliant'].all())}")


REASON_NAMES = {"price": "Price or a rival's offer", "contract": "Unsure about renewing / cancelling",
                "billing": "Bill looks wrong or too high", "network": "Coverage or speed",
                "device": "Phone problem", "data_need": "Runs out of data"}


def collect(subs, read, bt, members, flagged, scored, by_obj, roas, by_ch, ca, camp, val, pilot, breakeven,
            log, camps, contacts, aud, seg):
    g = bt.groupby("rule")[["customers", "left_next_60d"]].sum().reset_index()
    allr = g.set_index("rule").loc["ALL_postpaid"]
    base = allr["left_next_60d"] / allr["customers"]
    g["churn_rate"] = g["left_next_60d"] / g["customers"]
    g["lift_vs_all"] = g["churn_rate"] / base
    g["share_of_all_leavers"] = g["left_next_60d"] / allr["left_next_60d"]
    gi = g.set_index("rule")
    sig = gi.loc[["R1_leaving_now", "R2_wavering"]].sum()

    post = subs[subs["is_postpaid"]]
    rows = []
    for m in pd.period_range("2026-01", "2026-06", freq="M"):
        st, en = m.start_time, m.end_time
        b = post[(post["join_date"] < st) & (post["churn_date"].isna() | (post["churn_date"] >= st))]
        left = ((b["churn_date"] >= st) & (b["churn_date"] <= en)).sum()
        rows.append({"month": str(m), "customers": len(b), "left": int(left), "churn_rate": left / len(b)})
    monthly = pd.DataFrame(rows)

    r12 = members[members["tier"].isin(["R1_leaving_now", "R2_wavering"])]
    rs = r12["reasons"].fillna("").str.split(";").explode()
    rs = rs[rs != ""].map(REASON_NAMES).value_counts().reset_index()
    rs.columns = ["reason", "customers"]

    seg_plan = subs.groupby("plan_type").agg(customers=("sub_id", "size"), avg_bill=("monthly_arpu_twd", "mean"),
                                            churn_6m=("churn_flag", "mean")).reset_index()
    seg_plan["customers_full_base"] = seg_plan["customers"] * sizing.SCALE

    acq = sizing.acquisition_value(by_ch)
    roam_year = camps.loc[camps["objective"] == "roaming", "spend_twd"].sum() / 2
    vc = val.set_index(["objective", "scenario"])
    mixed = log.loc[log["step"].str.contains("contract_end"), "note"].iloc[0]
    K = {
        "sig_rate": sig["left_next_60d"] / sig["customers"], "base_rate": base,
        "ce_rate": gi.loc["BASELINE_contract_ends_<=4m", "churn_rate"],
        "sig_lift": (sig["left_next_60d"] / sig["customers"]) / base,
        "sig_share": sig["left_next_60d"] / allr["left_next_60d"],
        "r3_rate": gi.loc["R3_new_and_fragile", "churn_rate"], "r3_lift": gi.loc["R3_new_and_fragile", "lift_vs_all"],
        "missed": int(read["tag_missed_risk"].sum()),
        "churn_low": vc.loc[("1 churn", "low"), "net_margin_twd"], "churn_high": vc.loc[("1 churn", "high"), "net_margin_twd"],
        "kept_low": vc.loc[("1 churn", "low"), "customers_kept_per_year"], "kept_high": vc.loc[("1 churn", "high"), "customers_kept_per_year"],
        "roam_spend_year": roam_year,
        "up_low": vc.loc[("2 earn more", "low"), "net_margin_twd"] + roam_year,
        "up_high": vc.loc[("2 earn more", "high"), "net_margin_twd"] + roam_year,
        "acq_low": acq["extra_6m_margin_from_shift_twd"].min(), "acq_high": acq["extra_6m_margin_from_shift_twd"].max(),
        "best_cpl": by_ch["cost_per_line"].min(), "worst_cpl": by_ch["cost_per_line"].max(),
        "pilot_cost_low": pilot["total_cost"].min(), "pilot_cost_high": pilot["total_cost"].max(),
        "breakeven": breakeven,
        "breakeven_gap": breakeven * sizing.churn_rate_from_backtest(bt, ["R1_leaving_now", "R2_wavering"]),
        "bad_copy": int((~ca["compliant"]).sum()), "all_copy": len(ca), "vague": int(ca["vague_target"].sum()),
        "mixed_dates": n_from(mixed), "late_contacts": int((~contacts["window_complete"]).sum()),
        "monthly_mean": monthly["churn_rate"].mean(),
        "up_aud": int(members["audience"].str.startswith("upsell_").sum() * sizing.SCALE),
        "flag_fb": len(flagged) * sizing.SCALE,
    }
    return {"K": K, "bt_pooled": g, "monthly_churn": monthly, "reasons": rs, "seg_plan": seg_plan,
            "roas": roas, "paid_by_ch": by_ch, "pilot": pilot, "val": val, "acq": acq, "camp": camp,
            "copy_audit": ca, "log": log, "aud": aud, "seg": seg,
            "assump": pd.DataFrame(sizing.ASSUMPTIONS, columns=["key", "what", "value", "why"])}


def n_from(text):
    m = re.search(r"\d[\d,]*", str(text))
    return m.group(0) if m else "?"


if __name__ == "__main__":
    main()
