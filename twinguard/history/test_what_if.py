from pathlib import Path

from what_if import WhatIfSimulator


def test_sensor_drift():
    project_root = Path(__file__).resolve().parents[1]

    scenarios_path = (
        project_root / "contracts" / "scenarios.yaml"
    )

    simulator = WhatIfSimulator(scenarios_path)

    baseline = [
        {
            "schema_version": "1.0",
            "timestamp": "2026-10-21T10:00:00Z",
            "source": "uas_sim",
            "run_id": "run-001",
            "seq": 150,
            "voltage_v": 12.5,
            "temperature_c": 25.0,
            "latency_ms": 18.0,
            "config_version": "cfg-1.0.0",
        },
        {
            "schema_version": "1.0",
            "timestamp": "2026-10-21T10:00:01Z",
            "source": "uas_sim",
            "run_id": "run-001",
            "seq": 151,
            "voltage_v": 12.4,
            "temperature_c": 26.0,
            "latency_ms": 19.0,
            "config_version": "cfg-1.0.0",
        },
    ]

    simulated = simulator.simulate(baseline, "S2")

    assert simulated[0]["voltage_v"] == 12.5
    assert simulated[1]["voltage_v"] > 12.4

    # The original baseline must remain unchanged.
    assert baseline[1]["voltage_v"] == 12.4

    print("SUCCESS: Config-driven sensor drift works!")
    print("Baseline voltage:", baseline[1]["voltage_v"])
    print("Simulated voltage:", simulated[1]["voltage_v"])


if __name__ == "__main__":
    test_sensor_drift()