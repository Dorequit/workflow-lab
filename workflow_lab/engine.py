"""Explicit workflow: validate → classify → enrich → gate → explain."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping, TypeVar

from .models import Incident
from .tools import TransientToolError, lookup_owner, lookup_runbook

T = TypeVar("T")


@dataclass(frozen=True)
class TraceEvent:
    step: str
    status: str
    detail: str
    attempt: int = 1


def _classify(incident: Incident) -> tuple[str, str]:
    if incident.environment != "production":
        return "SEV4", "Non-production environment"
    if incident.customer_impact and (
        incident.error_rate_percent >= 20 or incident.affected_users >= 1_000
    ):
        return "SEV1", "Customer impact with ≥20% errors or ≥1,000 affected users"
    if incident.customer_impact and (
        incident.error_rate_percent >= 5 or incident.affected_users >= 100
    ):
        return "SEV2", "Customer impact with ≥5% errors or ≥100 affected users"
    if incident.customer_impact or incident.error_rate_percent > 0:
        return "SEV3", "Limited production impact or elevated errors"
    return "SEV4", "No measured production impact"


def _call_with_retry(
    name: str,
    fn: Callable[[], T],
    trace: list[TraceEvent],
    *,
    fail_first: bool = False,
    max_attempts: int = 3,
) -> T:
    for attempt in range(1, max_attempts + 1):
        try:
            if fail_first and attempt == 1:
                raise TransientToolError("Simulated temporary lookup failure")
            value = fn()
            trace.append(TraceEvent(name, "success", "Read-only lookup completed", attempt))
            return value
        except TransientToolError as exc:
            trace.append(TraceEvent(name, "retry", str(exc), attempt))
    raise TransientToolError(f"{name} failed after {max_attempts} attempts")


def _gate_action(action: str, trace: list[TraceEvent]) -> tuple[str, str]:
    if action == "none":
        status, reason = "ready", "No operational change requested"
    elif action in {"restart_service", "publish_status"}:
        status, reason = "approval_required", "A human must approve this action before execution"
    else:
        status, reason = "blocked", "Action is outside the approved action catalog"
    trace.append(TraceEvent("policy.gate", status, reason))
    return status, reason


def run_workflow(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Return a fully serializable decision. Never executes a production action."""
    incident = Incident.from_mapping(raw)
    trace = [TraceEvent("input.validate", "success", "Strict types and bounds accepted")]

    severity, rationale = _classify(incident)
    trace.append(TraceEvent("severity.classify", "success", rationale))

    runbook = _call_with_retry(
        "tool.runbook_lookup",
        lambda: lookup_runbook(incident.service),
        trace,
        fail_first=incident.simulate_tool_failure,
    )
    owner = _call_with_retry("tool.owner_lookup", lambda: lookup_owner(incident.service), trace)
    gate_status, gate_reason = _gate_action(incident.requested_action, trace)

    evidence = [
        f"Environment: {incident.environment}",
        f"Customer impact reported: {'yes' if incident.customer_impact else 'no'}",
        f"Error rate: {incident.error_rate_percent:g}%",
        f"Affected users: {incident.affected_users:,}",
    ]
    actions = [
        "Verify the metrics and confirm the incident scope.",
        runbook["first_step"],
        f"Notify {owner} with the evidence and severity rationale.",
    ]

    result = {
        "incident": {
            "title": incident.title,
            "service": incident.service,
            "symptoms": list(incident.symptoms),
        },
        "severity": severity,
        "rationale": rationale,
        "evidence": evidence,
        "owner": owner,
        "runbook": runbook,
        "recommended_actions": actions,
        "requested_action": incident.requested_action,
        "action_gate": {"status": gate_status, "reason": gate_reason},
        "trace": [asdict(event) for event in trace],
        "metadata": {
            "engine": "deterministic-policy-v1",
            "real_world_actions_executed": 0,
            "data_source": "local-demo",
        },
    }
    return result

