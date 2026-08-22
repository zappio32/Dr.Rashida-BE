import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:yEwuwhZUShgmZImJasaAsVzYvwWoNizF@sakura.proxy.rlwy.net:35155/railway")
import asyncio
from sqlalchemy import select
from app.db.database import get_async_sessionmaker
from app.models.availability import AvailabilityRule, Holiday, BlockedSlot
from app.models.user import DoctorProfile

async def main():
    Session = get_async_sessionmaker()
    async with Session() as db:
        rules = (await db.execute(select(AvailabilityRule))).scalars().all()
        for r in rules:
            print("rule", r.doctorId, r.weekday, r.startTime, r.endTime, r.slotMinutes, r.active)
        profiles = (await db.execute(select(DoctorProfile))).scalars().all()
        for p in profiles:
            print("profile", p.id, p.userId, p.displayName, p.departmentId)

asyncio.run(main())
