# Data Contract (Schemas)

This folder defines the **JSON contract** between the intake payload and the generated clinical documentation output.

See the project root `README.md` for how to run the demo runner and validate outputs.

---

## Files

- `intake.schema.json` — schema for the **patient/parent intake JSON**
- `output.schema.json` — schema for the **assistant Output JSON** (what the model must produce)

---

## Demo validation

The demo runner validates model outputs against the Output schema:

```powershell
python scripts/run_demo.py
```

---

## Practical rules (v1)

- Timeline is **by dates** (required).
- If `chief_complaint_category = fever` → `measurements.temperature` is required.
- If `chief_complaint_category = chest_pain_sob` → adult triage module is required (see schema).
- Output must include `safety.no_diagnosis_or_treatment = true`.

If a required detail is missing in the intake, the assistant must use `"unknown"` and ask a focused follow-up question.
