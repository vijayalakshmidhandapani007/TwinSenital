"""Deterministic residual summary tool for TwinGuard Module 2."""

from typing import Any


def get_residual_summary(
    run_id: str,
    window_s: int = 60
) -> dict[str, Any]:
    """Return a canned residual summary in the required tool shape."""

    return {
        "evidence_id": f"RESIDUAL-{run_id}",
        "mean_residual": {
            "voltage_v": 0.02,
            "temperature_c": 0.15
        },
        "max_residual": {
            "voltage_v": 0.08,
            "temperature_c": 0.45
        },
        "trend": "none",
        "twin_state": "Trusted",
        "confidence": 0.95
    }