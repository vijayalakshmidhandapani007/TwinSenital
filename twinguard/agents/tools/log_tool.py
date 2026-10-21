"""Deterministic log query tool for TwinGuard Module 2."""

from typing import Any


def query_logs(
    run_id: str,
    source: str,
    start: str,
    end: str,
    pattern: str | None = None
) -> list[dict[str, Any]]:
    """Return canned log records in the required tool shape."""

    logs = [
        {
            "evidence_id": f"LOG-{run_id}-001",
            "timestamp": "2026-10-21T10:00:00",
            "source": "telemetry",
            "detail": "Voltage residual increased gradually."
        },
        {
            "evidence_id": f"LOG-{run_id}-002",
            "timestamp": "2026-10-21T10:01:00",
            "source": "mqtt_messages",
            "detail": "Unexpected MQTT message received."
        },
        {
            "evidence_id": f"LOG-{run_id}-003",
            "timestamp": "2026-10-21T10:02:00",
            "source": "config_events",
            "detail": "Configuration version changed."
        }
    ]

    results = []

    for log in logs:
        if log["source"] != source:
            continue

        if not start <= log["timestamp"] <= end:
            continue

        if pattern and pattern.lower() not in log["detail"].lower():
            continue

        results.append(log)

    return results