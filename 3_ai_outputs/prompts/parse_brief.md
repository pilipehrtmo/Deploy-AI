# Prompt: read a marketer's brief

Used by `2_code/make_campaign.py --use-llm`. `{brief}` is replaced by the marketer's text.
Without `--use-llm` (and in the rerun) the same fields are read by simple keyword rules.

---

A Formosa Telecom marketer wrote a one-line campaign brief. Turn it into these fields.

- `offer`: exactly one of: Renewal discount, Data boost, Device credit, Plan upgrade, Data add-on,
  Roaming pass. If the brief names no approved offer, use null.
- `channel`: one of SMS, LINE, Email, App Push, Outbound Call. Default SMS.
- `reason`: the customer reason the brief targets, one of price, contract, billing, network,
  device, data_need, or "" for any.
- `tier`: one of R1_leaving_now, R2_wavering, R3_new_and_fragile, R4_unhappy_quiet, or null for any.

Never invent an offer, discount or price. Answer with JSON only:
{"offer": "...", "channel": "...", "reason": "...", "tier": null}

Brief:
{brief}
