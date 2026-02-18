import streamlit as st

st.set_page_config(page_title="Family Doctor Assistant (MVP)", layout="wide")

st.title("Family Doctor Visit Assistant (MVP)")
st.write("Use the pages on the left:")
st.markdown("- **Patient Intake**: fill a structured pre-visit form")
st.markdown("- **Doctor Dashboard**: review intake + generate draft note")

st.info("Safety: This tool does not provide diagnosis or treatment. Clinician review is required.")
