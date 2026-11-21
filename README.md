# Autonomous-Venue-Operations# Autonomous Venue Operations (AVO)

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

## Not included yet

- Authenticated HTTP API or user management; the library's `tenant_id` is **not** a verified user identity
- Production concurrency controls across processes, robust migration management, backup/restore
- Secure device identity, key lifecycle, signed telemetry, hardware attestation
- Building code, fire/egress, accessibility or personal-data compliance validation
- Human handoff, payments, cleaning workflows, occupancy safety, integration adapters

## Production security boundaries

Never connect the simulator directly to a door. In production, a dedicated certified access-control system must enforce safety and egress independently of AI, the network, and this application. AI can recommend actions but must not directly actuate locks or override safety policies. Audit hashes alone are not immutable against a privileged database administrator; external integrity anchoring and retention policy would be required.

## Roadmap

1. Threat model and role-based identity provider, role separation across tenants.
2. Idempotent transactional booking API, timezone/DST edge tests, resource bundles.
3. Adapter contracts for *simulated* device interfaces and supervised exception handling.
4. Cleaning/maintenance workflows, status dashboards, redacted audit exports.
5. Independent security review and controlled pilot only after legal and hardware safety assessment.

## IP and operating boundaries

Use only owned or authorized environments and synthetic test data. No employer facilities, secrets, customer records, or hardware are needed for this demonstration. Confirm employment/IP obligations before any commercial use.

License: not yet granted. Choose a license deliberately before public GitHub publication.
