"""Checks mock data and examples against the contracts. Run: python contracts/validate.py"""
import csv
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
C = ROOT / "contracts"


def load(name):
    return json.loads((C / name).read_text())


def check(schema_name, instance, label):
    errors = list(Draft202012Validator(load(schema_name)).iter_errors(instance))
    for e in errors:
        print(f"  FAIL {label}: {e.message}")
    return not errors


def main():
    ok = True
    print("Examples")
    for schema, example in [
        ("telemetry.schema.json", "examples/telemetry_example.json"),
        ("twin_output.schema.json", "examples/twin_output_example.json"),
        ("ledger_entry.schema.json", "examples/ledger_entry_example.json"),
    ]:
        good = check(schema, json.loads((C / example).read_text()), example)
        print(f"  {'ok  ' if good else 'FAIL'} {example}")
        ok &= good

    print("Mock telemetry")
    for csv_path in sorted((ROOT / "data" / "mock").glob("*.csv")):
        bad = 0
        with csv_path.open() as f:
            for row in csv.DictReader(f):
                msg = {
                    **row,
                    "seq": int(row["seq"]),
                    "voltage_v": float(row["voltage_v"]),
                    "temperature_c": float(row["temperature_c"]),
                    "latency_ms": float(row["latency_ms"]),
                }
                if not check("telemetry.schema.json", msg, f"{csv_path.name} seq={row['seq']}"):
                    bad += 1
        print(f"  {'ok  ' if not bad else 'FAIL'} {csv_path.name}")
        ok &= bad == 0

    print("Scenarios")
    data = yaml.safe_load((C / "scenarios.yaml").read_text())
    labels = {"normal", "physical_fault", "cyber_event", "config_issue", "compatibility_issue"}
    good = all(s["label"] in labels for s in data["scenarios"])
    print(f"  {'ok  ' if good else 'FAIL'} {len(data['scenarios'])} scenarios, labels valid")
    ok &= good

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
