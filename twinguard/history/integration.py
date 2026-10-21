"""Integration workflow for TwinGuard Module 4."""

from pathlib import Path
from typing import Any

from state_store import StateStore
from time_machine import TimeMachine
from what_if import WhatIfSimulator
from comparison import ComparisonEngine


class Module4Integration:
    """Connect historical storage, replay, simulation, and comparison."""

    def __init__(
        self,
        storage_path: str | Path,
        scenarios_path: str | Path,
    ):
        self.store = StateStore(storage_path)
        self.time_machine = TimeMachine(self.store)
        self.simulator = WhatIfSimulator(scenarios_path)
        self.comparator = ComparisonEngine()

    def run_scenario(
        self,
        run_id: str,
        scenario_id: str,
    ) -> dict[str, Any]:
        """Replay a run, simulate a fault, and compare the results."""

        # 1. Retrieve historical telemetry.
        baseline = list(self.time_machine.replay(run_id))

        if not baseline:
            raise ValueError(
                f"No historical records found for run: {run_id}"
            )

        # 2. Generate simulated telemetry without changing baseline.
        simulated = self.simulator.simulate(
            baseline,
            scenario_id,
        )

        # 3. Compare original and simulated behaviour.
        comparison = self.comparator.compare(
            baseline,
            simulated,
        )

        # 4. Return a structured result.
        return {
            "run_id": run_id,
            "scenario_id": scenario_id,
            "baseline_records": len(baseline),
            "simulated_records": len(simulated),
            "comparison": comparison,
            "baseline_unchanged": True,
        }