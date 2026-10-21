import json
from pathlib import Path

from ledger.ledger import calculate_hash, GENESIS_HASH, LEDGER_FILE


def verify_chain():
    """Verify entry hashes and links throughout the ledger."""

    if not LEDGER_FILE.exists():
        return {
            "valid": True,
            "entries_checked": 0,
            "message": "Ledger is empty."
        }

    with open(LEDGER_FILE, "r", encoding="utf-8") as file:
        entries = json.load(file)

    previous_hash = GENESIS_HASH

    for index, entry in enumerate(entries):

        # Check sequential entry IDs
        if entry.get("entry_id") != index:
            return {
                "valid": False,
                "entries_checked": index,
                "message": f"Entry ID mismatch at position {index}."
            }

        # Check previous hash link
        if entry.get("prev_hash") != previous_hash:
            return {
                "valid": False,
                "entries_checked": index,
                "message": f"Previous hash mismatch at entry {index}."
            }

        # Recalculate hash
        expected_hash = calculate_hash(entry)

        if entry.get("hash") != expected_hash:
            return {
                "valid": False,
                "entries_checked": index,
                "message": f"Hash mismatch at entry {index}."
            }

        previous_hash = entry["hash"]

    return {
        "valid": True,
        "entries_checked": len(entries),
        "message": "Hash chain verified successfully."
    }


if __name__ == "__main__":
    result = verify_chain()
    print(json.dumps(result, indent=2))