import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone


LEDGER_FILE = Path(__file__).resolve().parent / "ledger.json"

GENESIS_HASH = "GENESIS"


def canonical_json(entry):
    """Convert an entry to deterministic JSON."""
    return json.dumps(
        entry,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )


def calculate_hash(entry):
    """Calculate SHA-256 hash excluding the hash field itself."""
    data = dict(entry)
    data.pop("hash", None)

    canonical = canonical_json(data)

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def load_entries():
    """Load existing ledger entries."""
    if not LEDGER_FILE.exists():
        return []

    with open(LEDGER_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def append_entry(entry):
    """
    Append one entry to the ledger.

    Existing entries are never overwritten.
    The new entry links to the previous entry's hash.
    """

    entries = load_entries()

    # Determine the previous hash
    if entries:
        previous_hash = entries[-1]["hash"]
        entry_id = entries[-1]["entry_id"] + 1
    else:
        previous_hash = GENESIS_HASH
        entry_id = 0

    # Prepare entry
    new_entry = dict(entry)

    new_entry["entry_id"] = entry_id

    new_entry["timestamp"] = datetime.now(
        timezone.utc
    ).isoformat()

    new_entry["prev_hash"] = previous_hash

    # Generate hash
    new_entry["hash"] = calculate_hash(new_entry)

    # Append-only storage
    entries.append(new_entry)

    with open(LEDGER_FILE, "w", encoding="utf-8") as file:
        json.dump(
            entries,
            file,
            indent=2,
            ensure_ascii=False
        )

    return new_entry


if __name__ == "__main__":

    demo_entry = {
        "run_id": "DEMO-RUN-001",
        "twin_version": "1.0",
        "twin_confidence": 0.95,
        "evidence_refs": ["COMPAT-SENSOR-B2-TEST-PLATFORM-1"],
        "agents_used": ["orchestrator"],
        "tools_used": ["compatibility_checker"],
        "finding": {
            "label": "compatibility_issue",
            "confirmed_observations": [
                "SENSOR-B2 is incompatible with TEST-PLATFORM-1"
            ],
            "possible_explanations": [
                "Module voltage and interface requirements do not match"
            ],
            "insufficient_evidence": False
        },
        "recommendation": {
            "text": "Do not approve the module until compatibility is resolved.",
            "uncertainty": "low"
        },
        "human_approval": None,
        "test_outcome": None,
        "gate_result": "accepted",
        "gate_reasons": []
    }

    result = append_entry(demo_entry)

    print("Ledger entry appended:")
    print(json.dumps(result, indent=2))