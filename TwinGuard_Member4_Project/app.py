import json
import hashlib
import hmac
import base64
import os
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st

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

st.set_page_config(page_title="TwinGuard | Member 4", page_icon="🛡️", layout="wide")

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
st.caption("Member 4 · Compatibility Lab · Validation Gate · Evidence Ledger")
st.warning("Prototype mode: component specifications and events are synthetic demo data. This application does not yet ingest live ESP32 telemetry.")
if not NACL_AVAILABLE:
    st.info("Digital signatures are currently disabled because PyNaCl is not installed. Install requirements.txt to enable Ed25519 signatures.")

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Open module", ["Overview", "Compatibility Lab", "Validation Gate", "Evidence Ledger"])
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
    st.subheader("Member 4 control centre")
    left, right = st.columns(2)
    with left:
        st.markdown("### What this module does")
        st.markdown("- Checks virtual component specifications against platform rules.\n- Blocks unsupported gate decisions.\n- Records important actions in a hash-linked ledger.\n- Verifies record hashes, ordering, signatures and local anchor.")
    with right:
        st.markdown("### Platform requirements")
        st.json(platform)
    st.markdown("### Demo sequence")
    st.markdown("1. Open **Compatibility Lab** and test a passing and failing component.\n2. Open **Validation Gate** and test Trusted vs Degraded status.\n3. Open **Evidence Ledger**, verify the chain, then run the tamper demonstration.")
    st.info("For a judge-facing demo, clearly label simulated component data and do not describe it as real hardware validation.")

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
    st.subheader("Module 5 · Validation Gate")
    st.write("The gate only returns SUPPORTED when every required condition passes.")
    twin_status = st.selectbox("Digital twin status", ["Trusted", "Degraded", "Untrusted"])
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
        details = {"twin_status":twin_status, "evidence_present":evidence_present,
                   "compatibility":compat_result, "diagnosis_available":diagnosis,
                   "gate_result":outcome, "reasons":reasons}
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
            record_event("MANUAL_DEMO_EVENT", {"message":"Member 4 manually added a demonstration event"})
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

st.divider()
st.caption("TwinGuard student prototype · synthetic compatibility registry · not a hardware safety certification.")
