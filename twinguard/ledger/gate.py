MIN_TWIN_CONFIDENCE = 0.70


def evaluate_gate(
    twin_confidence,
    evidence_refs,
    required_evidence=None
):
    """
    Decide whether a recommendation can be accepted
    or must remain inconclusive.
    """

    reasons = []

    # Check twin confidence
    if twin_confidence < MIN_TWIN_CONFIDENCE:
        reasons.append(
            f"Twin confidence {twin_confidence:.2f} "
            f"is below threshold {MIN_TWIN_CONFIDENCE:.2f}"
        )

    # Check required evidence
    if required_evidence is None:
        required_evidence = []

    missing_evidence = [
        evidence
        for evidence in required_evidence
        if evidence not in evidence_refs
    ]

    if missing_evidence:
        reasons.append(
            "Required evidence missing: "
            + ", ".join(missing_evidence)
        )

    # Final decision
    if reasons:
        return {
            "gate_result": "inconclusive",
            "gate_reasons": reasons
        }

    return {
        "gate_result": "accepted",
        "gate_reasons": []
    }


if __name__ == "__main__":

    # Demo: high confidence and evidence available
    result = evaluate_gate(
        twin_confidence=0.95,
        evidence_refs=[
            "COMPAT-SENSOR-B2-TEST-PLATFORM-1"
        ],
        required_evidence=[
            "COMPAT-SENSOR-B2-TEST-PLATFORM-1"
        ]
    )

    print(result)