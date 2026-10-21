"""What-if fault simulation for TwinGuard."""

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class WhatIfSimulator:
    """Simulate configured faults without modifying baseline records."""

    def __init__(self, scenarios_path: str | Path):
        with open(scenarios_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        self.scenarios = {
            item["id"]: item
            for item in config["scenarios"]
        }

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        """Parse ISO timestamps, including timestamps ending in Z."""
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    def simulate(
        self,
        records: list[dict[str, Any]],
        scenario_id: str,
    ) -> list[dict[str, Any]]:
        """Return simulated records without modifying the originals."""

        if scenario_id not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario_id}")

        simulated = deepcopy(records)

        if not simulated:
            return []

        if scenario_id == "S1":
            return simulated

        scenario = self.scenarios[scenario_id]
        injection = scenario.get("injection", {})
        kind = injection.get("kind")
        start = injection.get("starts_at_s", 0)

        # Use the first record's timestamp as the start of the run.
        first_timestamp = self._parse_timestamp(
            simulated[0]["timestamp"]
        )

        for record in simulated:
            current_timestamp = self._parse_timestamp(
                record["timestamp"]
            )

            elapsed = (
                current_timestamp - first_timestamp
            ).total_seconds()

            active = elapsed >= start

            record["simulated_scenario"] = scenario_id
            record["fault_active"] = active

            if not active:
                continue

            # S2: Gradual sensor voltage drift.
            if scenario_id == "S2" and kind == "gradual_drift":
                rate = injection.get("rate_v_per_s", 0.004)

                record["voltage_v"] += (
                    rate * (elapsed - start)
                )

            # S3: Simplified battery degradation simulation.
            elif scenario_id == "S3" and kind == "faster_discharge":
                factor = injection.get("factor", 1.5)

                if factor <= 0:
                    raise ValueError(
                        "Scenario S3 factor must be greater than zero."
                    )

                # Simplified demonstration, not a physical battery model.
                record["voltage_v"] /= factor

            # S4: Communication latency spike and telemetry-dropout flags.
            elif scenario_id == "S4" and kind == "spike_and_dropout":
                duration = injection.get("duration_s", 20)

                if duration < 0:
                    raise ValueError(
                        "Scenario S4 duration cannot be negative."
                    )

                if start <= elapsed < start + duration:
                    record["latency_ms"] += 100.0

                    record["telemetry_dropped"] = (
                        int(elapsed - start) % 3 == 0
                    )
                else:
                    record["telemetry_dropped"] = False

            # S5: Configuration change simulation.
            elif scenario_id == "S5" and kind == "config_change":
                if injection.get("authorised") is False:
                    record["configuration_authorized"] = False

                new_version = injection.get("new_version")

                if new_version:
                    record["config_version"] = new_version

            else:
                raise ValueError(
                    f"Scenario {scenario_id} has unsupported "
                    f"injection kind: {kind}"
                )

        return simulated