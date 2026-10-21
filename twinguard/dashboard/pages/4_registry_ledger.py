import streamlit as st
import json
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compat.check import check_compatibility
from ledger.ledger import append_entry, load_entries
from ledger.verify import verify_chain
from ledger.gate import evaluate_gate
from agents.orchestrator import investigate


st.title("Compatibility Registry & Evidence Ledger")
st.caption("TwinGuard | Module 3 + Module 5")

# --------------------------------------------------
# Load registry
# --------------------------------------------------

components_path = ROOT / "compat" / "registry" / "components.json"
platforms_path = ROOT / "compat" / "registry" / "platforms.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


try:
    components = load_json(components_path).get("components", {})
    platforms = load_json(platforms_path).get("platforms", {})

except FileNotFoundError:
    st.error("Registry files are missing.")
    st.stop()

except json.JSONDecodeError:
    st.error("Registry JSON is invalid.")
    st.stop()


# --------------------------------------------------
# Registry overview
# --------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.metric("Registered Components", len(components))

with col2:
    st.metric("Registered Platforms", len(platforms))

st.divider()


# --------------------------------------------------
# Compatibility check
# --------------------------------------------------

st.subheader("Component Compatibility Check")

if not components or not platforms:
    st.warning("Add components and platforms to the registry.")

else:

    component_id = st.selectbox(
        "Select Component",
        list(components.keys())
    )

    platform_id = st.selectbox(
        "Select Platform",
        list(platforms.keys())
    )

    if st.button("Check Compatibility", type="primary"):

        result = check_compatibility(component_id, platform_id)

        st.session_state["compat_result"] = result
        st.session_state["compat_component"] = component_id
        st.session_state["compat_platform"] = platform_id


# --------------------------------------------------
# Compatibility report
# --------------------------------------------------

if "compat_result" in st.session_state:

    result = st.session_state["compat_result"]

    component_id = st.session_state["compat_component"]
    platform_id = st.session_state["compat_platform"]

    st.divider()
    st.subheader("Compatibility Report")

    st.write("**Evidence ID:**", result["evidence_id"])

    if result["compatible"]:
        st.success("Component is compatible.")

    else:
        st.error("Component is NOT compatible.")

    violations = result.get("violations", [])

    if violations:
        st.dataframe(
            violations,
            use_container_width=True,
            hide_index=True
        )

        st.metric("Total Violations", len(violations))

    else:
        st.info("No compatibility violations detected.")

    # --------------------------------------------------
    # Validation gate
    # --------------------------------------------------

    st.divider()
    st.subheader("Validation Gate")

    twin_confidence = st.slider(
        "Twin Confidence",
        min_value=0.0,
        max_value=1.0,
        value=0.95,
        step=0.05
    )

    evidence_refs = [result["evidence_id"]]

    gate = evaluate_gate(
        twin_confidence=twin_confidence,
        evidence_refs=evidence_refs,
        required_evidence=[result["evidence_id"]]
    )

    if gate["gate_result"] == "accepted":
        st.success("Gate Result: ACCEPTED")

    else:
        st.warning("Gate Result: INCONCLUSIVE")

        for reason in gate["gate_reasons"]:
            st.write("-", reason)

    # --------------------------------------------------
    # Append evidence to ledger
    # --------------------------------------------------

    st.divider()
    st.subheader("Save Investigation to Ledger")

    if st.button("Append Evidence to Ledger"):

        # Prevent duplicate appends on repeated clicks
        if st.session_state.get("last_saved_evidence") == result["evidence_id"]:

            st.warning("This evidence has already been saved.")

        else:

            if result["compatible"]:

                finding_label = "normal"

                observation = (
                    f"{component_id} is compatible with {platform_id}."
                )

                recommendation_text = (
                    "Proceed with the validated compatibility checks."
                )

            else:

                finding_label = "compatibility_issue"

                observation = (
                    f"{component_id} is incompatible with {platform_id}."
                )

                recommendation_text = (
                    "Do not approve the component until "
                    "compatibility violations are resolved."
                )

            entry = {
                "run_id": f"COMPAT-{component_id}-{platform_id}",
                "twin_version": "1.0",
                "twin_confidence": twin_confidence,
                "evidence_refs": evidence_refs,
                "agents_used": ["orchestrator"],
                "tools_used": ["compatibility_checker"],
                "finding": {
                    "label": finding_label,
                    "confirmed_observations": [observation],
                    "possible_explanations": [
                        violation["requirement"]
                        for violation in violations
                    ],
                    "insufficient_evidence": (
                        gate["gate_result"] == "inconclusive"
                    )
                },
                "recommendation": {
                    "text": recommendation_text,
                    "uncertainty": (
                        "high"
                        if gate["gate_result"] == "inconclusive"
                        else "medium"
                    )
                },
                "human_approval": None,
                "test_outcome": None,
                "gate_result": gate["gate_result"],
                "gate_reasons": gate["gate_reasons"]
            }

            saved = append_entry(entry)

            st.session_state["last_saved_evidence"] = result["evidence_id"]

            st.success(
                f"Ledger entry #{saved['entry_id']} saved successfully."
            )

            st.write("**Entry Hash:**", saved["hash"])


# --------------------------------------------------
# Run Orchestrator Investigation
# --------------------------------------------------

st.divider()
st.subheader("Agentic AI Investigation")

st.write(
    "Run the Orchestrator to collect telemetry, "
    "residual, MQTT, and configuration evidence."
)

investigation_run_id = st.text_input(
    "Investigation Run ID",
    value="TEST-001"
)

if st.button("Run Investigation", type="primary"):

    with st.spinner("Collecting evidence and investigating..."):

        investigation_result = investigate({
            "run_id": investigation_run_id,
            "anomaly_id": investigation_run_id
        })

    st.session_state["investigation_result"] = investigation_result

# Display investigation result
if "investigation_result" in st.session_state:

    investigation_result = st.session_state["investigation_result"]

    st.subheader("Investigation Result")

    st.write(
        "**Status:**",
        investigation_result["status"]
    )

    st.write(
        "**Twin Confidence:**",
        investigation_result["twin_confidence"]
    )

    if investigation_result["gate_result"] == "accepted":
        st.success("Validation Gate: ACCEPTED")
    else:
        st.warning("Validation Gate: INCONCLUSIVE")

        for reason in investigation_result["gate_reasons"]:
            st.write("-", reason)

    st.write("**Summary:**", investigation_result["summary"])

    st.write("**Possible Explanations:**")

    for explanation in investigation_result["possible_explanations"]:
        st.write("-", explanation)

    st.write(
        "**Ledger Entry ID:**",
        investigation_result["ledger_entry_id"]
    )

    st.write(
        "**Ledger Hash:**",
        investigation_result["ledger_hash"]
    )
# --------------------------------------------------
# Ledger overview
# --------------------------------------------------

st.divider()
st.subheader("Evidence Ledger")

entries = load_entries()

st.metric("Total Ledger Entries", len(entries))

if entries:

    st.dataframe(
        entries,
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No evidence entries have been saved yet.")


# --------------------------------------------------
# Verify hash chain
# --------------------------------------------------

st.divider()
st.subheader("Hash-Chain Verification")

if st.button("Verify Ledger"):

    verification = verify_chain()

    if verification["valid"]:

        st.success(verification["message"])

    else:

        st.error(verification["message"])

    st.write(
        "Entries checked:",
        verification["entries_checked"]
    )