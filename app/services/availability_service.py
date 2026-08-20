from datetime import date as date_cls
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.availability import AvailabilityRule, BlockedSlot, Holiday
from app.models.enums import AppointmentStatus
from app.models.service import Service
from app.models.user import DoctorProfile


def _minutes(value: str) -> int:
    hours, mins = (int(part) for part in value.split(":"))
    return hours * 60 + mins


def _clock(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def get_available_slots(db: Session, local_date: str, service_id: str) -> list[str]:
    doctor = db.execute(select(DoctorProfile).limit(1)).scalar_one_or_none()
    if not doctor:
        return []

    parsed_date = datetime.strptime(local_date, "%Y-%m-%d").date()

    holiday = db.execute(
        select(Holiday).where(Holiday.doctorId == doctor.id, Holiday.date == parsed_date)
    ).scalar_one_or_none()
    if holiday:
        return []

    weekday = (parsed_date.weekday() + 1) % 7  # Python Monday=0 -> JS-style Sunday=0

    rule = db.execute(
        select(AvailabilityRule).where(AvailabilityRule.doctorId == doctor.id, AvailabilityRule.weekday == weekday)
    ).scalar_one_or_none()
    service = db.get(Service, service_id)
    if not rule or not service or not rule.active:
        return []

    blocked = db.execute(select(BlockedSlot).where(BlockedSlot.doctorId == doctor.id, BlockedSlot.date == parsed_date)).scalars().all()
    booked = db.execute(
        select(Appointment.localTime).where(
            Appointment.doctorId == doctor.userId,
            Appointment.localDate == local_date,
            Appointment.status.notin_([AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]),
        )
    ).scalars().all()

    blocked_times = {item.time for item in blocked}
    booked_times = set(booked)

    result: list[str] = []
    cursor = _minutes(rule.startTime)
    end_minutes = _minutes(rule.endTime)
    while cursor + service.durationMin <= end_minutes:
        time_str = _clock(cursor)
        in_break = (
            rule.breakStart is not None
            and rule.breakEnd is not None
            and cursor < _minutes(rule.breakEnd)
            and cursor + service.durationMin > _minutes(rule.breakStart)
        )
        if not in_break and time_str not in blocked_times and time_str not in booked_times:
            result.append(time_str)
        cursor += rule.slotMinutes
    return result
