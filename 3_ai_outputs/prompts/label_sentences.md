# Prompt: label support-note sentences

Used by `2_code/src/llm.py` (`label_sentences`) for any note sentence that is not yet in
`3_ai_outputs/sentence_labels.csv`. The same instructions produced the saved labels.
`{sentences}` is replaced by a JSON list of normalised sentences
(bill amounts → `NT$<N>`, competitor names → `<RIVAL>`).

---

You label sentences from Formosa Telecom support-agent notes. Each sentence is one line an agent
wrote after a customer contact.

For every sentence give:

1. `topic`: exactly one of the topics below.
2. `leave_intent`: how close the customer is to leaving, from this sentence alone.
   - 0 no sign of leaving
   - 1 considering: comparing offers, undecided about renewal, looking around
   - 2 threat: says they will leave if X, or plainly says they want out
   - 3 acting: porting code, signing elsewhere, asked to cancel or close now

Topics:
- `account_admin`: routine account question
- `app_login`: cannot log in to the app
- `bill_shock`: bill much higher than usual
- `billing_admin`: routine billing request (address, e-bill, explain a fee)
- `billing_error`: bill is wrong (double charge, wrong amount, wrong name)
- `cancel`: wants to cancel or asks about cancelling
- `competitor`: mentions a rival or other providers
- `coverage`: weak or no signal, dropped calls
- `data_speed`: mobile data slow
- `device_fault`: phone broken, lost or faulty
- `device_upgrade`: wants a new phone, trade-in
- `family_lines`: add or manage family lines
- `feedback`: praise or complaint about service
- `follow_up`: chasing an earlier case
- `line_closing_no_save`: line closing for a reason no offer can change (bereavement, replacement line, idle line)
- `loyalty_points`: loyalty points
- `payment_issue`: payment failed or wants instalments
- `plan_question`: question about plans or changes
- `port_out`: moving the number to another provider
- `prepaid_to_postpaid`: prepaid wants a monthly plan
- `price_value`: plan feels too expensive or poor value
- `renewal_doubt`: unsure about renewing
- `roaming_interest`: travelling, wants roaming
- `roaming_problem`: roaming bill or roaming not working
- `student`: student pricing
- `suspend_line`: pause or suspend the line
- `wants_cheaper_plan`: wants a smaller or cheaper Formosa plan
- `wants_more_data`: runs out of data, wants more
- `filler`: only describes the contact (channel, repeat contact, who called)

Rules: judge only what the sentence says; do not guess the rest of the note. A sentence that only
describes the contact itself (channel, repeat contact) is `filler` with intent 0.

Answer with JSON only, one object per sentence, in the same order:
[{"sentence": "...", "topic": "...", "leave_intent": 0}]

Sentences:
{sentences}
