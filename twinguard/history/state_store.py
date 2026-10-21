import json
from pathlib import Path


class StateStore:
    """Store and retrieve historical TwinGuard telemetry."""

    def __init__(self, storage_path):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.storage_path.touch(exist_ok=True)

    def append(self, record):
        """Append one telemetry record to the history."""
        required = {
            "schema_version",
            "timestamp",
            "source",
            "run_id",
            "seq",
            "voltage_v",
            "temperature_c",
            "latency_ms",
            "config_version",
        }

        missing = required - record.keys()

        if missing:
            raise ValueError(
                f"Missing required fields: {sorted(missing)}"
            )

        with self.storage_path.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(record, allow_nan=False) + "\n"
            )

    def read_all(self):
        """Read all historical records."""
        records = []

        with self.storage_path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    records.append(json.loads(line))

        return records

    def read_run(self, run_id):
        """Read records for one run in chronological order."""
        records = [
            record
            for record in self.read_all()
            if record["run_id"] == run_id
        ]

        return sorted(
            records,
            key=lambda record: (
                record["timestamp"],
                record["seq"],
            ),
        )