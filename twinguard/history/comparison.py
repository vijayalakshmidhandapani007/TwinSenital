"""Baseline versus fault comparison for TwinGuard Module 4."""

from typing import Any


class ComparisonEngine:
    """Compare baseline telemetry against simulated telemetry."""

    NUMERIC_FIELDS = (
        "voltage_v",
        "temperature_c",
        "latency_ms",
    )

    def compare(
        self,
        baseline: list[dict[str, Any]],
        simulated: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate changes between baseline and simulated records."""

        if not baseline:
            raise ValueError("Baseline records cannot be empty.")

        if not simulated:
            raise ValueError("Simulated records cannot be empty.")

        baseline_by_key = {
            (record["run_id"], record["seq"]): record
            for record in baseline
        }

        simulated_by_key = {
            (record["run_id"], record["seq"]): record
            for record in simulated
        }

        common_keys = sorted(
            baseline_by_key.keys() & simulated_by_key.keys(),
            key=lambda key: (key[0], key[1]),
        )

        if not common_keys:
            raise ValueError(
                "No matching records found between baseline and simulation."
            )

        metrics = {}

        for field in self.NUMERIC_FIELDS:
            baseline_values = [
                float(baseline_by_key[key][field])
                for key in common_keys
            ]

            simulated_values = [
                float(simulated_by_key[key][field])
                for key in common_keys
            ]

            baseline_mean = sum(baseline_values) / len(baseline_values)
            simulated_mean = sum(simulated_values) / len(simulated_values)

            metrics[field] = {
                "baseline_mean": round(baseline_mean, 4),
                "simulated_mean": round(simulated_mean, 4),
                "difference": round(
                    simulated_mean - baseline_mean,
                    4,
                ),
            }

        return {
            "matched_records": len(common_keys),
            "baseline_records": len(baseline),
            "simulated_records": len(simulated),
            "metrics": metrics,
        }