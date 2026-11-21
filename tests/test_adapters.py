import unittest

from avo.adapters import (
    AccessGrant, AkerunAdapter, Provider, RemoteLockAdapter,
    SesameAdapter, VirtualLockAdapter, adapter_for,
)


GRANT = AccessGrant("hall-1", "booking-1", "company-1",
                    "2026-11-22T09:00:00+09:00", "2026-11-22T12:00:00+09:00")


class AdapterTests(unittest.TestCase):
    def test_vendor_adapters_do_not_execute(self):
        for adapter in (RemoteLockAdapter(), AkerunAdapter(), SesameAdapter()):
            intent = adapter.plan_grant("door-1", GRANT)
            self.assertTrue(intent.requires_human_approval)
            self.assertEqual(intent.booking_id, "booking-1")
            self.assertEqual(intent.parameters["tenant_id"], "company-1")
            self.assertEqual(adapter.plan_revoke("door-1", "booking-1").operation, "revoke")
            self.assertFalse(hasattr(adapter, "apply"))

    def test_virtual_lifecycle_and_offline_behavior(self):
        adapter = VirtualLockAdapter()
        intent = adapter.plan_grant("door-1", GRANT)
        adapter.apply_simulated(intent, GRANT)
        self.assertTrue(adapter.authorized("door-1", "booking-1", "2026-11-22T10:00:00+09:00"))
        self.assertFalse(adapter.authorized("door-1", "booking-1", "2026-11-22T12:00:00+09:00"))
        self.assertFalse(adapter.authorized("door-1", "booking-1", "2026-11-22T10:00:00+09:00", online=False))
        adapter.apply_simulated(adapter.plan_revoke("door-1", "booking-1"))
        self.assertFalse(adapter.authorized("door-1", "booking-1", "2026-11-22T10:00:00+09:00"))

    def test_invalid_intervals_and_cross_provider_protection(self):
        bad = AccessGrant("v", "b", "t", "2026-11-22T12:00:00+09:00", "2026-11-22T09:00:00+09:00")
        with self.assertRaises(ValueError):
            adapter_for(Provider.SESAME).plan_grant("door", bad)
        virtual = VirtualLockAdapter()
        with self.assertRaises(PermissionError):
            virtual.apply_simulated(RemoteLockAdapter().plan_grant("door", GRANT), GRANT)

    def test_factory(self):
        for name in ("virtual", "remotelock", "akerun", "sesame"):
            self.assertEqual(adapter_for(name).provider.value, name)


if __name__ == "__main__":
    unittest.main()
