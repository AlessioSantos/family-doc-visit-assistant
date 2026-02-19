# Synthetic Demo Data

This folder contains **synthetic demo cases only**.  
Do NOT store or add real patient data here.

---

## What’s inside

- `cases/` — synthetic intake examples (`*.json`)
- `assets/` — demo attachments (e.g., placeholder rash photo)
- (generated locally, ignored by git)
  - `outputs/` — `output_*.json`
  - `raw/` — `raw_*.txt` and `prompt_*.txt`
  - `demo_report.json` / `demo_report.md` — run reports

---

## Run the demo

From the project root:

```powershell
python scripts/run_demo.py
```

This will process all cases in `data_demo/cases/`, generate outputs, validate them against `schemas/output.schema.json`, and write a report.
