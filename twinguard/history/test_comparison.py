from comparison import ComparisonEngine


def test_comparison():
    baseline = [
        {
            "run_id": "baseline-001",
            "seq": 0,
            "voltage_v": 12.5,
            "temperature_c": 25.0,
            "latency_ms": 18.0,
        },
        {
            "run_id": "baseline-001",
            "seq": 1,
            "voltage_v": 12.4,
            "temperature_c": 26.0,
            "latency_ms": 20.0,
        },
    ]

    simulated = [
        {
            "run_id": "fault-001",
            "seq": 0,
            "voltage_v": 12.7,
            "temperature_c": 25.0,
            "latency_ms": 118.0,
        },
        {
            "run_id": "fault-001",
            "seq": 1,
            "voltage_v": 12.6,
            "temperature_c": 26.0,
            "latency_ms": 120.0,
        },
    ]

    # Align the sequence numbers across runs for comparison.
    baseline_aligned = [
        {**record, "run_id": "comparison"}
        for record in baseline
    ]

    simulated_aligned = [
        {**record, "run_id": "comparison"}
        for record in simulated
    ]

    engine = ComparisonEngine()

    result = engine.compare(
        baseline_aligned,
        simulated_aligned,
    )

    assert result["matched_records"] == 2

    assert result["metrics"]["voltage_v"]["difference"] == 0.2
    assert result["metrics"]["temperature_c"]["difference"] == 0.0
    assert result["metrics"]["latency_ms"]["difference"] == 100.0

    print("SUCCESS: Comparison Engine is working!")
    print(result)


if __name__ == "__main__":
    test_comparison()