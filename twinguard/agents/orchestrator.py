"""
TwinGuard Module 2:
Agentic AI Cyber-Physical Investigation Engine
"""

from typing import Any, TypedDict
from langgraph.graph import StateGraph, START, END

from agents.tools.residual_tool import get_residual_summary
from agents.tools.log_tool import query_logs
from ledger.gate import evaluate_gate
from ledger.ledger import append_entry

class InvestigationState(TypedDict):
    anomaly: dict[str, Any]
    observations: list[Any]
    possible_explanations: list[str]
    status: str
    summary: str


def evidence_is_sufficient(evidence: list) -> bool:
    return len(evidence) > 0


def collect_evidence(state: InvestigationState) -> dict[str, Any]:
    anomaly = state["anomaly"]
    run_id = anomaly.get("run_id", "mock-normal-001")

    # Get residual summary
    residual_summary = get_residual_summary(run_id)

    residual_evidence = {
        "evidence_id": residual_summary["evidence_id"],
        "source": "residual_summary",
        "detail": residual_summary,
    }

    # Query telemetry logs
    telemetry_logs = query_logs(
        run_id=run_id,
        source="telemetry",
        start="2026-10-21T00:00:00",
        end="2026-10-21T23:59:59",
    )

    # Query cybersecurity-related logs
    mqtt_logs = query_logs(
        run_id=run_id,
        source="mqtt_messages",
        start="2026-10-21T00:00:00",
        end="2026-10-21T23:59:59",
    )

    # Query configuration logs
    config_logs = query_logs(
        run_id=run_id,
        source="config_events",
        start="2026-10-21T00:00:00",
        end="2026-10-21T23:59:59",
    )

    evidence = (
        telemetry_logs
        + mqtt_logs
        + config_logs
        + [residual_evidence]
    )

    return {
        "observations": evidence,
        "status": (
            "READY_FOR_INVESTIGATION"
            if evidence_is_sufficient(evidence)
            else "INSUFFICIENT_EVIDENCE"
        ),
    }


def rule_based_summary(state: InvestigationState) -> dict[str, Any]:
    evidence = state["observations"]

    if not evidence:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "possible_explanations": [],
            "summary": "Insufficient evidence for a reliable investigation.",
        }

    residual = None
    logs = []

    # Separate residual summary from log records
    for item in evidence:
        if item.get("source") == "residual_summary":
            residual = item.get("detail", {})
        else:
            logs.append(item)

    explanations = []

    # An Untrusted twin cannot support a reliable classification
    if residual and residual.get("twin_state","").lower() == "untrusted":
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "possible_explanations": [],
            "summary": "Twin state is Untrusted. Insufficient evidence.",
        }

    # Possible physical or sensor fault
    if residual and residual.get("trend") == "gradual_drift":
        explanations.append("Possible physical or sensor fault.")

    # Identify log sources
    mqtt_logs = [
        log for log in logs
        if log.get("source") == "mqtt_messages"
    ]

    config_logs = [
        log for log in logs
        if log.get("source") == "config_events"
    ]

    # Possible cyber event: step change plus message/config activity
    if residual and residual.get("trend") == "step_change":
        if mqtt_logs or config_logs:
            explanations.append(
                "Possible cyber event. Step change detected alongside "
                "message or configuration activity; authorisation "
                "must be verified."
            )

    # Configuration activity requires further authorisation checks
    if config_logs:
        explanations.append(
            "Configuration change observed; authorisation evidence is unavailable."
        )

    if not explanations:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "possible_explanations": [],
            "summary": "Insufficient evidence to classify the anomaly.",
        }

    return {
        "status": "INVESTIGATION_COMPLETE",
        "possible_explanations": explanations,
        "summary": (
            "Investigation completed. these are possible explanations, "
            "not confirmed causes.Review the evidence and verify"
            "authorisation before confirming a cause."
        ),
    }


def build_graph():
    graph = StateGraph(InvestigationState)

    graph.add_node("collect_evidence", collect_evidence)
    graph.add_node("rule_based_summary", rule_based_summary)

    graph.add_edge(START, "collect_evidence")
    graph.add_edge("collect_evidence", "rule_based_summary")
    graph.add_edge("rule_based_summary", END)

    return graph.compile()


investigation_graph = build_graph()


def investigate(anomaly: dict[str, Any]) -> dict[str, Any]:
    initial_state = {
        "anomaly": anomaly,
        "observations": [],
        "possible_explanations": [],
        "status": "",
        "summary": "",
    }

    # Run the investigation graph
    result = investigation_graph.invoke(initial_state)

    # Collect evidence references
    evidence_refs = [
        item.get("evidence_id")
        for item in result["observations"]
        if item.get("evidence_id")
    ]

    # Get actual twin confidence from residual summary
    twin_confidence = None

    for item in result["observations"]:
        if item.get("source") == "residual_summary":
            residual_detail = item.get("detail", {})
            twin_confidence = residual_detail.get("confidence")
            break

    # Fallback if residual confidence is unavailable
    if twin_confidence is None:
        twin_confidence = anomaly.get("twin_confidence")

    # Run validation gate
    if twin_confidence is None:
        gate_result = {
            "gate_result": "inconclusive",
            "gate_reasons": [
                "Twin confidence is unavailable."
            ],
        }
    else:
        gate_result = evaluate_gate(
            twin_confidence=twin_confidence,
            evidence_refs=evidence_refs,
            required_evidence=[],
        )

        # Prepare finding label
    if gate_result["gate_result"] == "inconclusive":
        finding_label = "inconclusive"
    elif result["status"] == "INSUFFICIENT_EVIDENCE":
        finding_label = "inconclusive"
    elif any(
        "cyber" in explanation.lower()
        for explanation in result["possible_explanations"]
    ):
        finding_label = "cyber_event"
    elif any(
        "configuration" in explanation.lower()
        for explanation in result["possible_explanations"]
    ):
        finding_label = "config_issue"
    elif any(
        "physical" in explanation.lower()
        or "sensor fault" in explanation.lower()
        for explanation in result["possible_explanations"]
    ):
        finding_label = "physical_fault"
    else:
        finding_label = "normal"

    # Append investigation to Evidence Ledger
    ledger_entry = append_entry({
        "run_id": anomaly.get("run_id", "UNKNOWN"),
        "twin_version": anomaly.get("twin_version", "1.0"),
        "twin_confidence": twin_confidence,
        "evidence_refs": evidence_refs,
        "agents_used": ["orchestrator"],
        "tools_used": [
            "residual_tool",
            "log_tool",
            "validation_gate"
        ],
        "finding": {
            "label": finding_label,
            "confirmed_observations": [
                item.get("detail", "")
                for item in result["observations"]
                if item.get("source") != "residual_summary"
            ],
            "possible_explanations": result["possible_explanations"],
            "insufficient_evidence": (
                gate_result["gate_result"] == "inconclusive"
            )
        },
        "recommendation": {
            "text": (
                "Review the evidence and verify authorisation "
                "before confirming a cause."
            ),
            "uncertainty": (
                "high"
                if gate_result["gate_result"] == "inconclusive"
                else "medium"
            )
        },
        "human_approval": None,
        "test_outcome": None,
        "gate_result": gate_result["gate_result"],
        "gate_reasons": gate_result["gate_reasons"]
    })

    return {
        "anomaly_id": anomaly.get("anomaly_id", "UNKNOWN"),
        "observations": result["observations"],
        "possible_explanations": result["possible_explanations"],
        "status": result["status"],
        "summary": result["summary"],
        "twin_confidence": twin_confidence,
        "gate_result": gate_result["gate_result"],
        "gate_reasons": gate_result["gate_reasons"],
        "ledger_entry_id": ledger_entry["entry_id"],
        "ledger_hash": ledger_entry["hash"]
    }


if __name__ == "__main__":
    print(investigate({"run_id": "TEST-001"}))