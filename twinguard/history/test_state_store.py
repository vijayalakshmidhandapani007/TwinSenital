from state_store import StateStore


def test_historical_storage():
    store = StateStore("twinguard/data/runs/history_test.jsonl")

    sample = {
        "schema_version": "1.0",
        "timestamp": "2026-10-21T10:00:00Z",
        "source": "uas_sim",
        "run_id": "run-001",
        "seq": 0,
        "voltage_v": 12.5,
        "temperature_c": 25.0,
        "latency_ms": 18.0,
        "config_version": "cfg-1.0.0",
    }

    store.append(sample)

    records = store.read_run("run-001")

    assert records, "No records were stored!"
    assert records[-1]["voltage_v"] == 12.5

    print("SUCCESS: Historical storage is working!")
    print(f"Records stored: {len(records)}")


if __name__ == "__main__":
    test_historical_storage()