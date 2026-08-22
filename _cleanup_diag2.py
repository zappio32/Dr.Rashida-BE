import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:yEwuwhZUShgmZImJasaAsVzYvwWoNizF@sakura.proxy.rlwy.net:35155/railway")
import asyncio
from sqlalchemy import text
from app.db.database import get_async_sessionmaker

BOOKING_ID = "DRA-20260824-BB8B"
RULE_IDS = ["c1a029c6254a4fd546d0d6fa1825", "c1a029cff07ca2370c5f61411082"]

async def main():
    Session = get_async_sessionmaker()
    async with Session() as db:
        for rid in RULE_IDS:
            await db.execute(text('DELETE FROM "AvailabilityRule" WHERE "doctorId" = :d AND "weekday" = 1'), {"d": rid})
        result = await db.execute(text('SELECT id FROM "Appointment" WHERE "bookingId" = :b'), {"b": BOOKING_ID})
        row = result.first()
        if row:
            appt_id = row[0]
            await db.execute(text('DELETE FROM "AppointmentStatusHistory" WHERE "appointmentId" = :i'), {"i": appt_id})
            await db.execute(text('UPDATE "Notification" SET "appointmentId" = NULL WHERE "appointmentId" = :i'), {"i": appt_id})
            await db.execute(text('DELETE FROM "ReminderJob" WHERE "appointmentId" = :i'), {"i": appt_id})
            await db.execute(text('DELETE FROM "Payment" WHERE "appointmentId" = :i'), {"i": appt_id})
            await db.execute(text('DELETE FROM "Appointment" WHERE id = :i'), {"i": appt_id})
            await db.commit()
            print("deleted appointment + related rows:", appt_id)
        else:
            print("appointment already gone")

asyncio.run(main())
