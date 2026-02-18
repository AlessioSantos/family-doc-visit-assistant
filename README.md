# Family Doctor Visit Assistant (MVP)

**Goal:** Reduce documentation burden and non‑specific patient narratives by collecting **structured pre‑visit data**
(timeline by dates, temperature graph, optional cough audio / rash photo) and generating:

- a **short clinician summary**,
- a **draft note** ready to copy into the clinic system,
- a short list of **missing info / follow‑up questions**.

**Safety:** This is a workflow assistant. It does **not** provide diagnosis or treatment. Outputs must be reviewed by a clinician.

## Quick start (local)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app/Home.py
```

## Structure

- `app/` Streamlit multipage app (patient intake + doctor dashboard)
- `schemas/` JSON Schemas for Intake and Output payloads
- `prompts/` prompt templates (MedGemma JSON-first)
- `data_demo/` synthetic demo cases (no real patient data)
- `scripts/` helpers (validation, synthetic case generation)
- `docs/` screenshots + demo script

## License
MIT
