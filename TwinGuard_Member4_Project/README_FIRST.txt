# TwinGuard — Member 4 Demo

This is a beginner-friendly Python/Streamlit prototype for Member 4's responsibilities:
- Module 3: virtual compatibility lab
- Module 5: validation gate and evidence ledger
- Ed25519 signatures (PyNaCl)
- SHA-256 hash chain and local anchor
- A simple dashboard with Overview, Compatibility Lab, Validation Gate, and Evidence Ledger pages

## 1. Install Python
Install Python 3.11 or 3.12 from https://www.python.org/downloads/ if it is not already installed.
During Windows installation, tick **Add Python to PATH**.

## 2. Open the project folder
Extract `TwinGuard_Member4_Project.zip`. Open the extracted folder in File Explorer.

## 3. Open a terminal in this folder
Windows: open the folder, click the address bar, type `cmd`, and press Enter.

## 4. Install dependencies
Run:
```bash
python -m pip install -r requirements.txt
```
If `python` does not work on Windows, try:
```bash
py -m pip install -r requirements.txt
```

## 5. Launch the application
Run:
```bash
python -m streamlit run app.py
```
Or on Windows:
```bash
py -m streamlit run app.py
```
A browser tab should open. If not, copy the local URL shown in the terminal (usually http://localhost:8501) into Chrome or Edge.

## 6. Demo sequence
1. Open Compatibility Lab.
2. Test `Temperature Sensor A` — expected PASS under this simplified demo specification.
3. Test `Power Module A` — expected FAIL because it has incompatible demo settings.
4. Open Validation Gate.
5. Try Trusted + evidence + compatibility PASS + diagnosis Yes — expected SUPPORTED.
6. Change twin status to Degraded — expected INCONCLUSIVE.
7. Open Evidence Ledger and click Verify ledger.
8. Click `Demo: alter first record`, then verify again — expected TAMPER DETECTED.

## Files created while running
- `ledger.json`: ledger records
- `signing_key.txt`: local Ed25519 private key (keep private; do not share)
- `anchor.txt`: latest ledger hash anchor

The signing key is created on first use and reused. If you delete or replace it, older signatures may no longer verify. The local anchor detects ledger changes only while the anchor remains trustworthy; it is not secure against an attacker who can rewrite both files.

## Honest project scope
- Components and platform rules are synthetic demonstration data.
- Compatibility checks are simplified examples, not certification of real components.
- This app does not yet read live ESP32 data.
- Connect ESP32 telemetry only after the hardware teammate confirms the serial format and the team agrees how to share data.
