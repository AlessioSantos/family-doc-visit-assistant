Return ONLY the JSON below. Keep the same keys. Fill values using ONLY the Intake JSON. Use "unknown" if missing.
Do NOT add any text outside JSON.

{
  "summary": "",
  "draft_note": "",
  "missing_info": [],
  "followup_questions": [],
  "risk_level": "{{RISK_LEVEL}}",
  "risk_flags": {{RISK_FLAGS}},
  "safety": {"no_diagnosis_or_treatment": true, "notes": ["Human-in-the-loop: clinician must verify."]},
  "provenance": {"model_family": "transformers", "model_variant": "", "prompt_version": "step5", "generated_at": ""}
}

Intake JSON:
{{INTAKE_JSON}}