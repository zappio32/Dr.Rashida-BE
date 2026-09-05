import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError
from fastapi import HTTPException, Response

from app.api.routes.admin import create_doctor
from app.api.routes.auth import login, register
from app.core.security import hash_password, verify_password
from app.models.department import Department
from app.models.enums import Role
from app.models.service import Service
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, SessionUser
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


class _AuthResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def first(self):
        return self.value


class _AuthDatabase:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []

    async def execute(self, query):
        return _AuthResult(self.existing)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        for value in self.added:
            if getattr(value, "id", None) is None:
                value.id = "generated-id"
        user = next((item for item in self.added if isinstance(item, User)), None)
        profile = next((item for item in self.added if item.__class__.__name__ == "PatientProfile"), None)
        profile = profile or next((item for item in self.added if item.__class__.__name__ == "DoctorProfile"), None)
        if user and profile:
            profile.userId = user.id

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def refresh(self, value):
        return None


class _DoctorDatabase(_AuthDatabase):
    def __init__(self, results):
        super().__init__()
        self.results = iter(results)
        self.department = Department(id="department", name="General Medicine", active=True)

    async def execute(self, query):
        return next(self.results)

    async def get(self, model, identifier):
        return self.department if model is Department else None


class AccountFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_patient_registers_and_logs_in_with_same_credentials(self):
        db = _AuthDatabase()
        response = Response()
        await register(
            RegisterRequest(name="New Patient", email="new.patient@example.com", password="Password@123"),
            response,
            db,
        )
        user = next(item for item in db.added if isinstance(item, User))
        profile = next(item for item in db.added if item.__class__.__name__ == "PatientProfile")
        user.isActive = True
        self.assertEqual(user.role, Role.PATIENT)
        self.assertEqual(profile.userId, user.id)
        self.assertNotEqual(user.passwordHash, "Password@123")
        self.assertTrue(verify_password("Password@123", user.passwordHash))

        login_response = Response()
        result = await login(
            LoginRequest(email="new.patient@example.com", password="Password@123"),
            login_response,
            _AuthDatabase(existing=user),
        )
        self.assertEqual(result.role, Role.PATIENT)
        self.assertIn("dra_session", login_response.headers.get("set-cookie", ""))

    async def test_duplicate_patient_email_returns_conflict(self):
        existing = User(
            id="existing-user",
            name="Existing Patient",
            email="existing@example.com",
            passwordHash=hash_password("Password@123"),
            role=Role.PATIENT,
        )
        with self.assertRaises(HTTPException) as error:
            await register(
                RegisterRequest(name="Another", email="existing@example.com", password="Password@123"),
                Response(),
                _AuthDatabase(existing=existing),
            )
        self.assertEqual(error.exception.status_code, 409)

    async def test_admin_creates_doctor_account_and_same_credentials_login(self):
        db = _DoctorDatabase([_AuthResult(None), _AuthResult(None)])
        payload = DoctorCreateRequest(
            name="Dr. New",
            email="dr.new@example.com",
            password="Password@123",
            departmentId="department",
        )
        result = await create_doctor(
            payload,
            SessionUser(userId="admin-user", role="ADMIN", name="Admin", email="admin@example.com"),
            db,
        )
        user = next(item for item in db.added if isinstance(item, User))
        profile = next(item for item in db.added if item.__class__.__name__ == "DoctorProfile")
        user.isActive = True
        self.assertEqual(result["doctor"]["id"], user.id)
        self.assertEqual(user.role, Role.DOCTOR)
        self.assertEqual(profile.userId, user.id)
        self.assertEqual(profile.departmentId, "department")
        self.assertTrue(verify_password("Password@123", user.passwordHash))

        login_result = await login(
            LoginRequest(email="dr.new@example.com", password="Password@123"),
            Response(),
            _AuthDatabase(existing=user),
        )
        self.assertEqual(login_result.role, Role.DOCTOR)

    async def test_admin_duplicate_doctor_email_returns_conflict(self):
        existing = User(
            id="existing-doctor",
            name="Existing Doctor",
            email="doctor@example.com",
            passwordHash=hash_password("Password@123"),
            role=Role.DOCTOR,
        )
        db = _DoctorDatabase([_AuthResult(existing)])
        payload = DoctorCreateRequest(
            name="Dr. Duplicate",
            email="doctor@example.com",
            password="Password@123",
            departmentId="department",
        )
        with self.assertRaises(HTTPException) as error:
            await create_doctor(
                payload,
                SessionUser(userId="admin-user", role="ADMIN", name="Admin", email="admin@example.com"),
                db,
            )
        self.assertEqual(error.exception.status_code, 409)

    def test_patient_registration_requires_identity_fields(self):
        with self.assertRaises(ValidationError):
            RegisterRequest(name="Patient Name", email="patient@example.com")

    def test_legacy_internal_login_email_remains_supported(self):
        request = LoginRequest(email="doctor.legacy@drrashida.local", password="Password@123")
        self.assertEqual(request.email, "doctor.legacy@drrashida.local")

    def test_doctor_creation_requires_login_credentials(self):
        with self.assertRaises(ValidationError):
            DoctorCreateRequest(name="Dr. Test")

    def test_doctor_creation_requires_department(self):
        with self.assertRaises(ValidationError):
            DoctorCreateRequest(name="Dr. Test", email="doctor@example.com", password="Password@123")

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