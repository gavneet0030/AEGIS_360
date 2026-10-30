"""Small authorization helpers for optional OIDC-backed application access."""

from __future__ import annotations


def email_is_allowed(email: str, domains: tuple[str, ...], emails: tuple[str, ...]) -> bool:
    """Allow only an exact configured email or an address at an approved domain."""
    normalized = email.strip().casefold()
    if not normalized or normalized.count("@") != 1:
        return False
    local_part, domain = normalized.rsplit("@", 1)
    if not local_part or not domain:
        return False
    return normalized in {item.casefold() for item in emails} or domain in {
        item.casefold().lstrip("@") for item in domains
    }
