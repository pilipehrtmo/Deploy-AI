# How we used AI

Model: Claude Opus 5.5 (Anthropic), used through the Claude app. Every AI step ran once, on our
side. Its output is saved in this folder, and the code only reads these files, so the rerun is
offline and gives the same result every time.

## Step 1: reading the support notes → `sentence_labels.csv`

1. We split all 8,000 agent notes into sentences and normalised them: bill amounts → `NT$<N>`,
   competitor names → `<RIVAL>`, trailing time words ("this week", "for now") removed.
   That leaves 403 distinct sentences.
2. Claude labelled every distinct sentence with:
   - `topic`: one of 28 topics (billing error, coverage, competitor, port out, roaming interest, ...),
     or `filler` for sentences that only describe the contact ("Customer rang the support line.").
   - `leave_intent`: 0 none, 1 considering (comparing offers, undecided about renewal),
     2 threat (says they will leave if X), 3 acting (porting code, signing elsewhere, asked to cancel).
3. The code maps each note to its sentences' labels. A sentence not in the file sends the note to
   `review_queue.csv` as `unknown`, so new notes are never guessed silently.

Why per sentence and not per note: 403 labels can be checked by a person in under an hour, and
the same sentence always gets the same label.

**Checks.** A blind hand check by two team members is set up in `hand_check/`
(sheet + `check_labels.py`); its result is added below when run. Outcome check: customers whose notes carry intent ≥ 1
left at a 49–52% rate in the next 60 days vs 3.7% for all postpaid customers (`backtest.csv`).

## Step 2: campaign copy → `copy_templates.json`

Claude wrote one headline, body, call to action and call script per approved offer, following
`brand_guidelines.md`. The code adds the legal footer (full footer, or the short terms line on
SMS and LINE only) and runs `src/compliance.py` on every draft: footer verbatim, no banned claim
or paraphrase, approved offer for the objective.
