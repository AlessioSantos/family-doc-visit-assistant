TASK:
Given Intake JSON, generate Output JSON with fields:
- summary: max 10 lines
- draft_note: copy/paste-ready note (facts only)
- missing_info: 0-5 items
- followup_questions: 0-5 items
- safety: must include {"no_diagnosis_or_treatment": true}

RULES:
- Do NOT include diagnosis or treatment.
- Use "unknown" when data is missing.
- risk_level and risk_flags are PROVIDED separately; do NOT invent or change them.

INPUTS:
risk_level: {{RISK_LEVEL}}
risk_flags: {{RISK_FLAGS}}

Intake JSON:
{{INTAKE_JSON}}
