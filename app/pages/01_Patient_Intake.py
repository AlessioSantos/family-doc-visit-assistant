import json
import streamlit as st
from datetime import date

st.title("Patient Intake (demo)")
st.caption("Fill the form. This is a demo intake; no diagnosis is provided.")

age = st.number_input("Age (years)", min_value=0.0, max_value=120.0, value=30.0, step=1.0)
sex = st.selectbox("Sex", ["female","male","other","unknown"])

chief = st.selectbox(
    "Main reason",
    ["cough/cold (child)", "fever", "abdominal pain", "rash", "chest pain/shortness of breath (adult)", "other"]
)
started = st.date_input("When did symptoms start?", value=date.today())

st.subheader("Timeline (by dates)")
st.write("Add at least one event (date + symptom + change).")
events = st.session_state.get("events", [])
if st.button("Add event"):
    events.append({"date": str(date.today()), "symptom_type": "", "change": "appeared", "character": "", "severity": ""})
    st.session_state["events"] = events

for i, ev in enumerate(events):
    cols = st.columns(5)
    ev["date"] = str(cols[0].date_input(f"Date #{i+1}", value=date.fromisoformat(ev["date"]), key=f"d{i}"))
    ev["symptom_type"] = cols[1].text_input(f"Symptom #{i+1}", value=ev["symptom_type"], key=f"s{i}")
    ev["change"] = cols[2].selectbox(f"Change #{i+1}", ["appeared","worsened","improved","resolved"], index=0, key=f"c{i}")
    ev["character"] = cols[3].text_input(f"Character #{i+1}", value=ev.get("character",""), key=f"ch{i}")
    ev["severity"] = cols[4].text_input(f"Severity #{i+1}", value=ev.get("severity",""), key=f"sev{i}")

if not events:
    events = [{"date": str(started), "symptom_type": "unknown", "change": "appeared", "character": "", "severity": ""}]

intake = {
    "patient": {"age_years": age, "sex": sex},
    "visit": {"started_on_date": str(started), "chief_complaint_category": chief},
    "timeline": {"events": events}
}

st.subheader("Resulting Intake JSON")
st.code(json.dumps(intake, indent=2, ensure_ascii=False), language="json")

st.download_button(
    "Download intake.json",
    data=json.dumps(intake, indent=2, ensure_ascii=False),
    file_name="intake.json",
    mime="application/json"
)
