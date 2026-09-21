"""Strict input boundary for untrusted incident reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class InputError(ValueError):
    """An incident violates the public API contract."""


def _text(value: Any, field: str, *, minimum: int = 1, maximum: int = 280) -> str:
    if not isinstance(value, str):
        raise InputError(f"{field} must be a string")
    cleaned = value.strip()
    if not minimum <= len(cleaned) <= maximum:
        raise InputError(f"{field} must contain {minimum}–{maximum} characters")
    return cleaned


@dataclass(frozen=True)
class Incident:
    title: str
    service: str
    environment: str
    customer_impact: bool
    error_rate_percent: float
    affected_users: int
    symptoms: tuple[str, ...]
    requested_action: str
    simulate_tool_failure: bool

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Incident":
        if not isinstance(value, Mapping):
            raise InputError("Incident must be a JSON object")

        permitted = {
            "title", "service", "environment", "customer_impact",
            "error_rate_percent", "affected_users", "symptoms",
            "requested_action", "simulate_tool_failure",
        }
        unknown = set(value) - permitted
        if unknown:
            raise InputError(f"Unknown field(s): {', '.join(sorted(unknown))}")

        title = _text(value.get("title"), "title", maximum=120)
        service = _text(value.get("service"), "service", maximum=60).lower()
        environment = value.get("environment")
        if environment not in ("production", "staging", "development"):
            raise InputError("environment must be production, staging, or development")

        customer_impact = value.get("customer_impact")
        if type(customer_impact) is not bool:
            raise InputError("customer_impact must be a boolean")

        error_rate = value.get("error_rate_percent")
        if type(error_rate) not in (int, float) or not 0 <= error_rate <= 100:
            raise InputError("error_rate_percent must be a number between 0 and 100")

        affected_users = value.get("affected_users")
        if type(affected_users) is not int or not 0 <= affected_users <= 10_000_000:
            raise InputError("affected_users must be an integer between 0 and 10,000,000")

        symptoms = value.get("symptoms")
        if not isinstance(symptoms, list) or len(symptoms) > 8:
            raise InputError("symptoms must be an array of at most 8 strings")
        clean_symptoms = tuple(_text(item, "symptom", maximum=180) for item in symptoms)

        requested_action = value.get("requested_action", "none")
        requested_action = _text(requested_action, "requested_action", maximum=80)

        simulate_tool_failure = value.get("simulate_tool_failure", False)
        if type(simulate_tool_failure) is not bool:
            raise InputError("simulate_tool_failure must be a boolean")

        return cls(
            title, service, environment, customer_impact, float(error_rate),
            affected_users, clean_symptoms, requested_action, simulate_tool_failure,
        )

