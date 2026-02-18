import json
from pathlib import Path

import streamlit as st
import pandas as pd
from jsonschema import validate
from jsonschema.exceptions import ValidationError

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # корень проекта
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.generator import generate_output


BASE = Path(__file__).resolve().parents[2]
INTAKE_SCHEMA_PATH = BASE / "schemas" / "intake.schema.json"
OUTPUT_SCHEMA_PATH = BASE / "schemas" / "output.schema.json"


def safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def load_json_schema(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_exists(uri: str) -> bool:
    try:
        return Path(uri).exists()
    except Exception:
        return False


st.title("Doctor Dashboard (MVP)")

INTAKE_SCHEMA = load_json_schema(INTAKE_SCHEMA_PATH)
OUTPUT_SCHEMA = load_json_schema(OUTPUT_SCHEMA_PATH)

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

st.divider()

age = safe_get(intake, "patient", "age_years", default="unknown")
sex = safe_get(intake, "patient", "sex", default="unknown")
chief = safe_get(intake, "visit", "chief_complaint_category", default="unknown")
started = safe_get(intake, "visit", "started_on_date", default="unknown")
today = safe_get(intake, "visit", "today_date", default="unknown")
free = safe_get(intake, "visit", "chief_complaint_free_text", default=None)

c1, c2, c3 = st.columns(3)
c1.metric("Age", age)
c2.metric("Sex", sex)
c3.metric("Chief complaint", chief)
st.write(f"**Start:** {started}   |   **Today:** {today}")
if free:
    st.write(f"**Short note:** {free}")

st.divider()

risk_level = safe_get(intake, "risk_flags_rule_based", "risk_level", default="LOW")
risk_flags = safe_get(intake, "risk_flags_rule_based", "flags", default=[])

if risk_level == "HIGH":
    st.error(f"HIGH RISK (rule-based): {', '.join(risk_flags) if risk_flags else 'flags present'}")
elif risk_level == "MED":
    st.warning(f"MED RISK (rule-based): {', '.join(risk_flags) if risk_flags else 'flags present'}")
else:
    st.success("LOW RISK (rule-based)")

st.divider()

st.subheader("Timeline (by dates)")
events = safe_get(intake, "timeline", "events", default=[])
if events:
    df_tl = pd.DataFrame(events).copy()
    if "date" in df_tl.columns:
        df_tl["date"] = pd.to_datetime(df_tl["date"], errors="coerce")
        df_tl = df_tl.sort_values("date")
        df_tl["date"] = df_tl["date"].dt.date.astype(str)
    st.dataframe(df_tl, use_container_width=True)
else:
    st.info("No timeline events.")

st.divider()

st.subheader("Temperature graph")
temp_graph = safe_get(intake, "measurements", "temperature", "graph", default=[])
if temp_graph:
    df_temp = pd.DataFrame(temp_graph).copy()
    df_temp["date"] = pd.to_datetime(df_temp["date"], errors="coerce")
    order = {"morning": 0, "day": 1, "evening": 2, "night": 3}
    df_temp["tod_order"] = df_temp["time_of_day"].map(order).fillna(99).astype(int)
    df_temp = df_temp.sort_values(["date", "tod_order"])
    df_temp["label"] = df_temp["date"].dt.strftime("%Y-%m-%d") + " " + df_temp["time_of_day"]

    st.dataframe(df_temp[["label", "value_c", "antipyretic_taken"]], use_container_width=True)
    chart_df = df_temp.set_index("label")[["value_c"]]
    st.line_chart(chart_df)
else:
    st.info("No temperature data.")

st.divider()

st.subheader("Attachments")
atts = safe_get(intake, "attachments", default=[]) or []
if not atts:
    st.info("No attachments.")
else:
    for a in atts:
        a_type = a.get("type")
        uri = a.get("uri")
        label = a.get("label") or a.get("file_name") or a_type

        st.write(f"**{a_type}** — {label}")
        if not uri or not file_exists(uri):
            st.warning("File not found (uri missing or path not accessible).")
            continue

        p = Path(uri)
        if a_type == "audio_cough":
            st.audio(p.read_bytes())
        elif a_type == "photo_rash":
            st.image(str(p), caption=label, use_container_width=True)
        else:
            st.write(f"Stored at: {uri}")

st.divider()

st.subheader("Generate Output (MedGemma)")
st.caption("Default=stub. For real model: set MODEL_PROVIDER=transformers + MODEL_ID in .env.")

if st.button("Generate output.json"):
    with st.spinner("Generating..."):
        try:
            out, raw = generate_output(
                intake=intake,
                output_schema=OUTPUT_SCHEMA,
                risk_level=risk_level,
                risk_flags=risk_flags,
                prompts_dir=str(BASE / "prompts")
            )
            st.success("Generated output.json (schema-valid).")
            st.code(json.dumps(out, indent=2, ensure_ascii=False), language="json")
            st.download_button(
                "Download output.json",
                data=json.dumps(out, indent=2, ensure_ascii=False),
                file_name="output.json",
                mime="application/json",
            )
            with st.expander("Raw model text"):
                st.text(raw)
        except Exception as e:
            st.error(str(e))

with st.expander("Raw Intake JSON"):
    st.code(json.dumps(intake, indent=2, ensure_ascii=False), language="json")
