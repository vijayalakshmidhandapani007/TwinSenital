"""Integration tests for TwinGuard Module 4."""

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow imports from the history directory.
HISTORY_DIR = Path(__file__).resolve().parent

if str(HISTORY_DIR) not in sys.path:
    sys.path.insert(0, str(HISTORY_DIR))

from integration import Module4Integration


def create_test_records():
    """Create 181 telemetry records spanning 180 seconds."""

    records = []

    base_time = datetime(
        2026, 10, 21, 10, 0, 0,
        tzinfo=timezone.utc,
    )

    for seq in range(181):
        timestamp = (
            base_time + timedelta(seconds=seq)
        ).isoformat().replace("+00:00", "Z")

        record = {
            "schema_version": "1.0",
            "timestamp": timestamp,
            "source": "test_sensor",
            "run_id": "integration_test_run",
            "seq": seq,
            "voltage_v": 12.6 - (seq * 0.001),
            "temperature_c": 25.0 + (seq * 0.01),
            "latency_ms": 20.0,
            "config_version": "v1",
        }

        records.append(record)

    return records


def main():
    scenarios_path = (
        HISTORY_DIR.parent
        / "contracts"
        / "scenarios.yaml"
    )

    if not scenarios_path.exists():
        raise FileNotFoundError(
            f"Scenario configuration not found: {scenarios_path}"
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir) / "telemetry.jsonl"

        integration = Module4Integration(
            storage_path=storage_path,
            scenarios_path=scenarios_path,
        )

        # Store baseline telemetry.
        baseline_records = create_test_records()

        for record in baseline_records:
            integration.store.append(record)

        # Verify all four fault scenarios.
        scenarios = [
            ("S2", "Sensor drift"),
            ("S3", "Battery degradation"),
            ("S4", "Communication loss"),
            ("S5", "Configuration inconsistency"),
        ]

        for scenario_id, description in scenarios:
            result = integration.run_scenario(
                "integration_test_run",
                scenario_id,
            )

            comparison = result["comparison"]
            metrics = comparison["metrics"]

            voltage_difference = metrics["voltage_v"]["difference"]
            temperature_difference = metrics["temperature_c"]["difference"]
            latency_difference = metrics["latency_ms"]["difference"]

            print(f"PASS: {scenario_id} - {description}")
            print(f"  Voltage difference: {voltage_difference:.4f}")
            print(f"  Temperature difference: {temperature_difference:.4f}")
            print(f"  Latency difference: {latency_difference:.4f}")

            # Check that every baseline record was compared.
            assert result["baseline_records"] == 181
            assert result["simulated_records"] == 181
            assert comparison["matched_records"] == 181

            # Check that each scenario has an observable effect.
            if scenario_id == "S2":
                assert voltage_difference > 0

            elif scenario_id == "S3":
                assert voltage_difference < 0

            elif scenario_id == "S4":
                assert latency_difference > 0

            elif scenario_id == "S5":
                simulated_records = integration.simulator.simulate(
                    baseline_records,
                    scenario_id,
                )

                assert any(
                    record.get("config_version")
                    != original["config_version"]
                    for record, original in zip(
                        simulated_records,
                        baseline_records,
                    )
                ) or any(
                    record.get("configuration_authorized") is False
                    for record in simulated_records
                ), (
                    "S5 did not produce a detectable configuration change. "
                    "Check the S5 settings in scenarios.yaml."
                )

        # Verify the stored baseline was not modified.
        stored_records = integration.store.read_run(
            "integration_test_run"
        )

        assert stored_records == baseline_records

        print("\nSUCCESS: All four scenarios passed integration!")
        print("SUCCESS: Original baseline records remain unchanged!")


if __name__ == "__main__":
    main()