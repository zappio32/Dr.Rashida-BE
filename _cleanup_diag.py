import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:yEwuwhZUShgmZImJasaAsVzYvwWoNizF@sakura.proxy.rlwy.net:35155/railway")
import asyncio
from sqlalchemy import select
from app.db.database import get_async_sessionmaker
from app.models.availability import AvailabilityRule
from app.models.appointment import Appointment

RULE_IDS = ["c1a029d1329e485b7cf65345a7ea", "c1a029d1454e165ab4e244e4e988"]
BOOKING_ID = "DRA-20260824-BB8B"

async def main():
    Session = get_async_sessionmaker()
    async with Session() as db:
        for rid in RULE_IDS:
            rule = await db.get(AvailabilityRule, rid)
            if rule:
                await db.delete(rule)
                print("deleted rule", rid)
        appt = (await db.execute(select(Appointment).where(Appointment.bookingId == BOOKING_ID))).scalar_one_or_none()
        if appt:
            await db.delete(appt)
            print("deleted appointment", BOOKING_ID)
        await db.commit()

asyncio.run(main())
