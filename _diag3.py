import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:yEwuwhZUShgmZImJasaAsVzYvwWoNizF@sakura.proxy.rlwy.net:35155/railway")
import asyncio
from sqlalchemy import select
from app.db.database import get_async_sessionmaker
from app.models.user import User, DoctorProfile
from app.models.enums import Role

async def main():
    Session = get_async_sessionmaker()
    async with Session() as db:
        users = (await db.execute(select(User).where(User.role == Role.DOCTOR))).scalars().all()
        for u in users:
            profile = (await db.execute(select(DoctorProfile).where(DoctorProfile.userId == u.id))).scalar_one_or_none()
            print(u.id, u.email, u.name, u.isActive, u.createdAt, "profile:", profile.id if profile else None)

asyncio.run(main())
