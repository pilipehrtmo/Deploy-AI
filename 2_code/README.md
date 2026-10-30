# Formosa Signal Engine

Finds Formosa customers who are about to leave by reading what they tell support agents,
matches each one to an approved offer, writes the campaign, and checks every past campaign
against the group that was held back on purpose.

**Just want the answers?** Open `4_outputs/RESULTS.xlsx` (start with the "Start here" sheet)
or `1_report/report.pdf`. You do not need to run anything.

---

## Rebuild everything (about 30 seconds)

Works with standard Python 3.10 or newer on Windows or Mac. No internet or AI model needed.

**1. Put the data in place.** Copy the case data files into `2_code/data/raw/`:
`subscribers.csv`, `support_tickets.csv`, `campaigns.csv`, `campaign_copy.csv`, `campaign_contacts.csv`.

**2. Open a terminal in the `2_code` folder.**
Windows: open the `2_code` folder in File Explorer, click the address bar, type `cmd`, press Enter.
Mac: right-click the `2_code` folder → New Terminal at Folder.

**3. Install the three libraries (once):**

```
python -m pip install -r requirements.txt
```

(On Windows, if `python` is not found, use `py` instead.)

**4. Run:**

```
python run.py
```

When it ends you see a "Headlines" table. Everything is rebuilt in `4_outputs/`, `1_report/report.html`
and `5_finals/slides.html`. To make the PDFs, open either HTML file in Chrome or Edge → Print → Save as PDF
(slides: landscape).

---

## For marketers: write a campaign from a one-line brief

```
python make_campaign.py "renewal discount by SMS for customers who mention a rival"
python make_campaign.py "data boost on LINE for wavering customers"
python make_campaign.py "roaming pass app push"
```

You get the audience size (sample and full base), the finished message with the legal footer,
and PASS/FAIL against the brand rules. The customer list is saved to `4_outputs/brief_audience.csv`.
Name one approved offer: Renewal discount, Data boost, Device credit, Plan upgrade, Data add-on, Roaming pass.

## New support notes arrived?

```
python run.py --new-notes path/to/new_notes.csv
```

The file needs the same columns as `support_tickets.csv`. Every audience is refreshed. Any sentence the
AI has never read sends that note to `4_outputs/review_queue.csv`, marked `unknown`, instead of being guessed.

---

## What is in each folder

| Folder | What it holds |
|---|---|
| `1_report/` | `report.pdf` (parts 1–6), `report.html`, `charts/` |
| `2_code/` | This README, `run.py`, `make_campaign.py`, `src/`, `requirements.txt`, `data/raw/` |
| `3_ai_outputs/` | The AI's work, saved once: `sentence_labels.csv`, `copy_templates.json`, `how_we_did_it.md` |
| `4_outputs/` | `RESULTS.xlsx` plus every table as CSV |
| `5_finals/` | `slides.pdf`, `slides.html` |

## The files in `4_outputs/`

| File | What it tells you |
|---|---|
| **RESULTS.xlsx** | All key tables, formatted, in one workbook |
| customers_clean.csv | The clean customer table |
| cleaning_log.csv | Every fix, with row counts before and after |
| notes_read.csv | Every support note: topics, leave intent (0–3), reason, rival named |
| review_queue.csv | Notes the AI has not read yet |
| backtest.csv | Each rule tested on 1 Mar, 1 Apr, 1 May 2026: who left in the next 60 days |
| segments.csv | Every customer group with its size |
| audiences_summary.csv / audience_members.csv | Who to contact, with which offer (sample and ×130 full base) |
| flagged_family_business.csv | At-risk family and business customers, for the other teams (never targeted) |
| new_campaigns.csv | Ready campaigns: who, offer, channel, timing, message, compliance |
| audit_*.csv | Past campaigns: real effect vs control group, paid channel costs, brand compliance |
| value_ranges.csv, acquisition_scenarios.csv | NT$ ranges per objective |
| pilot_scenarios.csv | The 90-day pilot: cost, customers kept, value |
| assumptions.csv | Every assumption behind the NT$ figures |

## How it works, step by step

| Step | Code | What it does |
|---|---|---|
| 1 Clean | `src/clean.py` | Removes duplicates, reads three date formats (2026-01-31, 31/01/2026, 2026年1月31日), trims spaces, flags unfinished tracking windows, logs every fix |
| 2 Read notes | `src/notes.py` | Splits each note into sentences and looks each one up in the AI labels: topic and leave intent 0–3 |
| 3 Pick customers | `src/signals.py` | Written rules put customers in tiers using only notes from the 90 days before the send date; tested on past dates |
| 4 Audit | `src/audit.py`, `src/compliance.py` | Contacted vs held-back customers, paid channel payback, brand and legal check of every past message |
| 5 Campaigns | `src/campaigns.py` | One campaign per audience and offer, legal footer added, compliance checked |
| 6 NT$ | `src/sizing.py` | Value ranges and the pilot, assumptions written down |
| 7 Report | `src/report.py` | RESULTS.xlsx, the report, the slides and the charts |

### The rules

| Tier | Rule | What we send |
|---|---|---|
| R1 leaving now | Note says cancelling, porting or signing elsewhere | Outbound call, highest bill first; matched retention offer |
| R2 wavering | Note says comparing, unsure about renewal, or will leave if X | Call if capacity, else LINE/SMS; matched retention offer |
| R3 new | Joined less than six months ago | Welcome check-in, no paid offer |
| R4 unhappy, quiet | Billing or network complaint, no leave talk | Fix the bill or network care call, no paid offer |
| Excluded | Line closing for a reason no offer changes; family, business | Nothing |

Offer match: device problem on premium → Device credit · price, rival or renewal doubt within 4 months
of contract end → Renewal discount · price or data need, not unlimited → Data boost ·
billing error → fix it (not an offer) · network → care call.
