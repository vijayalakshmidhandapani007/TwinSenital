from pathlib import Path

from what_if import WhatIfSimulator


def main():
    project_root = Path(__file__).resolve().parents[1]
    scenarios_path = project_root / "contracts" / "scenarios.yaml"

    simulator = WhatIfSimulator(scenarios_path)

    def make_record(seq):
        return {
            "schema_version": "1.0",
            "timestamp": "2026-10-21T10:00:00Z",
            "source": "uas_sim",
            "run_id": "baseline-001",
            "seq": seq,
            "voltage_v": 12.5,
            "temperature_c": 25.0,
            "latency_ms": 18.0,
            "config_version": "cfg-1.0.0",
        }

    # S2 starts at 150 seconds.
    baseline_s2 = [make_record(150), make_record(151)]
    drift = simulator.simulate(baseline_s2, "S2")

    assert drift[1]["voltage_v"] > baseline_s2[1]["voltage_v"]
    print("PASS: S2 sensor drift")

    # S3 starts at 120 seconds.
    baseline_s3 = [make_record(120), make_record(121)]
    battery = simulator.simulate(baseline_s3, "S3")

    assert battery[1]["voltage_v"] < baseline_s3[1]["voltage_v"]
    print("PASS: S3 battery degradation")

    # S4 starts at 100 seconds and lasts 20 seconds.
    baseline_s4 = [make_record(100), make_record(101)]
    communication = simulator.simulate(baseline_s4, "S4")

    assert communication[0]["latency_ms"] > baseline_s4[0]["latency_ms"]
    assert communication[0]["fault_active"] is True
    print("PASS: S4 communication loss")

    # S5 starts at 140 seconds.
    baseline_s5 = [make_record(140), make_record(141)]
    configuration = simulator.simulate(baseline_s5, "S5")

    assert (
        configuration[0]["config_version"]
        != baseline_s5[0]["config_version"]
    )
    assert configuration[0]["configuration_authorized"] is False
    print("PASS: S5 configuration inconsistency")

    # Verify the original baseline records remain unchanged.
    assert baseline_s2[1]["voltage_v"] == 12.5
    assert baseline_s3[1]["voltage_v"] == 12.5
    assert baseline_s4[0]["latency_ms"] == 18.0
    assert baseline_s5[0]["config_version"] == "cfg-1.0.0"

    print("PASS: Baseline remains unchanged")
    print("\nAll scenario tests passed!")


if __name__ == "__main__":
    main()