from pathlib import Path
from tempfile import TemporaryDirectory

from state_store import StateStore
from time_machine import TimeMachine


def test_time_machine():
    with TemporaryDirectory() as temp_dir:
        store = StateStore(
            Path(temp_dir) / "history.jsonl"
        )

        timestamps = [
            "2026-10-21T10:00:00Z",
            "2026-10-21T10:00:01Z",
            "2026-10-21T10:00:02Z",
        ]

        for seq, timestamp in enumerate(timestamps):
            store.append({
                "schema_version": "1.0",
                "timestamp": timestamp,
                "source": "uas_sim",
                "run_id": "run-001",
                "seq": seq,
                "voltage_v": 12.5 - seq * 0.1,
                "temperature_c": 25.0 + seq,
                "latency_ms": 18.0,
                "config_version": "cfg-1.0.0",
            })

        machine = TimeMachine(store)

        records = list(machine.replay("run-001"))

        assert len(records) == 3
        assert records[0]["seq"] == 0
        assert records[-1]["seq"] == 2

        incident = machine.get_range(
            "run-001",
            "2026-10-21T10:00:01Z",
            "2026-10-21T10:00:02Z",
        )

        assert len(incident) == 2

        print("SUCCESS: Time Machine replay is working!")
        print(f"Total replayed records: {len(records)}")
        print(f"Records in selected time range: {len(incident)}")


if __name__ == "__main__":
    test_time_machine()