# DeployAI 2026 · Formosa Telecom case

Formosa Signal Engine: finds customers about to leave by reading what they tell support,
matches them to approved offers, writes compliant campaigns, and measures past campaigns
against their held-back control group.

| Folder | What it holds |
|---|---|
| [`1_report/`](1_report/) | `report.pdf`: parts 1–6, executive summary first |
| [`2_code/`](2_code/) | Code and the **[README to run it](2_code/README.md)** |
| [`3_ai_outputs/`](3_ai_outputs/) | Every AI output, and `how_we_did_it.md` |
| [`4_outputs/`](4_outputs/) | `RESULTS.xlsx` and the aggregate result tables |
| [`5_finals/`](5_finals/) | `slides.pdf`: the six finals slides |

Quick start: put the case data files in `2_code/data/raw/`, then in `2_code/` run
`python -m pip install -r requirements.txt` and `python run.py`.

The case data and per-customer outputs are not committed: the case rules keep the data inside the team.
`python run.py` rebuilds them from the raw files.
