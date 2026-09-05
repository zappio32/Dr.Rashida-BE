import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from app.core.security import hash_password, verify_password
from app.models.department import Department
from app.models.enums import Role
from app.models.service import Service
from app.models.user import DoctorProfile, User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.doctor import DoctorCreateRequest
from app.services.appointment_service import create_appointment


class _Result:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
        return self.value


class _BookingDatabase:
    def __init__(self):
        self.doctor = SimpleNamespace(userId="doctor-user", departmentId="department", timezone="Asia/Kolkata")
        self.doctor_user = SimpleNamespace(id="doctor-user", isActive=True)
        self.patient = SimpleNamespace(id="patient-user", name="Patient Name")
        self.service = Service(id="service", name="General", description="Consultation", durationMin=30, fee=500, active=True)
        self.department = Department(id="department", name="General Medicine", active=True)
        self.added = []

    async def execute(self, query):
        return _Result((self.doctor, self.doctor_user))

    async def get(self, model, identifier):
        return {
            Service: self.service,
            User: self.patient,
            Department: self.department,
        }.get(model)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        for value in self.added:
            if getattr(value, "id", None) is None:
                value.id = "appointment-id"

    async def commit(self):
        return None

    async def refresh(self, value):
        return None


class AccountFlowTests(unittest.IsolatedAsyncioTestCase):
    def test_patient_registration_requires_identity_fields(self):
        with self.assertRaises(ValidationError):
            RegisterRequest(name="Patient Name", email="patient@example.com")

    def test_legacy_internal_login_email_remains_supported(self):
        request = LoginRequest(email="doctor.legacy@drrashida.local", password="Password@123")
        self.assertEqual(request.email, "doctor.legacy@drrashida.local")

    def test_doctor_creation_requires_login_credentials(self):
        with self.assertRaises(ValidationError):
            DoctorCreateRequest(name="Dr. Test")

    def test_password_is_hashed(self):
        password_hash = hash_password("Password@123")
        self.assertNotEqual(password_hash, "Password@123")
        self.assertTrue(verify_password("Password@123", password_hash))

    async def test_appointment_uses_authenticated_patient_and_doctor_user_ids(self):
        db = _BookingDatabase()
        with patch(
            "app.services.appointment_service.get_available_slots",
            new=AsyncMock(return_value=["09:00"]),
        ):
            appointment = await create_appointment(
                db,
                patient_id="patient-user",
                service_id="service",
                doctor_id="doctor-user",
                department_id="department",
                consultation_type="ONLINE",
                local_date="2026-09-09",
                local_time="09:00",
                concern=None,
                notes=None,
            )

        self.assertEqual(appointment.patientId, "patient-user")
        self.assertEqual(appointment.doctorId, "doctor-user")
        notifications = [item for item in db.added if item.__class__.__name__ == "Notification"]
        doctor_notification = next(item for item in notifications if item.userId == "doctor-user")
        self.assertIn("Patient: Patient Name", doctor_notification.body)
        self.assertIn("Booking ID:", doctor_notification.body)
        self.assertIn("Department: General Medicine", doctor_notification.body)
        self.assertIn("Consultation Type: ONLINE", doctor_notification.body)
        self.assertEqual(doctor_notification.appointmentId, appointment.id)


if __name__ == "__main__":
    unittest.main()