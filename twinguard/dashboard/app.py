"""TwinGuard dashboard shell (Member 4). Each member builds their own page in pages/."""
import streamlit as st

st.set_page_config(page_title="TwinGuard", layout="wide")
st.title("TwinGuard")
st.write("Self-validating digital twin and evidence-backed investigation for modular UAS (non-weapon test setup).")
st.info("Use the sidebar pages: telemetry, twin, reports, registry and ledger.")
