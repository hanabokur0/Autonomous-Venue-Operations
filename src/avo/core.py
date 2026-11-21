"""Dependency-free, local-first facility reservation and simulated access.

All times are timezone-aware ISO-8601 timestamps, normalized to UTC.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def utc_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone offset required")
    return parsed.astimezone(timezone.utc)


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class VenueOperations:
    def __init__(self, database: str | Path = ":memory:"):
        self.db = sqlite3.connect(str(database))
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS venues (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
            capacity INTEGER NOT NULL CHECK(capacity > 0));
          CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY, venue_id TEXT NOT NULL REFERENCES venues(id),
            tenant_id TEXT NOT NULL, starts TEXT NOT NULL, ends TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('active','cancelled')));
          CREATE TABLE IF NOT EXISTS credentials (
            digest TEXT PRIMARY KEY, booking_id TEXT NOT NULL REFERENCES bookings(id),
            revoked INTEGER NOT NULL DEFAULT 0);
          CREATE TABLE IF NOT EXISTS audit (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            action TEXT NOT NULL, subject TEXT NOT NULL, result TEXT NOT NULL,
            previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL);
        """)
        self.db.commit()

    def _record(self, action: str, subject: str, result: str) -> None:
        # Tamper-evident chain, not tamper-proof against privileged DB rewrites.
        last = self.db.execute("SELECT entry_hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        previous = last[0] if last else "0" * 64
        when = stamp(datetime.now(timezone.utc))
        encoded = json.dumps([when, action, subject, result, previous], separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        self.db.execute("INSERT INTO audit(timestamp,action,subject,result,previous_hash,entry_hash) VALUES(?,?,?,?,?,?)",
                        (when, action, subject, result, previous, digest))

    def add_venue(self, venue_id: str, name: str, kind: str, capacity: int) -> None:
        if not venue_id or not name or not kind or capacity <= 0:
            raise ValueError("Invalid venue")
        with self.db:
            self.db.execute("INSERT INTO venues VALUES(?,?,?,?)", (venue_id, name, kind, capacity))
            self._record("venue_created", venue_id, "ok")

    def reserve(self, venue_id: str, tenant_id: str, start: str, end: str) -> str:
        beginning, ending = utc_time(start), utc_time(end)
        if not tenant_id or beginning >= ending:
            raise ValueError("Invalid booking interval or tenant")
        booking_id = secrets.token_hex(12)
        with self.db:
            if not self.db.execute("SELECT 1 FROM venues WHERE id=?", (venue_id,)).fetchone():
                raise ValueError("Unknown venue")
            conflict = self.db.execute("""SELECT 1 FROM bookings WHERE venue_id=? AND status='active'
                 AND starts < ? AND ends > ? LIMIT 1""", (venue_id, stamp(ending), stamp(beginning))).fetchone()
            if conflict:
                self._record("reservation_rejected", venue_id, "overlap")
                raise ValueError("Booking overlaps an existing reservation")
            self.db.execute("INSERT INTO bookings VALUES(?,?,?,?,?,?)",
                            (booking_id, venue_id, tenant_id, stamp(beginning), stamp(ending), "active"))
            self._record("reserved", booking_id, "ok")
        return booking_id

    def cancel(self, booking_id: str, tenant_id: str) -> None:
        with self.db:
            cur = self.db.execute("UPDATE bookings SET status='cancelled' WHERE id=? AND tenant_id=? AND status='active'",
                                  (booking_id, tenant_id))
            if not cur.rowcount:
                raise PermissionError("Booking not found for tenant")
            self.db.execute("UPDATE credentials SET revoked=1 WHERE booking_id=?", (booking_id,))
            self._record("cancelled", booking_id, "ok")

    def issue_access(self, booking_id: str, tenant_id: str) -> str:
        booking = self.db.execute("SELECT tenant_id,status FROM bookings WHERE id=?", (booking_id,)).fetchone()
        if not booking or booking["tenant_id"] != tenant_id or booking["status"] != "active":
            raise PermissionError("Not authorized to issue credentials")
        token = secrets.token_urlsafe(32)
        with self.db:
            self.db.execute("INSERT INTO credentials(digest,booking_id) VALUES(?,?)",
                            (hashlib.sha256(token.encode()).hexdigest(), booking_id))
            self._record("credential_issued", booking_id, "ok")
        return token

    def simulated_unlock(self, venue_id: str, token: str, now: str, *, online: bool = True) -> bool:
        """Demonstration only: never actuates a real lock; fails closed offline."""
        moment = stamp(utc_time(now))
        digest = hashlib.sha256(token.encode()).hexdigest()
        row = self.db.execute("""SELECT b.id,b.venue_id,b.starts,b.ends,b.status,c.revoked
            FROM credentials c JOIN bookings b ON b.id=c.booking_id WHERE c.digest=?""", (digest,)).fetchone()
        accepted = bool(online and row and row["venue_id"] == venue_id and
                        row["status"] == "active" and not row["revoked"] and
                        row["starts"] <= moment < row["ends"])
        with self.db:
            self._record("simulated_unlock", venue_id, "allow" if accepted else "deny")
        return accepted

    def verify_audit(self) -> bool:
        previous = "0" * 64
        for row in self.db.execute("SELECT * FROM audit ORDER BY seq"):
            encoded = json.dumps([row["timestamp"],row["action"],row["subject"],row["result"],previous],separators=(",", ":"))
            digest = hashlib.sha256(encoded.encode()).hexdigest()
            if not hmac.compare_digest(digest, row["entry_hash"]) or row["previous_hash"] != previous:
                return False
            previous = digest
        return True

    def close(self) -> None:
        self.db.close()
