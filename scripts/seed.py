"""
Seed script — clears ALL data and creates fresh users for every role.

Usage:
    cd be
    .venv/bin/python scripts/seed.py

Users created:
    ADMIN   — admin@drrashida.com       / Password@123
    DOCTOR  — doctor@drrashida.com      / Password@123  (+ DoctorProfile)
    PATIENT — patient@drrashida.com     / Password@123  (+ PatientProfile)
"""

import sys
import os

# ── make sure 'be/' is on sys.path so all app.* imports resolve ──────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.database import Base
from app.models.availability import AvailabilityRule
from app.models.enums import Role
from app.models.user import DoctorProfile, PatientProfile, User
from app.utils.ids import new_id

# ── sync engine (seed runs once — no need for async) ────────────────────────
settings = get_settings()
engine = create_engine(settings.sqlalchemy_database_url, echo=False, future=True)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

PASSWORD = "Password@123"

SEED_USERS = [
    {
        "role": Role.ADMIN,
        "name": "Admin User",
        "email": "admin@drrashida.com",
    },
    {
        "role": Role.DOCTOR,
        "name": "Dr. Rashida Ahmad",
        "email": "doctor@drrashida.com",
    },
    {
        "role": Role.PATIENT,
        "name": "Test Patient",
        "email": "patient@drrashida.com",
    },
]


def clear_all_tables(session) -> None:
    """Delete every row from all tables in dependency order (FK-safe)."""
    print("🗑️  Clearing database …")
    tables_in_order = [
        "AuditLog",
        "ContactEnquiry",
        "SystemSetting",
        "NotificationLog",
        "ReminderJob",
        "Notification",
        "PaymentTransaction",
        "Payment",
        "AppointmentStatusHistory",
        "Prescription",
        "ConsultationNote",
        "MedicalDocument",
        "Appointment",
        "BlockedSlot",
        "Holiday",
        "AvailabilityRule",
        "Service",
        "DoctorProfile",
        "PatientProfile",
        "User",
    ]
    for table in tables_in_order:
        try:
            session.execute(text(f'DELETE FROM "{table}"'))
            print(f"   ✓ {table} cleared")
        except Exception as exc:
            print(f"   ⚠  {table} — {exc} (skipped)")
    session.commit()
    print()


def seed_users(session) -> None:
    print("🌱  Creating seed users …")
    pw_hash = hash_password(PASSWORD)
    doctor_profile_id = None

    for data in SEED_USERS:
        user_id = new_id()
        user = User(
            id=user_id,
            name=data["name"],
            email=data["email"],
            passwordHash=pw_hash,
            role=data["role"],
            isActive=True,
        )
        session.add(user)
        session.flush()  # get the id before creating profile

        if data["role"] == Role.PATIENT:
            session.add(PatientProfile(id=new_id(), userId=user_id))

        elif data["role"] == Role.DOCTOR:
            doctor_profile_id = new_id()
            session.add(
                DoctorProfile(
                    id=doctor_profile_id,
                    userId=user_id,
                    displayName=data["name"],
                    qualification="MBBS, MD",
                    specialization="General Physician",
                    experience="10 years",
                    bio="Dr. Rashida Ahmad is a highly experienced general physician available for online and in-clinic consultations.",
                    languages=["English", "Hindi", "Urdu"],
                    clinicAddress="123 Medical Lane, New Delhi, India",
                    timezone="Asia/Kolkata",
                    onlineFee=500,
                    clinicFee=700,
                    durationMinutes=30,
                )
            )

    session.commit()

    if doctor_profile_id:
        seed_availability(session, doctor_profile_id)
    print()
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│                   ✅  Seed Complete                         │")
    print("├──────────┬─────────────────────────────┬───────────────────┤")
    print("│ Role     │ Email                        │ Password          │")
    print("├──────────┼─────────────────────────────┼───────────────────┤")
    for data in SEED_USERS:
        role_str = data["role"].value.ljust(8)
        email_str = data["email"].ljust(28)
        print(f"│ {role_str} │ {email_str} │ {PASSWORD}     │")
    print("└──────────┴─────────────────────────────┴───────────────────┘")


def seed_availability(session, doctor_profile_id: str) -> None:
    """Default Mon–Sat 09:00-17:00 schedule (JS weekday convention: Sun=0..Sat=6)."""
    print("🗓️  Creating default availability schedule (Mon–Sat, 09:00–17:00) …")
    for weekday in range(1, 7):  # Monday..Saturday
        session.add(
            AvailabilityRule(
                id=new_id(),
                doctorId=doctor_profile_id,
                weekday=weekday,
                startTime="09:00",
                endTime="17:00",
                breakStart="13:00",
                breakEnd="14:00",
                slotMinutes=30,
                active=True,
            )
        )
    session.commit()


if __name__ == "__main__":
    with Session() as session:
        clear_all_tables(session)
        seed_users(session)
