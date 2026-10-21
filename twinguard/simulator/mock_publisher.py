"""Replays a telemetry CSV to MQTT in the contract format (contracts/telemetry.schema.json).
Member 1 ships this on day one so everyone can build against live-looking data.

Usage: python simulator/mock_publisher.py --csv data/mock/telemetry_mock_drift.csv --rate 5
"""
import argparse
import csv
import json
import time

import paho.mqtt.client as mqtt


def make_client():
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)  # paho-mqtt 2.x
    except AttributeError:
        return mqtt.Client()  # paho-mqtt 1.x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/mock/telemetry_mock.csv")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--rate", type=float, default=1.0, help="messages per second")
    args = ap.parse_args()

    client = make_client()
    client.connect(args.host, args.port)
    client.loop_start()

    with open(args.csv) as f:
        for row in csv.DictReader(f):
            msg = {
                "schema_version": row["schema_version"],
                "timestamp": row["timestamp"],
                "source": row["source"],
                "run_id": row["run_id"],
                "seq": int(row["seq"]),
                "voltage_v": float(row["voltage_v"]),
                "temperature_c": float(row["temperature_c"]),
                "latency_ms": float(row["latency_ms"]),
                "config_version": row["config_version"],
            }
            client.publish(f"twinguard/telemetry/{msg['source']}", json.dumps(msg))
            time.sleep(1.0 / args.rate)

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
