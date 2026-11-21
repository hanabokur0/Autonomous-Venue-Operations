"""Export a neutral, privacy-minimized JSON feed for the monthly Excel view."""
import argparse
import json
import sqlite3
from calendar import monthrange
from datetime import datetime, timezone

from .core import utc_time


def monthly_snapshot(database: str, year: int, month: int, timezone_name: str = "Asia/Tokyo") -> dict:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(timezone_name)
    if not 1 <= month <= 12:
        raise ValueError("Month must be 1-12")
    start = datetime(year, month, 1, tzinfo=tz)
    end = datetime(year + (month == 12), (month % 12) + 1, 1, tzinfo=tz)
    db = sqlite3.connect(database)
    db.row_factory = sqlite3.Row
    venues = [dict(r) for r in db.execute("SELECT id,name,type,capacity FROM venues ORDER BY name,id")]
    bookings = []
    for r in db.execute("SELECT id,venue_id,tenant_id,starts,ends,status FROM bookings ORDER BY starts"):
        if r["status"] != "active":
            continue
        s, e = utc_time(r["starts"]), utc_time(r["ends"])
        if s >= end.astimezone(timezone.utc) or e <= start.astimezone(timezone.utc):
            continue
        bookings.append({**dict(r), "starts_local": s.astimezone(tz).isoformat(),
                         "ends_local": e.astimezone(tz).isoformat()})
    db.close()
    return {"year": year, "month": month, "timezone": timezone_name,
            "days": monthrange(year, month)[1], "venues": venues, "bookings": bookings}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a monthly schedule JSON feed")
    parser.add_argument("--database", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--timezone", default="Asia/Tokyo")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data = monthly_snapshot(args.database, args.year, args.month, args.timezone)
    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
