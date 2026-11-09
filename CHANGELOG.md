# Changelog

## 9 Nov 2026: organizers' FAQ
- Pinned requirements (`==`) and named the tested Python (3.12.3; outputs identical on 3.13).
- Live AI step: `src/llm.py` calls Claude through the Anthropic API with the saved prompts in `3_ai_outputs/prompts/`,
  only with `--use-llm` and `ANTHROPIC_API_KEY`. The rerun stays offline; unseen sentences still go to the review queue.
- New notes files are picked up automatically when saved next to `support_tickets.csv` as `support_tickets_*.csv`.
- `run.py` saves the README brief example as `4_outputs/brief_campaign.md` and `brief_audience.csv`.
- SMS messages now open with "Formosa Telecom:" (FAQ: name Formosa Telecom in the message). No number changed.

## 9 Nov 2026: label check
- The organizers allowed AI for the hand check. Labeler A is a second Claude Opus 5.5 pass from the written definitions (same model as the first labels, so it checks consistency, not independent human agreement): 100% agreement on leave / not leave, 86% on the exact intent level, 98% on topic. All 14 intent disagreements are 1 vs 2, which keeps the customer in R2, so no audience or NT$ figure changes. Labeler B is left for a team member.

## 8 Nov 2026: two stale sentences fixed
- Assumptions: kept customers' later churn now reads the computed figure (13.7% a month, March and April cohorts pooled) instead of the old fixed text "about 12%".
- Part 4: removed "the earn-more range in Part 1 adds this saving"; roaming spend saved is shown apart from new margin, not added to it.

## 6 Nov 2026: fixes from an external review, checked against the data

| Review point | Verdict | What changed |
|---|---|---|
| Call scripts had no legal footer | **Agreed.** The brief says every message carries it. | Every call script ends with the agent reading the full footer word for word; the same compliance check now runs on calls (no exception). Same in `campaign_builder.html`. |
| Customers could get two campaigns (Vivian, answer 3) | **Agreed.** 25 customers in the sample were in two audiences. | One campaign per customer. Order: R1, R2, R4, R3, Plan upgrade, Data add-on, Roaming pass. `audience_members.csv` has unique customers (checked in code). |
| Day 45 rule could stop a winning pilot on noise | **Agreed.** Noise at day 45 is about ±3 points, more than the break-even gap. | Day 45 is now a safety check: stop paid offers only if the contacted group churns more than the held-back group by 1.5 standard errors (about 2.3 points). Otherwise run to day 90. |
| Earn-more headline mixed new margin with spend saved | **Agreed.** | Shown separately: new upsell margin, plus roaming spend that can stop. |
| SMS and LINE both charged for every customer | **Agreed** (small money, but wrong). | One message per customer: LINE where they follow Formosa, else SMS where they agreed. About 7% of non-called customers cannot be reached; only reached customers can be kept. |
| NT$60M into Google Search is unrealistic | **Agreed.** Its biggest month was NT$2.5M and cost per line rose slightly with spend. | Scenarios now move 25–100% of Retail Promotion's budget to Google Search. A 24-month column sits beside the 6-month credit. |
| Months a kept customer pays came from one cohort | **Checked.** April gives 13.9% a month, March 12.1%. | Pooled both cohorts by months at risk: 13.7% a month, about 4.3 of 6 credited months. |
| numpy missing from requirements | Agreed (pandas installs it, but list it). | Added. |
| Per-customer outputs gitignored | **Disagree, kept.** The repo is public and the case data must stay inside the team. | README explains; the Drive hand-in has every output. |
| Prepaid bills under NT$100 leak into sizing | **Checked: no.** 0 of those customers are in any audience. | None. |
| Contract end date looks ahead | Already handled: used only for the comparison rule and today's renewal eligibility, never for risk tiers. | None. |
| "Populate realistic human labels" in the hand-check sheet | **Refused.** Invented labels presented as a human check would be fabricated validation. | The sheet stays for two team members to fill; `check_labels.py` then writes the real agreement everywhere. |

Numbers after these fixes: retention NT$1.8–6.2M a year; upsell new margin NT$143–475K a year plus NT$2.0M roaming spend saved;
acquisition shift NT$155–620K a year; pilot NT$1.0M expected (at most NT$1.8M); break-even 2.6%; provable save rate 6.2%+.

## 5 Nov 2026: Vivian's round 2 answers
Credit stops if a kept customer cancels; two-part call charge (NT$2 per dial + NT$25 per conversation); 20% planning save rate;
one offer per customer; prepaid may take Data add-on and Roaming pass; daily notes file; 10/20/30% holdout options; 24-month view.

## 30 Oct 2026: first full hand-in
Pipeline, report, slides, RESULTS.xlsx, campaign builder, talk script, pandas 3 fix, hand-check kit.
