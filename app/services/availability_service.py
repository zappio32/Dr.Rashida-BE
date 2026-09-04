import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.availability import AvailabilityRule, BlockedSlot, Holiday
from app.models.enums import AppointmentStatus
from app.models.service import Service
from app.models.user import DoctorProfile, User

logger = logging.getLogger(__name__)

# Statuses that should NOT block a slot from being offered again.
NON_BLOCKING_STATUSES = (AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW)


def _minutes(value: str) -> int:
    hours, mins = (int(part) for part in value.split(":"))
    return hours * 60 + mins


def _clock(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


async def get_available_slots(
    db: AsyncSession, local_date: str, service_id: str, doctor_id: str | None = None
) -> list[str]:
    try:
        parsed_date = datetime.strptime(local_date, "%Y-%m-%d").date()
    except ValueError:
        logger.warning("availability: invalid date format requested date=%r", local_date)
        return []

    if doctor_id:
        doctor = (
            await db.execute(
                select(DoctorProfile)
                .join(User, User.id == DoctorProfile.userId)
                .where(DoctorProfile.userId == doctor_id, User.isActive.is_(True))
            )
        ).scalar_one_or_none()
    else:
        doctor = (await db.execute(select(DoctorProfile).limit(1))).scalar_one_or_none()
    if not doctor:
        logger.warning("availability: no active doctor profile found doctorId=%s", doctor_id)
        return []

    day_start = datetime.combine(parsed_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    holiday = (
        await db.execute(
            select(Holiday).where(Holiday.doctorId == doctor.id, Holiday.date >= day_start, Holiday.date < day_end)
        )
    ).scalar_one_or_none()
    if holiday:
        logger.info("availability: date=%s doctorId=%s is a holiday, no slots", local_date, doctor.id)
        return []

    weekday = (parsed_date.weekday() + 1) % 7  # Python Monday=0 → JS-style Sunday=0

    rule = (
        await db.execute(
            select(AvailabilityRule).where(AvailabilityRule.doctorId == doctor.id, AvailabilityRule.weekday == weekday)
        )
    ).scalar_one_or_none()
    service = await db.get(Service, service_id)
    if not rule or not rule.active:
        logger.info(
            "availability: date=%s doctorId=%s weekday=%s no active schedule rule found", local_date, doctor.id, weekday
        )
        return []
    if not service:
        logger.warning("availability: serviceId=%s not found", service_id)
        return []

    try:
        schedule_start = _minutes(rule.startTime)
        schedule_end = _minutes(rule.endTime)
        break_start = _minutes(rule.breakStart) if rule.breakStart is not None else None
        break_end = _minutes(rule.breakEnd) if rule.breakEnd is not None else None
    except (TypeError, ValueError) as error:
        logger.exception("availability: invalid persisted schedule rule id=%s", rule.id)
        return []

    blocked = (
        await db.execute(
            select(BlockedSlot).where(
                BlockedSlot.doctorId == doctor.id, BlockedSlot.date >= day_start, BlockedSlot.date < day_end
            )
        )
    ).scalars().all()
    booked = (
        await db.execute(
            select(Appointment.localTime, Service.durationMin)
            .join(Service, Service.id == Appointment.serviceId)
            .where(
                Appointment.doctorId == doctor.userId,
                Appointment.localDate == local_date,
                Appointment.status.notin_(NON_BLOCKING_STATUSES),
            )
        )
    ).all()

    blocked_times = {item.time for item in blocked}
    booked_intervals = [(_minutes(time), _minutes(time) + duration) for time, duration in booked]

    generated: list[str] = []
    result: list[str] = []
    cursor = schedule_start
    end_minutes = schedule_end
    while cursor + service.durationMin <= end_minutes:
        time_str = _clock(cursor)
        generated.append(time_str)
        in_break = (
            break_start is not None
            and break_end is not None
            and cursor < break_end
            and cursor + service.durationMin > break_start
        )
        overlaps_booked = any(
            cursor < booked_end and cursor + service.durationMin > booked_start
            for booked_start, booked_end in booked_intervals
        )
        if not in_break and time_str not in blocked_times and not overlaps_booked:
            result.append(time_str)
        cursor += rule.slotMinutes

    logger.info(
        "availability: date=%s doctorId=%s serviceId=%s schedule=%s-%s slotMinutes=%s generated=%s blocked=%s booked=%s available=%s",
        local_date,
        doctor.id,
        service_id,
        rule.startTime,
        rule.endTime,
        rule.slotMinutes,
        generated,
        sorted(blocked_times),
        [(time, duration) for time, duration in booked],
        result,
    )
    return result


