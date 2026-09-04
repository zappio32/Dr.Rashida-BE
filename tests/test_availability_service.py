import unittest
from types import SimpleNamespace

from app.models.availability import AvailabilityRule
from app.models.service import Service
from app.services.availability_service import get_available_slots


class _Result:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values or []

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.values


class _Database:
    def __init__(self, rule=None, holiday=None, blocked=None, booked=None):
        self.results = [
            _Result(SimpleNamespace(id="profile", userId="user", durationMinutes=30)),
            _Result(holiday),
            _Result(rule),
            _Result(values=blocked),
            _Result(values=booked),
        ]
        self.service = Service(id="service", name="Consultation", description="Test", durationMin=30, fee=0, active=True)

    async def execute(self, query):
        return self.results.pop(0)

    async def get(self, model, identifier):
        return self.service


class AvailabilityServiceTests(unittest.IsolatedAsyncioTestCase):
    base_rule = {
        "id": "rule",
        "doctorId": "profile",
        "weekday": 1,
        "startTime": "09:00",
        "endTime": "13:00",
        "breakStart": None,
        "breakEnd": None,
        "slotMinutes": 30,
        "active": True,
    }

    async def available(self, rule=None, **database_values):
        return await get_available_slots(
            _Database(rule=rule, **database_values), "2026-09-21", "service", "user"
        )

    async def test_configured_monday_returns_slots(self):
        slots = await self.available(AvailabilityRule(**self.base_rule))
        self.assertEqual(slots, ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30"])

    async def test_inactive_or_missing_schedule_returns_empty(self):
        inactive = AvailabilityRule(**{**self.base_rule, "active": False})
        self.assertEqual(await self.available(inactive), [])
        self.assertEqual(await self.available(), [])

    async def test_break_is_excluded(self):
        rule = AvailabilityRule(**{**self.base_rule, "breakStart": "10:00", "breakEnd": "11:00"})
        self.assertEqual(await self.available(rule), ["09:00", "09:30", "11:00", "11:30", "12:00", "12:30"])

    async def test_leave_and_blocked_time_return_no_conflicting_slots(self):
        rule = AvailabilityRule(**self.base_rule)
        self.assertEqual(await self.available(rule, holiday=SimpleNamespace()), [])
        slots = await self.available(rule, blocked=[SimpleNamespace(time="12:00")])
        self.assertNotIn("12:00", slots)

    async def test_overlapping_booked_appointment_is_excluded(self):
        rule = AvailabilityRule(**self.base_rule)
        slots = await self.available(rule, booked=[("11:30", 60)])
        self.assertNotIn("11:30", slots)
        self.assertNotIn("12:00", slots)

    async def test_malformed_schedule_returns_empty(self):
        rule = AvailabilityRule(**{**self.base_rule, "startTime": "bad"})
        self.assertEqual(await self.available(rule), [])


if __name__ == "__main__":
    unittest.main()
