# Family Doc Visit Assistant (MVP)

Synthetic demo cases only. Do NOT store real patient data.

This project reduces documentation burden in family medicine (adults + children) by:
- collecting **structured pre-visit intake** (timeline by dates, temperature graph, optional cough audio / rash photo),
- generating a **structured Output JSON** (validated by schema) with:
  - a short clinician summary,
  - a draft note (copy-ready),
  - missing info + follow-up questions.

**Safety scope:** no diagnosis, no treatment recommendations, no medication dosing. Outputs require clinician review.

---

## What’s in this repo

- `app/` — Streamlit app (patient intake + doctor dashboard)
- `schemas/` — JSON Schemas for Intake and Output
- `prompts/` — prompt templates (JSON-first)
- `data_demo/` — synthetic demo cases (no real patient data)
- `scripts/run_demo.py` — one-command demo runner (generate + validate + report)

---

## Quick start (Windows)

### 1) Create venv & install deps
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Create `.env`
Create a file named `.env` in the project root:

```env
MODEL_PROVIDER=transformers
MODEL_ID=google/medgemma-1.5-4b-it
MAX_NEW_TOKENS=2000
RETRIES=3

# Hugging Face token (use ONE of these)
HF_TOKEN=hf_...
# or:
HUGGINGFACE_HUB_TOKEN=hf_...

# Optional (debug): save last prompt
SAVE_LAST_PROMPT=1
```

---

## Demo (one command)

Runs all synthetic demo cases end-to-end:
- reads `data_demo/cases/*.json`
- generates `data_demo/outputs/output_*.json`
- validates against `schemas/output.schema.json`
- writes a run report

```powershell
python scripts/run_demo.py
```

Generated artifacts are written locally (and ignored by git):
- `data_demo/outputs/`
- `data_demo/raw/`
- `data_demo/demo_report.json`
- `data_demo/demo_report.md`

---

## Run the UI (optional)

```powershell
streamlit run app/Home.py
```

---

## Safety & limitations

- No diagnosis / no treatment plan / no dosing.
- No invented facts: missing details are marked as `"unknown"` and asked as follow-up questions.
- Human review required: outputs are drafts for documentation only.

## Why this exists (real-world validation)

This MVP was shaped by a short questionnaire study with practicing physicians in Poland.
Their answers highlighted the same pain points: routine documentation, bureaucracy, and time taken away from patient care.
Based on those responses, the assistant was designed to structure pre-visit narratives and reduce “free-text noise” in clinical notes.

## Survey notes

A short, anonymized summary of the questionnaire study (Poland) and how it shaped the MVP:
- `docs/survey.md`

## License
MIT
