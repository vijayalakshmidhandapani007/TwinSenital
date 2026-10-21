# Agent tool signatures

Deterministic tools do the checks. Agents call these tools and cite the evidence they return.
Every returned item carries an `evidence_id` so the ledger can reference it.
Until the real implementations exist, return canned data in exactly these shapes.

```python
def get_residual_summary(run_id: str, window_s: int = 60) -> dict:
    """Owner: Member 2 data, wrapped by Member 3.
    Returns {"evidence_id": str, "mean_residual": {"voltage_v": float, "temperature_c": float},
             "max_residual": {...}, "trend": "none" | "gradual_drift" | "step_change",
             "twin_state": "Trusted" | "Degraded" | "Untrusted", "confidence": float}"""

def query_logs(run_id: str, source: str, start: str, end: str, pattern: str | None = None) -> list[dict]:
    """source: "telemetry" | "mqtt_messages" | "config_events".
    Returns [{"evidence_id": str, "timestamp": str, "source": str, "detail": str}]"""

def get_config_diff(run_id: str, from_version: str, to_version: str) -> dict:
    """Returns {"evidence_id": str, "changed_keys": [str], "authorised": bool, "changed_at": str | None}"""

def check_compatibility(module_id: str, platform_id: str) -> dict:
    """Owner: Member 4.
    Returns {"evidence_id": str, "compatible": bool,
             "violations": [{"rule_id": str, "requirement": str, "actual": str}]}"""

def get_twin_state(run_id: str, timestamp: str) -> dict:
    """Returns one TwinOutput (see twin_output.schema.json)."""
```

## Physical versus cyber signatures (starting point, Member 3 refines)

- Gradual drift correlated with temperature: likely a physical or sensor fault.
- Sudden step change that coincides with an unauthorised message or configuration change: possible cyber event.
- Configuration version changed without an authorisation record: configuration issue.
- Component spec violation found by `check_compatibility`: compatibility issue.
- Missing evidence or twin state Untrusted: report "insufficient evidence", do not force a label.
