"""Step 1: load the raw files, fix what is wrong, and log every fix with row counts."""
import re
import pandas as pd

CUTOFF_PULL = pd.Timestamp("2026-07-01")
LOG = []


def log(file, step, before, after, note=""):
    LOG.append({"file": file, "step": step, "rows_before": before,
                "rows_after": after, "changed": before - after, "note": note})


def parse_date(x):
    """Dates come as 2026-01-31, 31/01/2026 (day/month/year) or 2026年1月31日."""
    if pd.isna(x) or str(x).strip() == "":
        return pd.NaT
    s = str(x).strip()
    m = re.fullmatch(r"(\d{4})年(\d{1,2})月(\d{1,2})日", s)
    if m:
        return pd.Timestamp(int(m[1]), int(m[2]), int(m[3]))
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", s):
        return pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    return pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")


def strip_text(df, cols, file):
    for c in cols:
        before = df[c].astype("string")
        df[c] = before.str.strip()
        n = int((before.fillna("") != df[c].fillna("")).sum())
        if n:
            log(file, f"strip spaces in {c}", len(df), len(df), f"{n} values had extra spaces")
    return df


def clean_subscribers(path):
    f = "subscribers.csv"
    df = pd.read_csv(path, dtype=str)
    n0 = len(df)
    log(f, "load", n0, n0)
    df = strip_text(df, ["sub_id", "plan_type", "region", "device_tier"], f)

    n = len(df)
    df = df.drop_duplicates()
    log(f, "drop exact duplicate rows", n, len(df))
    n = len(df)
    df = df.drop_duplicates("sub_id", keep="first")
    log(f, "drop repeated sub_id", n, len(df))

    for c in ["monthly_arpu_twd", "tenure_months", "data_gb"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["churn_flag"] = pd.to_numeric(df["churn_flag"], errors="coerce").fillna(0).astype(int)

    raw = df["contract_end"].copy()
    df["contract_end"] = df["contract_end"].map(parse_date)
    mixed = raw.notna() & ~raw.astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$")
    log(f, "unify contract_end date formats", len(df), len(df),
        f"{int(mixed.sum())} dates were dd/mm/yyyy or 年月日 format")
    df["churn_date"] = df["churn_date"].map(parse_date)

    df["unlimited_data"] = df["data_gb"] == 999
    miss_gb = int(df["data_gb"].isna().sum())
    log(f, "flag data_gb 999 as unlimited; keep missing as unknown", len(df), len(df),
        f"{int(df['unlimited_data'].sum())} unlimited, {miss_gb} missing")

    for c in ["region", "device_tier"]:
        m = int(df[c].isna().sum())
        df[c] = df[c].fillna("unknown")
        log(f, f"fill missing {c} with 'unknown'", len(df), len(df), f"{m} missing")

    odd = (df["plan_type"] == "prepaid") & (df["monthly_arpu_twd"] < 100)
    df["arpu_suspect"] = odd
    log(f, "flag prepaid bills under NT$100 as suspect (kept)", len(df), len(df), f"{int(odd.sum())} rows")

    bad = (df["churn_flag"] == 1) & df["churn_date"].isna()
    log(f, "check churn_flag vs churn_date", len(df), len(df), f"{int(bad.sum())} churned rows without a date")

    df["last_day"] = df["churn_date"].fillna(CUTOFF_PULL)
    # Approximate join date: last day minus tenure in months.
    df["join_date"] = df.apply(lambda r: r["last_day"] - pd.DateOffset(months=int(r["tenure_months"])), axis=1)
    df["is_postpaid"] = df["plan_type"].isin(["postpaid_basic", "postpaid_premium"])
    df["active"] = df["churn_flag"] == 0
    return df


def clean_tickets(path, subs):
    f = "support_tickets.csv"
    df = pd.read_csv(path, dtype=str)
    log(f, "load", len(df), len(df))
    df = strip_text(df, ["ticket_id", "sub_id", "category"], f)
    n = len(df)
    df = df.drop_duplicates()
    log(f, "drop exact duplicate rows", n, len(df))
    n = len(df)
    df = df.drop_duplicates("ticket_id", keep="first")
    log(f, "drop repeated ticket_id", n, len(df))

    df["date"] = df["date"].map(parse_date)
    log(f, "unify date formats; missing dates kept but excluded from time tests", len(df), len(df),
        f"{int(df['date'].isna().sum())} tickets have no date")
    m = int(df["category"].isna().sum())
    df["category"] = df["category"].fillna("untagged")
    log(f, "fill missing category with 'untagged'", len(df), len(df), f"{m} missing")
    log(f, "notes with no text kept, read as 'no note'", len(df), len(df),
        f"{int(df['free_text_note'].isna().sum())} empty notes")
    orphan = int((~df["sub_id"].isin(subs["sub_id"])).sum())
    log(f, "check sub_id joins to subscribers", len(df), len(df), f"{orphan} tickets without a customer")
    return df


def clean_campaigns(path):
    f = "campaigns.csv"
    df = pd.read_csv(path, dtype=str)
    log(f, "load", len(df), len(df))
    df = strip_text(df, ["campaign_id", "channel", "channel_type", "objective", "offer", "target_segment"], f)
    num = ["spend_twd", "media_twd", "messaging_twd", "offer_twd", "creative_twd", "sent", "reach",
           "clicks", "conversions", "revenue_twd", "launched_days_after_brief", "impressions", "holdout_pct"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    parts = df[["media_twd", "messaging_twd", "offer_twd", "creative_twd"]].fillna(0).sum(axis=1)
    log(f, "check spend = media + messaging + offer + creative", len(df), len(df),
        f"{int(((parts - df['spend_twd']).abs() > 1).sum())} mismatches")
    m = int(df["target_segment"].isna().sum())
    df["target_segment"] = df["target_segment"].fillna("not recorded")
    log(f, "fill missing target_segment", len(df), len(df), f"{m} missing")
    df["month"] = pd.to_datetime(df["month"] + "-01")
    return df


def clean_contacts(path, campaigns):
    f = "campaign_contacts.csv"
    df = pd.read_csv(path, dtype=str)
    log(f, "load", len(df), len(df))
    df = strip_text(df, ["contact_id", "campaign_id", "sub_id", "group", "channel", "attribution"], f)
    n = len(df)
    df = df.drop_duplicates()
    log(f, "drop exact duplicate rows", n, len(df))
    n = len(df)
    df = df.drop_duplicates(["campaign_id", "sub_id", "group"], keep="first")
    log(f, "drop repeated customer within one campaign", n, len(df))
    for c in ["delivered", "opened", "clicked", "converted", "offer_redeemed", "revenue_twd"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["contact_date"] = df["contact_date"].map(parse_date)
    df["conversion_date"] = df["conversion_date"].map(parse_date)
    late = df["contact_date"] > pd.Timestamp("2026-05-31")
    df["window_complete"] = ~late
    log(f, "flag contacts after 31 May 2026 (30-day window not finished)", len(df), len(df),
        f"{int(late.sum())} rows flagged, excluded from lift measurement")
    return df


def run(data_dir):
    LOG.clear()
    subs = clean_subscribers(f"{data_dir}/subscribers.csv")
    tickets = clean_tickets(f"{data_dir}/support_tickets.csv", subs)
    camps = clean_campaigns(f"{data_dir}/campaigns.csv")
    contacts = clean_contacts(f"{data_dir}/campaign_contacts.csv", camps)
    copy = pd.read_csv(f"{data_dir}/campaign_copy.csv", dtype=str)
    return subs, tickets, camps, contacts, copy, pd.DataFrame(LOG)
