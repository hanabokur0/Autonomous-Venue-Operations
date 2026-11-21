import unittest
from avo.core import VenueOperations

A = "2026-11-22T10:00:00+09:00"
B = "2026-11-22T12:00:00+09:00"
C = "2026-11-22T11:00:00+09:00"
D = "2026-11-22T13:00:00+09:00"


class VenueTests(unittest.TestCase):
    def setUp(self):
        self.ops = VenueOperations()
        self.ops.add_venue("v1", "Test Room", "studio", 10)
        self.booking = self.ops.reserve("v1", "tenant-a", A, B)

    def tearDown(self):
        self.ops.close()

    def test_overlap_and_adjacency(self):
        with self.assertRaises(ValueError):
            self.ops.reserve("v1", "tenant-b", C, D)
        self.ops.reserve("v1", "tenant-b", B, D)

    def test_authorization_and_access_window(self):
        with self.assertRaises(PermissionError):
            self.ops.issue_access(self.booking, "tenant-b")
        token = self.ops.issue_access(self.booking, "tenant-a")
        self.assertTrue(self.ops.simulated_unlock("v1", token, C))
        self.assertFalse(self.ops.simulated_unlock("v1", token, B))
        self.assertFalse(self.ops.simulated_unlock("v1", token, C, online=False))
        self.assertFalse(self.ops.simulated_unlock("wrong", token, C))
        self.assertFalse(self.ops.simulated_unlock("v1", "invalid", C))
        self.ops.cancel(self.booking, "tenant-a")
        self.assertFalse(self.ops.simulated_unlock("v1", token, C))

    def test_audit_chain_detects_change(self):
        self.assertTrue(self.ops.verify_audit())
        self.ops.db.execute("UPDATE audit SET result='allow' WHERE seq=1")
        self.assertFalse(self.ops.verify_audit())

    def test_invalid_times(self):
        with self.assertRaises(ValueError):
            self.ops.reserve("v1", "tenant-a", B, A)
        with self.assertRaises(ValueError):
            self.ops.reserve("v1", "tenant-a", "2026-11-22T10:00:00", B)


if __name__ == "__main__":
    unittest.main()
