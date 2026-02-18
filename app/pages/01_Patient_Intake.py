import json
import uuid
from pathlib import Path
from datetime import date, datetime, timezone

import streamlit as st


# ---------- helpers ----------
UPLOAD_DIR = Path("uploads")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_session_defaults():
    st.session_state.setdefault("timeline_events", [])
    st.session_state.setdefault("temp_rows", [])
    st.session_state.setdefault("attachments", [])


def save_upload(uploaded_file, prefix: str) -> dict:
    """Save uploaded file to uploads/ and return attachment object for Intake JSON."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    folder = UPLOAD_DIR / stamp
    folder.mkdir(parents=True, exist_ok=True)

    safe_name = uploaded_file.name.replace("/", "_").replace("\\", "_")
    fname = f"{prefix}_{uuid.uuid4().hex}_{safe_name}"
    path = folder / fname

    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return {
        "type": prefix,  # must match schema enum ("audio_cough" / "photo_rash" / "other")
        "label": None,
        "file_name": safe_name,
        "mime_type": uploaded_file.type,
        "uri": str(path).replace("\\", "/"),
    }


def add_missing(missing: list, msg: str):
    if msg not in missing:
        missing.append(msg)


# ---------- UI ----------
st.title("Patient Intake (MVP) — Family doctor (child + adult)")
st.caption("Zbieramy fakty (daty, chronologia, pomiary). Bez diagnozy i leczenia.")

ensure_session_defaults()

# META
with st.expander("Meta (optional)", expanded=False):
    lang = st.selectbox("Language / Język", ["pl", "ru", "uk", "en", "mixed"], index=0)
    source = st.selectbox("Who fills this form?", ["patient", "parent", "caregiver", "staff", "unknown"], index=0)

# PATIENT
st.subheader("1) Patient / Pacjent")
age = st.number_input("Age (years)", min_value=0.0, max_value=120.0, value=30.0, step=1.0)
sex = st.selectbox("Sex", ["female", "male", "other", "unknown"], index=3)
weight_kg = st.number_input("Weight (kg) — optional", min_value=0.0, max_value=300.0, value=0.0, step=0.5)
weight_kg_val = None if weight_kg == 0 else float(weight_kg)
is_child = True if age < 18 else False

# VISIT
st.subheader("2) Visit / Wizyta")
today = st.date_input("Today date / Data", value=date.today())
started = st.date_input("When did symptoms start? / Początek objawów", value=date.today())

chief = st.selectbox(
    "Main reason / Główna skarga",
    [
        "cough_cold",
        "fever",
        "abdominal_pain",
        "rash",
        "chest_pain_sob",
        "other",
    ],
)
chief_free = st.text_area("Short description (optional)", max_chars=400)

first_follow = st.selectbox("First visit or follow-up?", ["first", "followup"], index=0)

st.divider()

# TIMELINE
st.subheader("3) Timeline by dates / Chronologia po datach")
st.write("Dodaj zdarzenia: **data + objaw + co się zmieniło**. Minimum 1 wpis.")

if st.button("➕ Add timeline event"):
    st.session_state["timeline_events"].append(
        {
            "date": str(started),
            "symptom_type": "other",
            "change": "appeared",
            "character": None,
            "severity": "unknown",
            "notes": None,
        }
    )

symptom_options = [
    "cough",
    "runny_nose",
    "sore_throat",
    "fever",
    "abdominal_pain",
    "vomiting",
    "diarrhea",
    "rash",
    "chest_pain",
    "shortness_of_breath",
    "fatigue",
    "dizziness",
    "other",
]

for i, ev in enumerate(st.session_state["timeline_events"]):
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        ev["date"] = str(c1.date_input(f"Date #{i+1}", value=date.fromisoformat(ev["date"]), key=f"tl_date_{i}"))
        ev["symptom_type"] = c2.selectbox(
            f"Symptom #{i+1}", symptom_options, index=symptom_options.index(ev["symptom_type"]), key=f"tl_sym_{i}"
        )
        ev["change"] = c3.selectbox(
            f"Change #{i+1}", ["appeared", "worsened", "improved", "resolved"],
            index=["appeared","worsened","improved","resolved"].index(ev["change"]),
            key=f"tl_chg_{i}"
        )
        c4, c5 = st.columns(2)
        ev["severity"] = c4.selectbox(
            f"Severity #{i+1}", ["mild", "moderate", "severe", "unknown"],
            index=["mild","moderate","severe","unknown"].index(ev["severity"] or "unknown"),
            key=f"tl_sev_{i}"
        )
        ev["character"] = c5.text_input(f"Character (optional) #{i+1}", value=ev.get("character") or "", key=f"tl_char_{i}") or None
        ev["notes"] = st.text_area(f"Notes (optional) #{i+1}", value=ev.get("notes") or "", key=f"tl_notes_{i}") or None

        if st.button("🗑 Remove this event", key=f"tl_del_{i}"):
            st.session_state["timeline_events"].pop(i)
            st.rerun()

st.divider()

# TEMPERATURE (required for fever)
st.subheader("4) Temperature graph / Wykres temperatury")
show_temp = (chief == "fever") or st.toggle("Add temperature section (optional)", value=(chief == "fever"))

if show_temp:
    st.write("Wpisz pomiary: data + pora dnia + wartość. (Rano/Dzień/Wieczór/Noc)")
    if st.button("➕ Add temperature row"):
        st.session_state["temp_rows"].append(
            {"date": str(today), "time_of_day": "morning", "value_c": 37.0, "antipyretic_taken": "unknown"}
        )

    for i, tr in enumerate(st.session_state["temp_rows"]):
        with st.container(border=True):
            a, b, c, d = st.columns(4)
            tr["date"] = str(a.date_input(f"Date T#{i+1}", value=date.fromisoformat(tr["date"]), key=f"t_date_{i}"))
            tr["time_of_day"] = b.selectbox(
                f"Time T#{i+1}", ["morning", "day", "evening", "night"],
                index=["morning","day","evening","night"].index(tr["time_of_day"]),
                key=f"t_time_{i}"
            )
            tr["value_c"] = float(c.number_input(f"Value °C T#{i+1}", min_value=30.0, max_value=45.0, value=float(tr["value_c"]), step=0.1, key=f"t_val_{i}"))
            tr["antipyretic_taken"] = d.selectbox(
                f"Antipyretic? T#{i+1}", ["yes", "no", "unknown"],
                index=["yes","no","unknown"].index(tr["antipyretic_taken"]),
                key=f"t_ant_{i}"
            )
            if st.button("🗑 Remove temp row", key=f"t_del_{i}"):
                st.session_state["temp_rows"].pop(i)
                st.rerun()

st.divider()

# MODULES (tree by chief)
st.subheader("5) Quick details (tree) / Szczegóły (drzewko)")

modules = {}

if chief == "cough_cold":
    st.markdown("**Respiratory / Oddechowe**")
    cough_present = st.checkbox("Cough present? / Kaszel?", value=True)
    cough_type = st.selectbox("Cough type / Jaki kaszel?", ["dry", "wet", "paroxysmal", "night_worse", "unknown"], index=0)
    rn_present = st.checkbox("Runny nose? / Katar?", value=True)
    rn_type = st.selectbox("Runny nose type / Jaki katar?", ["watery", "thick", "congestion_only", "unknown"], index=0)
    bd = st.selectbox("Breathing difficulty / Duszność?", ["no", "mild", "moderate", "severe", "unknown"], index=0)

    modules["respiratory"] = {
        "cough_present": cough_present,
        "cough_type": cough_type,
        "runny_nose_present": rn_present,
        "runny_nose_type": rn_type,
        "breathing_difficulty": bd,
    }

elif chief == "rash":
    st.markdown("**Rash / Wysypka**")
    rash_present = st.checkbox("Rash present?", value=True)
    loc = st.multiselect(
        "Where is rash? / Gdzie?", ["face", "trunk", "arms", "legs", "hands", "feet", "genital", "other"]
    )
    appearance = st.selectbox("Appearance / Wygląd", ["spots", "dots", "hives", "blisters", "other", "unknown"], index=0)
    itching = st.selectbox("Itching / Swędzi?", ["yes", "no", "unknown"], index=2)

    modules["rash"] = {
        "rash_present": rash_present,
        "location": loc,
        "appearance": appearance,
        "itching": itching,
    }

elif chief == "abdominal_pain":
    st.markdown("**Abdominal pain / Ból brzucha**")
    pain_present = st.checkbox("Pain present?", value=True)
    zone = st.selectbox("Location 3x3 / Lokalizacja", ["UL","UM","UR","ML","MM","MR","LL","LM","LR"], index=4)
    pain_type = st.selectbox("Pain type / Rodzaj bólu", ["cramping", "stabbing", "pulling", "burning", "other", "unknown"], index=0)
    v = st.selectbox("Vomiting? / Wymioty?", ["yes", "no", "unknown"], index=2)
    d = st.selectbox("Diarrhea? / Biegunka?", ["yes", "no", "unknown"], index=2)
    c = st.selectbox("Constipation? / Zaparcie?", ["yes", "no", "unknown"], index=2)

    modules["abdominal_pain"] = {
        "pain_present": pain_present,
        "location_zone_3x3": zone,
        "pain_type": pain_type,
        "associated": {"vomiting": v, "diarrhea": d, "constipation": c},
    }

elif chief == "chest_pain_sob":
    st.markdown("**Adult triage (rule-based) / Triage dorosłych (reguły)**")
    chest_pain_now = st.checkbox("Chest pain now? / Ból w klatce teraz?", value=True)
    sob_rest = st.checkbox("Shortness of breath at rest? / Duszność w spoczynku?", value=True)
    syncope = st.checkbox("Fainting/syncope? / Omdlenie?", value=False)
    cold_sweat = st.checkbox("Cold sweat / very pale? / Zimny pot / bladość?", value=True)
    radiates = st.checkbox("Pain radiates to arm/jaw? / Promieniuje do ręki/szczęki?", value=True)
    duration = st.number_input("Duration (minutes) / Czas (min)", min_value=0, max_value=1440, value=30, step=1)

    rf = st.multiselect(
        "Risk factors (optional)",
        ["known_heart_disease", "hypertension", "diabetes", "smoking", "high_cholesterol", "family_history", "none", "unknown"],
        default=["hypertension"]
    )

    modules["triage_adult"] = {
        "chest_pain_now": chest_pain_now,
        "shortness_of_breath_rest": sob_rest,
        "fainting_or_syncope": syncope,
        "cold_sweat_or_pale": cold_sweat,
        "pain_radiates_arm_jaw": radiates,
        "duration_minutes": int(duration),
        "risk_factors": rf,
    }

st.divider()

# HISTORY
st.subheader("6) Background / Wywiad")
chronic = st.text_area("Chronic conditions (comma-separated) / Choroby przewlekłe", value="")
allergies = st.text_area("Allergies (comma-separated) / Alergie", value="")
meds = st.text_area("Current meds/supplements (comma-separated)", value="")

history = {
    "chronic_conditions": [x.strip() for x in chronic.split(",") if x.strip()],
    "allergies": [x.strip() for x in allergies.split(",") if x.strip()],
    "current_meds_supplements": [x.strip() for x in meds.split(",") if x.strip()],
}

st.divider()

# ATTACHMENTS
st.subheader("7) Attachments / Załączniki (opcjonalnie)")
attachments = []

if chief == "cough_cold":
    up_audio = st.file_uploader("Upload cough audio (10–20 sec) / Nagraj kaszel", type=["m4a","mp3","wav","ogg"])
    if up_audio is not None:
        att = save_upload(up_audio, "audio_cough")
        att["label"] = "cough_audio"
        attachments.append(att)

if chief == "rash":
    up_photo = st.file_uploader("Upload rash photo / Zdjęcie wysypki", type=["jpg","jpeg","png","webp"])
    if up_photo is not None:
        att = save_upload(up_photo, "photo_rash")
        att["label"] = "rash_photo"
        attachments.append(att)

# Rule-based risk flags (filled later by our rules engine; here we keep placeholder)
risk_flags_rule_based = {"risk_level": "LOW", "flags": []}

# Build intake
intake = {
    "meta": {
        "schema_version": "1.0",
        "language": lang if "lang" in locals() else "pl",
        "created_at": now_iso(),
        "source": source if "source" in locals() else "patient",
    },
    "patient": {
        "patient_id": None,
        "age_years": float(age),
        "sex": sex,
        "weight_kg": weight_kg_val,
        "is_child": is_child,
    },
    "visit": {
        "today_date": str(today),
        "started_on_date": str(started),
        "chief_complaint_category": chief,
        "chief_complaint_free_text": chief_free or None,
        "first_visit_or_followup": first_follow,
    },
    "timeline": {
        "events": st.session_state["timeline_events"] if st.session_state["timeline_events"] else [
            {"date": str(started), "symptom_type": "other", "change": "appeared", "character": None, "severity": "unknown", "notes": None}
        ]
    },
    "measurements": {},
    "modules": modules,
    "history": history,
    "attachments": attachments,
    "risk_flags_rule_based": risk_flags_rule_based,
}

if show_temp:
    intake["measurements"]["temperature"] = {
        "measured": True if st.session_state["temp_rows"] else False,
        "unit": "C",
        "graph": st.session_state["temp_rows"],
    }

# Simple missing-info hints (patient-side)
missing = []
if not intake["timeline"]["events"]:
    add_missing(missing, "Add at least one timeline event (date + symptom).")
if chief == "fever" and (not intake.get("measurements", {}).get("temperature", {}).get("graph")):
    add_missing(missing, "For fever: please enter at least one temperature measurement.")
if chief == "chest_pain_sob" and "triage_adult" not in modules:
    add_missing(missing, "For chest pain/shortness of breath: triage block is required.")
if started > today:
    add_missing(missing, "Start date cannot be after today.")

if missing:
    st.warning("Missing / Braki:\n- " + "\n- ".join(missing))

st.subheader("Resulting Intake JSON")
st.code(json.dumps(intake, indent=2, ensure_ascii=False), language="json")

st.download_button(
    "Download intake.json",
    data=json.dumps(intake, indent=2, ensure_ascii=False),
    file_name="intake.json",
    mime="application/json",
)