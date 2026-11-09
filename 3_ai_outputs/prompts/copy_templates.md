# Prompt: campaign copy (run once, saved as `copy_templates.json`)

Run once in the Claude app with `brand_guidelines.md` and the approved offer list attached.
The output is saved in `3_ai_outputs/copy_templates.json`; the code fills in the reason, adds the
legal footer and checks every draft with `src/compliance.py`. It is not called in the rerun.

---

Write one campaign template for each approved Formosa Telecom offer: Renewal discount, Data boost,
Device credit, Plan upgrade, Data add-on, Roaming pass. Follow the attached brand guide exactly.

For each offer give `headline`, `body`, `cta` and `call_script`. The call script may contain
`{reason_text}`, which the code replaces with the customer's reason (for example "their bill
looked wrong"). Name Formosa Telecom, state only the offer's approved terms and value, use NT$,
write in English, no banned claims, no more than one exclamation mark, no private customer details.
Do not write the legal footer: the code adds it.

Answer with JSON only: {"<offer>": {"headline": "...", "body": "...", "cta": "...", "call_script": "..."}}
