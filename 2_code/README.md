# Formosa Signal Engine

Code repository: https://github.com/pilipehrtmo/Deploy-AI

Finds Formosa customers who are about to leave by reading what they tell support agents,
matches each one to an approved offer, writes the campaign, and checks every past campaign
against the group that was held back on purpose.

**Just want the answers?** Open `4_outputs/RESULTS.xlsx` (start with the "Start here" sheet)
or `1_report/report.pdf`. You do not need to run anything.

---

## Rebuild everything (about 30 seconds)

Tested on **Python 3.12.3** (also runs on 3.10–3.13) on Windows or Mac, with the pinned versions in
`requirements.txt`. The rerun needs no internet and no AI model: it reads the saved AI outputs.

**1. Put the data in place.** The data pack is not included. Copy its files into `2_code/data/raw/`
(or keep them anywhere and run `python run.py --data path/to/folder`):
`subscribers.csv`, `support_tickets.csv`, `campaigns.csv`, `campaign_copy.csv`, `campaign_contacts.csv`.

**2. Open a terminal in the `2_code` folder.**
Windows: open the `2_code` folder in File Explorer, click the address bar, type `cmd`, press Enter.
Mac: right-click the `2_code` folder → New Terminal at Folder.

**3. Install the libraries (once, pinned versions):**

```
python -m pip install -r requirements.txt
```

(On Windows, if `python` is not found, use `py` instead.)

**4. Run:**

```
python run.py
```

When it ends you see a "Headlines" table. Everything is rebuilt in `4_outputs/` (every table, RESULTS.xlsx,
the campaign builder and the brief example), plus `1_report/report.html` and `5_finals/slides.html`.
Our `report.pdf` and `slides.pdf` are our own written work and are not rebuilt by code. To make the PDFs, open either HTML file in Chrome or Edge → Print → Save as PDF
(slides: landscape).

---

## On GitHub: why some outputs are missing

The GitHub copy leaves out the case data and the five per-customer tables (`customers_clean.csv`, `notes_read.csv`,
`audience_members.csv`, `flagged_family_business.csv`, `review_queue.csv`), because the case rules keep the data inside
the team. The Drive hand-in has all of them. From a GitHub clone, put the data in `data/raw/` and run `python run.py`
first; `make_campaign.py` then works.

## For marketers: the campaign builder (no install needed)

Double-click `4_outputs/campaign_builder.html`. Pick an offer, a channel, who, and the reason in their note: you get the audience size, the finished message with the legal footer, and a PASS/FAIL brand check, with a button to copy the message.

## Or from the terminal: write a campaign from a one-line brief

**Brief format:** one line of plain English that names one approved offer, plus optionally a channel
(SMS, LINE, email, app push, call), a reason (rival, price, renewal, bill, signal, phone, data) and a tier
(leaving, wavering, new, unhappy). Example and the campaign it made: `4_outputs/brief_campaign.md`.

```
python make_campaign.py "renewal discount by SMS for customers who mention a rival"
python make_campaign.py "data boost on LINE for wavering customers"
python make_campaign.py "roaming pass app push"
```

You get the audience size (sample and full base), the finished message with the legal footer,
and PASS/FAIL against the brand rules. Everything is saved to `4_outputs/brief_campaign.md` and the customer list to `4_outputs/brief_audience.csv`.
`python run.py` also runs the first example, so those two files always hold the campaign made from it.
Name one approved offer: Renewal discount, Data boost, Device credit, Plan upgrade, Data add-on, Roaming pass.

## New support notes arrived?

Put the new file **next to `support_tickets.csv`** in the data folder, named `support_tickets_<anything>.csv`
(for example `support_tickets_2026-07-02.csv`): same columns, only the added notes. Then run `python run.py`
as usual; every `support_tickets_*.csv` there is added automatically. A file elsewhere also works:

```
python run.py --new-notes path/to/new_notes.csv
```

Every audience is refreshed. Any note sentence the AI has not read yet sends that note to
`4_outputs/review_queue.csv`, marked `unknown`, instead of being guessed.

## The AI step in real use (switch it on with a key)

In real use the pipeline calls Claude through the Anthropic API to read new notes and briefs.
The rerun leaves that call out and reads what the AI produced once, saved in `3_ai_outputs/`.

| AI step | Prompt | Saved output (read in the rerun) | Code |
|---|---|---|---|
| Label each note sentence: topic + leave intent 0–3 | `3_ai_outputs/prompts/label_sentences.md` | `sentence_labels.csv` | `src/llm.py`, `src/notes.py` |
| Write the message for each approved offer | `3_ai_outputs/prompts/copy_templates.md` | `copy_templates.json` | `src/campaigns.py` |
| Read a marketer's brief | `3_ai_outputs/prompts/parse_brief.md` | `4_outputs/brief_campaign.md` (example) | `make_campaign.py` |

To switch it on:

```
set ANTHROPIC_API_KEY=sk-ant-...        (Mac/Linux: export ANTHROPIC_API_KEY=sk-ant-...)
python run.py --use-llm
python make_campaign.py --use-llm "renewal discount by SMS for customers who mention a rival"
```

With `--use-llm`, every sentence in the review queue is sent to Claude (model `claude-opus-5-5`, temperature 0;
change it with `FORMOSA_MODEL`). Answers with an unknown topic or level are rejected and stay in the queue. Valid
labels are added to `sentence_labels.csv`, so the next run reads them offline. The call uses only the Python
standard library. Without a key, or without `--use-llm`, nothing is sent anywhere.

## Checking the AI labels

Done for this hand-in: a second Claude pass relabelled 100 sentences (all 75 the AI marked as leave intent plus
25 random others) from the written definitions. Results are in `3_ai_outputs/how_we_did_it.md` and
`3_ai_outputs/hand_check/`. A team member can still fill the Labeler B sheet of `hand_check_sheet.xlsx`
and run `python check_labels.py`, then `python run.py`.

---

## What is in each folder

| Folder | What it holds |
|---|---|
| `1_report/` | `report.pdf` (parts 1–6, our written report); `report.html` and `charts/` are written when you run |
| `2_code/` | This README, `run.py`, `make_campaign.py`, `src/`, `requirements.txt`, `src/llm.py` (live AI step); the data pack goes in `data/raw/` (not included) |
| `3_ai_outputs/` | The AI's work, saved once: `sentence_labels.csv`, `copy_templates.json`, `prompts/`, `hand_check/`, `how_we_did_it.md` |
| `4_outputs/` | `RESULTS.xlsx` plus every table as CSV |
| `5_finals/` | `slides.pdf`; `slides.html` and `talk_script.md` (8-minute script + hard Q&A) are written when you run |

## The files in `4_outputs/`

| File | What it tells you |
|---|---|
| **RESULTS.xlsx** | All key tables, formatted, in one workbook |
| **campaign_builder.html** | Clickable campaign builder for marketers |
| brief_campaign.md / brief_audience.csv | The campaign `make_campaign.py` made from the README example brief |
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
| 7 Report | `src/report.py` | RESULTS.xlsx, the report, slides, talk script, campaign builder and charts |

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
