# Demo script (for reviewers)

This repository contains **synthetic demo cases only**. Do NOT use real patient data.

## Goal (what to look for)
The demo shows an end-to-end workflow:
- structured intake JSON (timeline by dates, measurements, optional attachments)
- model generates a **schema-validated Output JSON**
- output contains: summary, draft note, missing info, follow-up questions
- strict safety: **no diagnosis / no treatment / no dosing**

---

## Prerequisites (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `.env` in the project root:

```env
MODEL_PROVIDER=transformers
MODEL_ID=google/medgemma-1.5-4b-it
MAX_NEW_TOKENS=2000
RETRIES=3
HF_TOKEN=hf_...   # or HUGGINGFACE_HUB_TOKEN=hf_...
```

---

## One-command demo (recommended)

```powershell
python scripts/run_demo.py
```

What this does:
- reads `data_demo/cases/*.json`
- generates `data_demo/outputs/output_*.json`
- validates outputs against `schemas/output.schema.json`
- writes a report: `data_demo/demo_report.md` (and `.json`)
- saves raw model text + prompts in `data_demo/raw/`

Key files to inspect:
- `data_demo/demo_report.md`
- `data_demo/outputs/output_case_*.json`

---

## Optional: run the UI

```powershell
streamlit run app/Home.py
```

---

## Safety notes

- The system prompt enforces: output-only JSON, no diagnosis, no treatment, no dosing.
- Missing details are marked as `"unknown"` and asked via follow-up questions.
- Human review is required: outputs are documentation drafts only.