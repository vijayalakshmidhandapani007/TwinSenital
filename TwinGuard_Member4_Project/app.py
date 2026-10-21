import json
import hashlib
import hmac
import base64
import os
from pathlib import Path
from datetime import datetime, timezone
from twin import Twin, simulate_plant
import streamlit as st
st.set_page_config(page_title="TwinGuard", layout="wide")
@st.cache_resource
def get_twin():
    loads = [0.8, 1.0, 1.2]

    train = [
        simulate_plant(s, load=l, ambient=a)
        for s in range(10)
        for l, a in zip(loads, [20, 25, 30])
    ]

    calib = [
        simulate_plant(100 + s, load=l)
        for s in range(10)
        for l in loads
    ]

    t = Twin().fit(train)
    t.calibrate(calib)
    return t

twin = get_twin()
try:
    from nacl.signing import SigningKey, VerifyKey
    from nacl.exceptions import BadSignatureError
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False

APP_DIR = Path(__file__).parent
COMPONENTS_FILE = APP_DIR / "components.json"
PLATFORM_FILE = APP_DIR / "platform_spec.json"
LEDGER_FILE = APP_DIR / "ledger.json"
KEY_FILE = APP_DIR / "signing_key.txt"
ANCHOR_FILE = APP_DIR / "anchor.txt"


def load_json(path, fallback):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return fallback
    return fallback

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def parse_version(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)

def check_compatibility(component, platform):
    reasons = []
    vmin = component.get("voltage_min")
    vmax = component.get("voltage_max")
    if not isinstance(vmin, (int, float)) or not isinstance(vmax, (int, float)):
        reasons.append("Voltage range is missing or invalid")
    elif vmin < platform["voltage_min"] or vmax > platform["voltage_max"]:
        reasons.append(
            f"Voltage range {vmin}–{vmax} V is outside platform range "
            f"{platform['voltage_min']}–{platform['voltage_max']} V"
        )

    if component.get("protocol") != platform["required_protocol"]:
        reasons.append(
            f"{platform['required_protocol']} required but "
            f"{component.get('protocol', 'missing')} provided"
        )
    if parse_version(component.get("firmware", "0")) < parse_version(platform["minimum_firmware"]):
        reasons.append(
            f"Firmware {component.get('firmware', 'missing')} is below minimum "
            f"{platform['minimum_firmware']}"
        )
    if component.get("interface") != platform["required_interface"]:
        reasons.append(
            f"{platform['required_interface']} interface required but "
            f"{component.get('interface', 'missing')} provided"
        )
    if component.get("configuration") != platform["required_configuration"]:
        reasons.append(
            f"Configuration must be '{platform['required_configuration']}'"
        )
    return {"component_id": component.get("component_id", "UNKNOWN"),
            "component": component.get("name", "Unnamed component"),
            "overall": "PASS" if not reasons else "FAIL",
            "reason": "All demo rules passed." if not reasons else "; ".join(reasons),
            "rule_failures": reasons}

def ensure_signing_key():
    if not NACL_AVAILABLE:
        return None
    if KEY_FILE.exists():
        try:
            raw = base64.b64decode(KEY_FILE.read_text(encoding="utf-8").strip())
            return SigningKey(raw)
        except Exception:
            st.error("Signing key file could not be read. Do not delete it if you need to verify existing records.")
            return None
    key = SigningKey.generate()
    KEY_FILE.write_text(base64.b64encode(bytes(key)).decode("ascii"), encoding="utf-8")
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass
    return key

def load_ledger():
    data = load_json(LEDGER_FILE, [])
    return data if isinstance(data, list) else []

def ledger_payload(entry):
    return {k: entry[k] for k in ("index", "timestamp", "previous_hash", "payload")}

def append_ledger(payload):
    ledger = load_ledger()
    previous_hash = ledger[-1]["entry_hash"] if ledger else "GENESIS"
    entry = {
        "index": len(ledger) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "previous_hash": previous_hash,
        "payload": payload
    }
    entry_hash = sha256_text(canonical(ledger_payload(entry)))
    entry["entry_hash"] = entry_hash

    if NACL_AVAILABLE:
        key = ensure_signing_key()
        if key is not None:
            entry["signature"] = base64.b64encode(key.sign(entry_hash.encode("utf-8")).signature).decode("ascii")
            entry["public_key"] = base64.b64encode(bytes(key.verify_key)).decode("ascii")
        else:
            entry["signature"] = None
            entry["public_key"] = None
    else:
        entry["signature"] = None
        entry["public_key"] = None

    ledger.append(entry)
    save_json(LEDGER_FILE, ledger)
    # This local anchor helps detect ledger rewrites if the anchor remains unchanged.
    # It is not secure against an attacker who can rewrite both files.
    ANCHOR_FILE.write_text(entry_hash, encoding="utf-8")
    return entry

def verify_ledger():
    ledger = load_ledger()
    if not ledger:
        return False, "Ledger is empty.", 0
    previous = "GENESIS"
    for expected_index, entry in enumerate(ledger, start=1):
        if entry.get("index") != expected_index:
            return False, f"Record order/index error at entry {expected_index}.", expected_index
        if entry.get("previous_hash") != previous:
            return False, f"Hash-chain link broken at entry {expected_index}.", expected_index
        calculated = sha256_text(canonical(ledger_payload(entry)))
        if not hmac.compare_digest(calculated, entry.get("entry_hash", "")):
            return False, f"Record contents were changed at entry {expected_index}.", expected_index
        if NACL_AVAILABLE:
            try:
                pub = base64.b64decode(entry.get("public_key", ""))
                sig = base64.b64decode(entry.get("signature", ""))
                VerifyKey(pub).verify(entry["entry_hash"].encode("utf-8"), sig)
            except (BadSignatureError, ValueError, TypeError, Exception):
                return False, f"Signature verification failed at entry {expected_index}.", expected_index
        previous = entry["entry_hash"]

    if ANCHOR_FILE.exists():
        anchor = ANCHOR_FILE.read_text(encoding="utf-8").strip()
        if anchor != ledger[-1]["entry_hash"]:
            return False, "Latest ledger hash does not match anchor.txt.", len(ledger)
    return True, "Hash chain, record ordering, signatures (if enabled), and local anchor verified.", len(ledger)

def record_event(event_type, details):
    append_ledger({"event": event_type, "details": details})


def validate_investigation(diagnosis, confidence, evidence):
    required_evidence = {
        "Sensor drift": [
            "reference_comparison",
            "sensor_readings"
        ],
        "Communication loss": [
            "communication_logs"
        ],
        "Configuration mismatch": [
            "configuration_check"
        ],
        "Battery degradation": [
            "battery_readings"
        ]
    }

    reasons = []

    if confidence < twin.hi:
        reasons.append(
            f"Twin confidence {confidence:.0f} is below "
            f"the calibrated threshold {twin.hi:.0f}."
        )

    required = required_evidence.get(diagnosis)

    if required is None:
        reasons.append("Unknown diagnosis type.")
    else:
        for item in required:
            if not evidence.get(item, False):
                reasons.append(
                    f"Required evidence is missing: {item}."
                )

    status = "SUPPORTED" if not reasons else "INCONCLUSIVE"

    return {
        "diagnosis": diagnosis,
        "confidence": confidence,
        "required_evidence": required or [],
        "validation_status": status,
        "reasons": reasons
    }


def badge(text, color):
    st.markdown(
        f'<span style="display:inline-block;padding:5px 10px;border-radius:16px;'
        f'background:{color};color:white;font-weight:700;font-size:0.85rem">{text}</span>',
        unsafe_allow_html=True
    )

components_data = load_json(COMPONENTS_FILE, {"components":[]})
components = components_data.get("components", [])
platform = load_json(PLATFORM_FILE, {})

st.title("🛡️ TwinGuard")
st.warning(
    "Telemetry is currently software-simulated. "
    "No physical sensor or UAV data is connected."
)
if not NACL_AVAILABLE:
    st.info("Digital signatures are currently disabled because PyNaCl is not installed. Install requirements.txt to enable Ed25519 signatures.")

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
    "Open module",
    [
        "Overview",
        "Compatibility Lab",
        "Validation Gate",
        "Evidence Ledger",
        "Digital Twin Time Machine",
        "Investigation Review"
    ]
)
    st.divider()
    st.caption("Demo data is stored beside app.py in JSON files.")
    st.caption("Do not use this prototype to certify real hardware.")

ledger = load_ledger()
verified, verify_message, count = verify_ledger() if ledger else (True, "No records yet.", 0)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Virtual components", len(components))
c2.metric("Ledger records", len(ledger))
c3.metric("Ledger integrity", "VALID" if verified else "FAILED")
c4.metric("Signature mode", "Ed25519" if NACL_AVAILABLE else "Off")


if page == "Overview":
    st.subheader("TwinGuard Monitoring Dashboard")
    
    st.caption("Simulated UAV telemetry · No physical hardware")

    st.markdown("### Simulated telemetry source")

    device1, device2, device3 = st.columns(3)
    device1.metric("Data Source", "Software simulator")
    device2.metric("Stream Status", "Ready")
    device3.metric("Update Interval", "2 seconds")

    st.divider()
    st.markdown("### Live Twin Monitor")

    fault = st.selectbox(
        "Inject fault",
        [
            None,
            "sensor_drift",
            "battery_degradation",
            "config_mismatch",
            "comm_loss",
        ],
        format_func=lambda x: "Normal operation" if x is None else x,
        key="live_twin_fault",
    )

    S = st.session_state
    S.setdefault("live_run", None)
    S.setdefault("live_idx", 30)
    S.setdefault("live_running", False)

    seed = st.number_input(
    "Simulation seed",
    min_value=0,
    value=42,
    step=1,
    key="live_twin_seed"
    )

    start_col, stop_col = st.columns(2)

    if start_col.button("Start simulation", type="primary"):
        S.live_run = simulate_plant(
            seed=int(seed),
            n=300,
            fault=fault,
            fault_start=150
        )
        S.live_idx = 30
        S.live_running = True
        S.pop("last_assessment", None)

        record_event(
            "LIVE_RUN_STARTED",
            {
            "seed": int(seed),
            "fault": fault if fault is not None else "normal",
            "fault_start": 150,
            "samples": 300
            }
        )

    if stop_col.button("Stop simulation"):
        S.live_running = False

    @st.fragment(run_every=2)
    def live_panel():
        if S.live_run is None or not S.live_running:
            st.info("Select a scenario and press Start simulation.")
            return

        r = S.live_run
        S.live_idx = min(S.live_idx + 1, len(r["t"]))

        a = twin.assess(r, S.live_idx)
        S.last_assessment = a

        c1, c2, c3 = st.columns(3)
        c1.metric("Twin Status", a["status"])
        c2.metric("Confidence", f'{a["confidence"]:.1f}/100')
        c3.metric("Sample", f'{S.live_idx}/{len(r["t"])}')

        st.caption(a["reason"])

        st.line_chart({
            "Observed temperature": r["temp"][:S.live_idx],
            "Predicted temperature": twin.pred_t(r)[:S.live_idx],
        })

        st.line_chart({
            "Observed voltage": r["volt"][:S.live_idx],
            "Predicted voltage": twin.pred_v(r)[:S.live_idx],
        })

        if S.live_idx >= len(r["t"]):
            S.live_running = False
            st.info("Simulation finished. Press Start to run another test.")

    live_panel()


elif page == "Compatibility Lab":
    st.subheader("Module 3 · Virtual Compatibility Lab")
    st.write("Choose a synthetic component and check it against the platform specification.")
    if not components:
        st.error("No components found in components.json.")
    else:
        names = {f'{c["name"]} ({c["component_id"]})': c for c in components}
        selected = st.selectbox("Component to evaluate", list(names.keys()))
        comp = names[selected]
        with st.expander("View component specification"):
            st.json(comp)
        with st.expander("View platform requirements"):
            st.json(platform)
        if st.button("Run compatibility check", type="primary"):
            result = check_compatibility(comp, platform)
            if result["overall"] == "PASS":
                badge("PASS", "#16835d")
            else:
                badge("FAIL", "#b83245")
            st.markdown(f"**Component:** {result['component']}")
            st.markdown(f"**Result:** {result['overall']}")
            st.markdown(f"**Reason:** {result['reason']}")
            with st.expander("Rule-by-rule failures"):
                st.write(result["rule_failures"] if result["rule_failures"] else ["No rule failures"])
            record_event("COMPATIBILITY_CHECK", result)
            st.success("Result recorded in the evidence ledger.")
            st.session_state["last_compatibility"] = result["overall"]

elif page == "Validation Gate":
    st.subheader("Validation Gate")
    st.write("The gate only returns SUPPORTED when every required condition passes.")
    a = st.session_state.get("last_assessment")
    twin_status = a["status"] if a else "Untrusted"
    st.write("Twin status from live monitor:", twin_status)
    evidence_present = st.checkbox("Required evidence is present", value=True)
    compat_options = ["PASS", "FAIL", "NOT CHECKED"]
    default_compat = st.session_state.get("last_compatibility", "PASS")
    default_idx = compat_options.index(default_compat) if default_compat in compat_options else 0
    compat_result = st.selectbox("Compatibility result", compat_options, index=default_idx)
    diagnosis = st.selectbox("Diagnosis available", ["Yes", "No"])
    if st.button("Evaluate gate", type="primary"):
        reasons = []
        if twin_status != "Trusted":
            reasons.append(f"Twin status is {twin_status}")
        if not evidence_present:
            reasons.append("Required evidence is missing")
        if compat_result != "PASS":
            reasons.append("Compatibility has not passed")
        if diagnosis != "Yes":
            reasons.append("Diagnosis is missing")
        outcome = "SUPPORTED" if not reasons else "INCONCLUSIVE"
        details = {
            "twin_status": twin_status,
            "twin_confidence": a["confidence"] if a else 0.0,
            "evidence_present": evidence_present,
            "compatibility": compat_result,
            "diagnosis_available": diagnosis,
            "gate_result": outcome,
            "reasons": reasons
        }
        if outcome == "SUPPORTED":
            badge("SUPPORTED", "#16835d")
            st.success("All demo gate conditions passed.")
        else:
            badge("INCONCLUSIVE", "#a96d12")
            st.warning("The result must not be treated as verified.")
            for reason in reasons:
                st.write("• " + reason)
        record_event("VALIDATION_GATE", details)
        st.success("Gate decision recorded in the evidence ledger.")

elif page == "Evidence Ledger":
    st.subheader("Module 5 · Trustworthy Evidence Ledger")
    st.write("Records are hash-linked. Ed25519 signatures are enabled when PyNaCl is installed.")
    a, b = st.columns(2)
    with a:
        if st.button("Verify ledger", type="primary"):
            ok, msg, where = verify_ledger()
            if ok:
                st.success("VALID — " + msg)
            else:
                st.error("TAMPER DETECTED — " + msg)
    with b:
        if st.button("Add sample event"):
            record_event(
            "MANUAL_DEMO_EVENT",
            {"message": "A demonstration event was manually added"}
    )
            st.success("Sample event added.")
            st.rerun()
    st.markdown("### Tamper demonstration")
    st.caption("This deliberately edits the first saved record. Use only for the demo; reset the project afterwards if needed.")
    if st.button("Demo: alter first record", type="secondary", disabled=not bool(ledger)):
        altered = load_ledger()
        altered[0]["payload"]["details"] = {"message":"DELIBERATELY ALTERED FOR TAMPER TEST"}
        save_json(LEDGER_FILE, altered)
        ok, msg, where = verify_ledger()
        st.error("TAMPER DETECTED — " + msg)
    if st.button("Reset ledger for a fresh demo"):
        save_json(LEDGER_FILE, [])
        if ANCHOR_FILE.exists():
            ANCHOR_FILE.unlink()
        st.success("Ledger reset. Your signing key was kept.")
        st.rerun()
    st.markdown("### Ledger records")
    ledger = load_ledger()
    if not ledger:
        st.info("No records yet. Run a compatibility check or gate decision first.")
    else:
        for entry in reversed(ledger):
            with st.expander(f'Entry {entry.get("index")} · {entry.get("payload", {}).get("event", "Event")}'):
                st.write("Timestamp:", entry.get("timestamp"))
                st.json(entry.get("payload", {}))
                st.code("Previous hash: " + entry.get("previous_hash", ""))
                st.code("Entry hash: " + entry.get("entry_hash", ""))
                if entry.get("signature"):
                    st.caption("Ed25519 signature present.")
    st.markdown("### Local anchor")
    if ANCHOR_FILE.exists():
        st.code(ANCHOR_FILE.read_text(encoding="utf-8").strip())
        st.caption("Prototype limitation: if an attacker can alter both ledger.json and anchor.txt, this local anchor can also be rewritten. A trusted external anchor is needed for stronger protection.")

elif page == "Digital Twin Time Machine":
    import json
    import random
    from datetime import datetime, timezone
    from pathlib import Path

    st.subheader("Digital Twin Time Machine")
    st.caption("SIMULATION ONLY · Repeatable fault experiments")

    history_file = Path(__file__).parent / "time_machine_states.json"

    faults = {
    "Sensor calibration error": "sensor_drift",
    "Battery degradation": "battery_degradation",
    "Communication loss": "comm_loss",
    "Configuration inconsistency": "config_mismatch",
    }

    st.write(
        "Compare the same baseline with a controlled fault. "
        "These values are illustrative, not real sensor measurements."
    )

    fault_name = st.selectbox(
        "Choose a fault to simulate",
        list(faults.keys())
    )

    seed = st.number_input(
        "Replay seed",
        min_value=0,
        max_value=999999,
        value=42,
        step=1
    )

    
    if st.button("Run and save experiment", type="primary"):
        import math

        run_seed = int(seed)
        sample_count = 200
        fault_start = 100

        # Run baseline and fault scenarios with the same seed
        baseline_run = simulate_plant(
            seed=run_seed,
            n=sample_count,
            fault=None
        )

        faulty_run = simulate_plant(
            seed=run_seed,
            n=sample_count,
            fault=faults[fault_name],
            fault_start=fault_start
        )

        def safe_value(value):
            value = float(value)
            return round(value, 2) if math.isfinite(value) else None

        def make_replay_rows(run):
            rows = []
            predicted_temp = twin.pred_t(run)
            predicted_volt = twin.pred_v(run)

            for end in [30, 60, 90, 110, 130, 150, 170, 190, 200]:
                assessment = twin.assess(run, end)
                index = end - 1

                rows.append({
                    "sample": end,
                    "observed_temperature": safe_value(run["temp"][index]),
                    "predicted_temperature": safe_value(predicted_temp[index]),
                    "observed_voltage": safe_value(run["volt"][index]),
                    "predicted_voltage": safe_value(predicted_volt[index]),
                    "twin_status": assessment["status"],
                    "confidence": round(assessment["confidence"], 1),
                    "reason": assessment["reason"]
                })

            return rows

        baseline = make_replay_rows(baseline_run)
        faulty = make_replay_rows(faulty_run)

        experiment = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fault": fault_name,
            "fault_code": faults[fault_name],
            "seed": run_seed,
            "fault_start": fault_start,
            "samples": sample_count,
            "baseline": baseline,
            "faulty": faulty,
            "note": (
                "Software-simulated telemetry; "
                "not physical sensor or UAV evidence."
            )
        }

        try:
            if history_file.exists():
                with history_file.open("r", encoding="utf-8") as file:
                    history = json.load(file)

                if not isinstance(history, list):
                    raise ValueError(
                        "History file must contain a JSON list."
                    )
            else:
                history = []

            history.append(experiment)

            with history_file.open("w", encoding="utf-8") as file:
                json.dump(history, file, indent=2)

            st.session_state["last_time_machine_experiment"] = experiment

            record_event(
                "TIME_MACHINE_REPLAY",
                {
                    "seed": run_seed,
                    "fault": fault_name,
                    "fault_code": faults[fault_name],
                    "fault_start": fault_start,
                    "samples": sample_count,
                    "baseline_status": baseline[-1]["twin_status"],
                    "baseline_confidence": baseline[-1]["confidence"],
                    "fault_status": faulty[-1]["twin_status"],
                    "fault_confidence": faulty[-1]["confidence"]
                }
            )

            st.success(
                "Replay saved to time_machine_states.json "
                "and recorded in the evidence ledger."
            )

        except (OSError, json.JSONDecodeError, ValueError) as error:
            st.error(f"Could not save experiment: {error}")


    experiment = st.session_state.get("last_time_machine_experiment")

    if experiment:
        st.markdown("### Replay results")
        st.write("Fault:", experiment["fault"])
        st.write("Random seed:", experiment["seed"])
        st.caption("Running again with the same seed and fault reproduces the same readings.")

        st.markdown("#### Baseline readings")
        st.dataframe(experiment["baseline"], use_container_width=True)

        st.markdown("#### Fault scenario readings")
        st.dataframe(experiment["faulty"], use_container_width=True)

        if experiment["fault"] == "Communication loss":
            st.warning(
                "No observations were generated for the fault scenario. "
                "This represents simulated communication loss, not a confirmed cause."
            )
        else:
            st.info(
                "The fault effect is a fixed demonstration offset. "
                "It is not a calibrated model of a real battery or sensor."
            )

    st.markdown("### Saved experiment history")

    try:
        if history_file.exists():
            with history_file.open("r", encoding="utf-8") as file:
                saved_history = json.load(file)

            if saved_history:
                st.write(f"Saved experiments: {len(saved_history)}")
                for item in reversed(saved_history):
                    with st.expander(
                        f'{item.get("timestamp", "Unknown time")} · '
                        f'{item.get("fault", "Unknown fault")} · '
                        f'Seed {item.get("seed", "?")}'
                    ):
                        st.json(item)
            else:
                st.info("No experiments saved yet.")
        else:
            st.info("Run your first experiment to create the history file.")

    except (OSError, json.JSONDecodeError):
        st.error("The saved history file could not be read. Keep a backup before repairing it.")



elif page == "Investigation Review":
    st.subheader("Module 5 · Investigation Review")
    st.write(
        "Review an investigation, check required evidence, "
        "and record a human decision."
    )

    st.info(
        "Live twin confidence is connected to the simulated telemetry monitor. "
        "Diagnosis, evidence checklist, and recommendations are entered manually. "
        "No physical hardware is connected."
    )

    diagnosis = st.selectbox(
        "Investigation type",
        [
            "Sensor drift",
            "Communication loss",
            "Configuration mismatch",
            "Battery degradation"
        ]
    )

    a = st.session_state.get("last_assessment")

    if a is not None:
        confidence = a["confidence"]
        st.metric("Live twin confidence", f"{confidence:.1f}%")
    else:
        confidence = 0.0
        st.warning("No live twin assessment available. Confidence defaults to 0%.")

    st.markdown("### Evidence checklist")

    reference_comparison = st.checkbox(
        "Reference comparison available"
    )
    sensor_readings = st.checkbox(
        "Sensor readings available"
    )
    communication_logs = st.checkbox(
        "Communication logs available"
    )
    configuration_check = st.checkbox(
        "Configuration check completed"
    )
    battery_readings = st.checkbox(
        "Battery readings available"
    )

    observation = st.text_area(
        "Observed problem",
        placeholder="Describe what was observed..."
    )

    recommendation = st.text_area(
        "Proposed engineering recommendation",
        placeholder="Describe the proposed action..."
    )

    uncertainty = st.text_area(
        "Uncertainty or missing information",
        placeholder="Mention anything not yet confirmed..."
    )

    if st.button("Evaluate investigation", type="primary"):
        if not observation.strip():
            st.error("Please describe the observed problem.")
        elif not recommendation.strip():
            st.error("Please enter an engineering recommendation.")
        else:
            evidence = {
                "reference_comparison": reference_comparison,
                "sensor_readings": sensor_readings,
                "communication_logs": communication_logs,
                "configuration_check": configuration_check,
                "battery_readings": battery_readings
            }

            result = validate_investigation(
                diagnosis,
                confidence,
                evidence
            )

            investigation = {
                "investigation_id": datetime.now().isoformat(),
                "diagnosis": diagnosis,
                "confidence": confidence,
                "evidence": evidence,
                "observation": observation,
                "recommendation": recommendation,
                "uncertainty": uncertainty,
                "validation": result
            }
            st.session_state.pop("approved_investigation_id", None)
            st.session_state["pending_investigation"] = investigation

            a = st.session_state.get("last_assessment")

            if a is not None:
                investigation["twin_status"] = a["status"]
                investigation["twin_confidence"] = a["confidence"]
            else:
                investigation["twin_status"] = "Untrusted"
                investigation["twin_confidence"] = 0.0

            st.session_state["pending_investigation"] = investigation

            record_event(
                "INVESTIGATION_CREATED",
                investigation
            )

    investigation = st.session_state.get(
        "pending_investigation"
    )

    if investigation:
        result = investigation["validation"]

        st.markdown("### Validation result")

        if result["validation_status"] == "SUPPORTED":
            st.success("SUPPORTED — demo rules passed.")
        else:
            st.warning(
                "INCONCLUSIVE — further evidence or review is needed."
            )

        for reason in result["reasons"]:
            st.write("- " + reason)

        st.markdown("### Human review")

        reviewer = st.text_input(
            "Reviewer name or ID",
            key="investigation_reviewer"
        )

        decision = st.selectbox(
            "Review decision",
            [
                "Pending",
                "Approve recommendation",
                "Reject recommendation",
                "Request more evidence"
            ],
            key="investigation_review_decision"
        )

        if st.button("Record human review"):
            if not reviewer.strip():
                st.error("Enter the reviewer name or ID first.")
            elif decision == "Pending":
                st.warning("Choose a review decision first.")
            elif (
                decision == "Approve recommendation"
                and result["validation_status"] != "SUPPORTED"
            ):
                st.error(
                    "Approval is blocked because validation is inconclusive."
                )
            else:
                record_event(
                    "HUMAN_REVIEW",
                    {
                        "diagnosis": investigation["diagnosis"],
                        "reviewer": reviewer.strip(),
                        "decision": decision,
                        "validation_status": result["validation_status"],
                        "observation": investigation["observation"]
                    }
                )
                if decision == "Approve recommendation":
                    st.session_state["approved_investigation_id"] = (
                        investigation["investigation_id"]
                    )
                else:
                    st.session_state.pop("approved_investigation_id", None)
                st.success(
                    "Human review decision recorded in the evidence ledger."
                )
                
    
        st.markdown("### Test Outcome Recording")

        test_result = st.selectbox(
            "Engineering test result",
            ["Not tested", "PASS", "FAIL"],
            key="investigation_test_result"
        )

        test_notes = st.text_area(
            "Test observations",
            placeholder="Describe what happened during testing...",
            key="investigation_test_notes"
        )

        if st.button("Record test outcome"):
            if (
                st.session_state.get("approved_investigation_id")
                != investigation["investigation_id"]
            ):
                st.error("Record a test outcome only after the recommendation is approved.")
            elif test_result == "Not tested":
                st.warning("Select PASS or FAIL first.")
            elif not test_notes.strip():
                st.error("Enter the test observations first.")
            else:
                record_event(
                    "TEST_OUTCOME",
                    {
                        "diagnosis": investigation["diagnosis"],
                        "reviewer": reviewer.strip(),
                        "test_result": test_result,
                        "test_notes": test_notes,
                        "validation_status": result["validation_status"]
                    }
                )
                st.success(
                    "Test outcome recorded in the evidence ledger."
                )




st.divider()
st.caption("TwinGuard student prototype · synthetic compatibility registry · not a hardware safety certification.")
