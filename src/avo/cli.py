"""Safe local demo for any bookable space."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from .core import VenueOperations


def main() -> None:
    parser = argparse.ArgumentParser(description="Run simulated shared-venue operations")
    parser.add_argument("--database", default=":memory:")
    args = parser.parse_args()
    ops = VenueOperations(args.database)
    venue_id = "room-alpha"
    try:
        ops.add_venue(venue_id, "Shared Space A", "multipurpose", 20)
    except Exception as exc:
        parser.error(f"Use a new database for the demo: {exc}")
    beginning = datetime.now(timezone.utc) + timedelta(minutes=1)
    ending = beginning + timedelta(hours=2)
    booking = ops.reserve(venue_id, "tenant-a", beginning.isoformat(), ending.isoformat())
    credential = ops.issue_access(booking, "tenant-a")
    print(json.dumps({"venue": venue_id, "booking": booking,
        "early_access": ops.simulated_unlock(venue_id, credential, datetime.now(timezone.utc).isoformat()),
        "during_booking": ops.simulated_unlock(venue_id, credential, (beginning+timedelta(minutes=1)).isoformat()),
        "offline_access": ops.simulated_unlock(venue_id, credential, (beginning+timedelta(minutes=1)).isoformat(), online=False),
        "audit_valid": ops.verify_audit()}, indent=2))
    ops.close()


if __name__ == "__main__":
    main()
