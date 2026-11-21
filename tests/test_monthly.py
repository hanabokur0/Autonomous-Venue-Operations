import tempfile
import unittest
from pathlib import Path

from avo.core import VenueOperations
from avo.monthly import monthly_snapshot


class MonthlyExportTests(unittest.TestCase):
    def test_month_boundary_and_cancelled_booking(self):
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / "venue.db")
            ops = VenueOperations(database)
            ops.add_venue("v", "ギャラリー", "gallery", 20)
            good = ops.reserve("v", "tenant-a", "2026-11-30T23:00:00+09:00", "2026-12-01T02:00:00+09:00")
            bad = ops.reserve("v", "tenant-b", "2026-12-03T10:00:00+09:00", "2026-12-03T11:00:00+09:00")
            ops.cancel(bad, "tenant-b")
            ops.close()
            data = monthly_snapshot(database, 2026, 12)
            self.assertEqual(data["days"], 31)
            self.assertEqual([b["id"] for b in data["bookings"]], [good])
            self.assertEqual(data["bookings"][0]["ends_local"], "2026-12-01T02:00:00+09:00")


if __name__ == "__main__":
    unittest.main()
