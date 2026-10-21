# TwinGuard

An agentic AI-driven, self-validating digital twin for cybersecurity and reliability assurance of modular Unmanned Aerial Systems (UAS).

**Scope:** non-weapon components and controlled engineering scenarios only. Component specifications are synthetic. Cyber events are simulated on an isolated test network for defensive detection. Safety-critical decisions need authorised human approval.

## Modules

| # | Module | Folder | Owner |
|---|---|---|---|
| 1 | Self-validating digital twin | `twin/` | Member 2 |
| 2 | Agentic cyber-physical investigation engine | `agents/` | Member 3 |
| 3 | Virtual interoperability and compatibility lab | `compat/` | Member 4 |
| 4 | Time machine and what-if simulator | `twin/` | Member 2 |
| 5 | Trustworthy AI engineering evidence ledger | `ledger/` | Member 4 |
| - | Edge, simulator, data pipeline | `edge/`, `simulator/`, `backend/` | Member 1 |

## Quick start

```bash
cp .env.example .env            # then edit the values
docker compose up -d            # MQTT broker + PostgreSQL
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python contracts/validate.py    # checks mock data and examples against the contracts
python simulator/mock_publisher.py   # publishes mock telemetry to MQTT
streamlit run dashboard/app.py
```

## Day-one rule

Everyone builds against the mock data in `data/mock/` and the schemas in `contracts/`. Do not wait for another member's real module.

See `CONTRIBUTING.md` for the working agreement.
