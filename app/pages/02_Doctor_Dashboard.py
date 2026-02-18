import json
import streamlit as st
from pathlib import Path
from jsonschema import validate
from jsonschema.exceptions import ValidationError

BASE = Path(__file__).resolve().parents[2]
INTAKE_SCHEMA = json.loads((BASE / "schemas" / "intake.schema.json").read_text(encoding="utf-8"))

st.title("Doctor Dashboard (demo)")

uploaded = st.file_uploader("Upload intake.json", type=["json"])
if not uploaded:
    st.info("Upload an intake.json (download one on the Patient Intake page).")
    st.stop()

intake = json.loads(uploaded.read().decode("utf-8"))

try:
    validate(instance=intake, schema=INTAKE_SCHEMA)
    st.success("Intake JSON is valid.")
except ValidationError as e:
    st.error(f"Intake JSON is invalid: {e.message}")

st.subheader("Intake JSON")
st.code(json.dumps(intake, indent=2, ensure_ascii=False), language="json")

st.divider()
st.subheader("Generate Output (placeholder)")

st.warning("Placeholder: next step is connecting MedGemma and enforcing JSON-only output.")

output = {
    "summary": f"Demo summary (placeholder)\n- Timeline events: {len(intake.get('timeline', {}).get('events', []))}",
    "draft_note": "Draft note (placeholder).\n\n1) Timeline...\n2) Temperature...\n3) Next questions...",
    "missing_info": ["If fever suspected: please add temperature measurements (graph)."],
    "risk_level": "LOW",
    "risk_flags": []
}

st.code(json.dumps(output, indent=2, ensure_ascii=False), language="json")

st.download_button(
    "Download output.json",
    data=json.dumps(output, indent=2, ensure_ascii=False),
    file_name="output.json",
    mime="application/json"
)
