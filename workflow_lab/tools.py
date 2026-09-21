"""Read-only demo tools. No external systems are contacted."""

from __future__ import annotations


class TransientToolError(RuntimeError):
    """A recoverable lookup failure."""


RUNBOOKS = {
    "checkout": {
        "title": "Checkout error spike",
        "url": "https://example.invalid/runbooks/checkout-errors",
        "first_step": "Compare the last successful deployment with the first failing request.",
    },
    "payments": {
        "title": "Payment processing degradation",
        "url": "https://example.invalid/runbooks/payment-errors",
        "first_step": "Check gateway health and isolate failures by payment provider.",
    },
    "identity": {
        "title": "Authentication failures",
        "url": "https://example.invalid/runbooks/auth-failures",
        "first_step": "Compare failed sign-ins by region and identity provider.",
    },
}

OWNERS = {
    "checkout": "commerce-on-call",
    "payments": "payments-on-call",
    "identity": "identity-on-call",
}


def lookup_runbook(service: str) -> dict[str, str]:
    """Return a service runbook or a transparent generic fallback."""
    return RUNBOOKS.get(service, {
        "title": "General incident triage",
        "url": "https://example.invalid/runbooks/general-triage",
        "first_step": "Confirm the affected service and identify a recent change.",
    })


def lookup_owner(service: str) -> str:
    return OWNERS.get(service, "platform-on-call")

