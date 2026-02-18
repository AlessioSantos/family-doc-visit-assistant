# Data contract (v1)

Copy into your repo:

- `schemas/intake.schema.json`
- `schemas/output.schema.json`

Demo cases (synthetic):

- `data_demo/cases/case_child_cough.json`
- `data_demo/cases/case_adult_chest_pain.json`

Rules:
- Timeline is **by dates** (required).
- If `chief_complaint_category = fever` → `measurements.temperature` required.
- If `chief_complaint_category = chest_pain_sob` → `modules.triage_adult` required.
- Model output must include `safety.no_diagnosis_or_treatment = true`.
