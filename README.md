# Autonomous Venue Operations (AVO)

A **venue-neutral, local-first prototype** for operating shared rental spaces: funeral halls, meeting rooms, studios, classrooms, event spaces, and other reservable facilities.

**Status: simulation / research prototype. NOT production-ready.** No real lock actuation, payment processing, emergency egress, or cloud service is implemented.

## Principle

Core objects are `Venue`, `Tenant`, `Booking`, `Credential`, and `AuditEvent`. Venue type is metadata, not business logic. Booking overlap, tenant authorization, time-bound credentials, and audit verification behave the same for any venue.

## Run

Requires Python 3.10+ and no third-party runtime dependencies.

```bash
python -m pip install -e .
python -m avo.cli
python -m unittest discover -s tests -v
```

## Included

- SQLite-backed venue registry and time-slot reservations
- Atomic overlap rejection and adjacent-booking support
- Tenant-scoped credential issuance and revocation
- Simulated time-bound lock authorization (offline = deny)
- Hash-chained audit log and integrity verification
- Automated tests for conflicts, permissions, time boundaries, offline mode, and audit tampering
- Vendor-neutral `LockAdapter` interface, review-only RemoteLOCK/Akerun/SESAME
  intent planners, and an in-memory virtual-lock lifecycle test fixture

## Access-device adapter boundary

```python
from avo.adapters import AccessGrant, adapter_for

grant = AccessGrant("hall-1", "reservation-1", "tenant-1",
                    "2026-11-22T09:00:00+09:00", "2026-11-22T12:00:00+09:00")
intent = adapter_for("remotelock").plan_grant("door-1", grant)
assert intent.requires_human_approval  # NO device command was sent
```

`RemoteLockAdapter`, `AkerunAdapter`, and `SesameAdapter` currently produce
provider-tagged *review intents only*. They do not call vendor APIs or encode
unverified vendor request schemas. `VirtualLockAdapter` alone can apply
simulated grants in memory; there are no real-hardware unlock methods.

Before adding physical integrations, check vendor API terms and device-specific
support for time windows, revoke propagation, offline behavior, emergency egress,
and independently approved operational controls.

## Not included yet

- Authenticated HTTP API or user management; the library's `tenant_id` is **not** a verified user identity
- Production concurrency controls across processes, robust migration management, backup/restore
- Secure device identity, key lifecycle, signed telemetry, hardware attestation
- Building code, fire/egress, accessibility or personal-data compliance validation
- Human handoff, payments, cleaning workflows, occupancy safety, production-grade vendor API integration

## Production security boundaries

Never connect the simulator directly to a door. In production, a dedicated certified access-control system must enforce safety and egress independently of AI, the network, and this application. AI can recommend actions but must not directly actuate locks or override safety policies. Audit hashes alone are not immutable against a privileged database administrator; external integrity anchoring and retention policy would be required.

## Roadmap

1. Threat model and role-based identity provider, role separation across tenants.
2. Idempotent transactional booking API, timezone/DST edge tests, resource bundles.
3. Adapter contracts for *simulated* device interfaces and supervised exception handling.
4. Cleaning/maintenance workflows, status dashboards, redacted audit exports.
5. Independent security review and controlled pilot only after legal and hardware safety assessment.

## Monthly Excel schedule

For operators, the JSON booking feed can be rendered into a Japanese monthly
Excel schedule. Requires the project authoring environment with
`@oai/artifact-tool` available to Node.js (development dependency only).

```bash
python -m avo.monthly --database venue.db --year 2026 --month 12 --output monthly.json
node scripts/export_monthly.mjs monthly.json monthly.xlsx
```

The workbook includes a human-readable day-by-day schedule and reservation
details. It only exports active bookings; empty dates are labeled `空き`. Tenant
IDs are shown as entered (do not use customer personal information in them).
Note: `空き` means no registered reservation, **not** certified operational
availability; closures, cleaning buffers, and maintenance are not modeled yet.

## IP and operating boundaries

Use only owned or authorized environments and synthetic test data. No employer facilities, secrets, customer records, or hardware are needed for this demonstration. Confirm employment/IP obligations before any commercial use.

License: not yet granted. Choose a license deliberately before public GitHub publication.
