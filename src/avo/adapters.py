"""Vendor-neutral access-device adapter contracts.

No class in this module communicates with physical hardware. Vendor adapters
prepare intent records for review; they do NOT implement vendor HTTP APIs.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping

from .core import utc_time


class Provider(str, Enum):
    VIRTUAL = "virtual"
    REMOTELOCK = "remotelock"
    AKERUN = "akerun"
    SESAME = "sesame"


@dataclass(frozen=True)
class AccessGrant:
    venue_id: str
    booking_id: str
    tenant_id: str
    starts_at: str
    ends_at: str

    def validate(self) -> None:
        if not all((self.venue_id, self.booking_id, self.tenant_id)):
            raise ValueError("Venue, booking, and tenant are required")
        if utc_time(self.starts_at) >= utc_time(self.ends_at):
            raise ValueError("Access interval must have positive duration")


@dataclass(frozen=True)
class AccessIntent:
    """An auditable *request*, not evidence that a device was changed."""
    provider: Provider
    operation: str
    booking_id: str
    device_id: str
    parameters: Mapping[str, str]
    requires_human_approval: bool = True


class LockAdapter(ABC):
    provider: Provider

    @abstractmethod
    def plan_grant(self, device_id: str, grant: AccessGrant) -> AccessIntent:
        """Return intended credential provisioning without any side effects."""

    @abstractmethod
    def plan_revoke(self, device_id: str, booking_id: str) -> AccessIntent:
        """Return intended credential revocation without any side effects."""


class ReviewOnlyAdapter(LockAdapter):
    """Generic vendor boundary, deliberately unable to execute commands.

    Mapping a booking to a specific vendor endpoint requires vendor API
    documentation, granted access, verified hardware behavior and an operator
    approval flow. The generic contract prevents application lock-in meanwhile.
    """
    def __init__(self, provider: Provider):
        if provider == Provider.VIRTUAL:
            raise ValueError("Use VirtualLockAdapter for virtual devices")
        self.provider = provider

    def plan_grant(self, device_id: str, grant: AccessGrant) -> AccessIntent:
        grant.validate()
        if not device_id:
            raise ValueError("Device ID required")
        return AccessIntent(self.provider, "grant", grant.booking_id, device_id, {
            "venue_id": grant.venue_id,
            "tenant_id": grant.tenant_id,
            "starts_at": utc_time(grant.starts_at).isoformat(),
            "ends_at": utc_time(grant.ends_at).isoformat(),
        })

    def plan_revoke(self, device_id: str, booking_id: str) -> AccessIntent:
        if not device_id or not booking_id:
            raise ValueError("Device and booking IDs required")
        return AccessIntent(self.provider, "revoke", booking_id, device_id, {})


class RemoteLockAdapter(ReviewOnlyAdapter):
    def __init__(self):
        super().__init__(Provider.REMOTELOCK)


class AkerunAdapter(ReviewOnlyAdapter):
    def __init__(self):
        super().__init__(Provider.AKERUN)


class SesameAdapter(ReviewOnlyAdapter):
    def __init__(self):
        super().__init__(Provider.SESAME)


class VirtualLockAdapter(LockAdapter):
    """In-memory fixture for API-integration tests, never a physical lock."""
    provider = Provider.VIRTUAL

    def __init__(self):
        self.grants: dict[tuple[str, str], AccessGrant] = {}

    def plan_grant(self, device_id: str, grant: AccessGrant) -> AccessIntent:
        grant.validate()
        if not device_id:
            raise ValueError("Device ID required")
        return AccessIntent(self.provider, "grant", grant.booking_id, device_id, {}, False)

    def plan_revoke(self, device_id: str, booking_id: str) -> AccessIntent:
        if not device_id or not booking_id:
            raise ValueError("Device and booking IDs required")
        return AccessIntent(self.provider, "revoke", booking_id, device_id, {}, False)

    def apply_simulated(self, intent: AccessIntent, grant: AccessGrant | None = None) -> None:
        if intent.provider != self.provider or intent.requires_human_approval:
            raise PermissionError("Only simulated intents can be applied")
        key = (intent.device_id, intent.booking_id)
        if intent.operation == "grant":
            if grant is None or grant.booking_id != intent.booking_id:
                raise ValueError("Matching grant required")
            grant.validate()
            self.grants[key] = grant
        elif intent.operation == "revoke":
            self.grants.pop(key, None)
        else:
            raise ValueError("Unknown simulated operation")

    def authorized(self, device_id: str, booking_id: str, when: str, *, online: bool = True) -> bool:
        grant = self.grants.get((device_id, booking_id))
        if not online or grant is None:
            return False
        moment: datetime = utc_time(when)
        return utc_time(grant.starts_at) <= moment < utc_time(grant.ends_at)


def adapter_for(provider: Provider | str) -> LockAdapter:
    key = Provider(provider)
    return {
        Provider.VIRTUAL: VirtualLockAdapter,
        Provider.REMOTELOCK: RemoteLockAdapter,
        Provider.AKERUN: AkerunAdapter,
        Provider.SESAME: SesameAdapter,
    }[key]()
