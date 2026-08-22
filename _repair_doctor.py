"""One-off, additive repair: restore the missing DoctorProfile for the orphaned
'doctor@drrashida.com' User row (login preserved, only adds back the profile)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:yEwuwhZUShgmZImJasaAsVzYvwWoNizF@sakura.proxy.rlwy.net:35155/railway")
import asyncio
from sqlalchemy import select
from app.db.database import get_async_sessionmaker
from app.models.user import User, DoctorProfile
from app.utils.ids import new_id

TARGET_EMAIL = "doctor@drrashida.com"

async def main():
    Session = get_async_sessionmaker()
    async with Session() as db:
        user = (await db.execute(select(User).where(User.email == TARGET_EMAIL))).scalar_one_or_none()
        if not user:
            print("user not found, nothing to do")
            return
        existing = (await db.execute(select(DoctorProfile).where(DoctorProfile.userId == user.id))).scalar_one_or_none()
        if existing:
            print("profile already exists, nothing to do:", existing.id)
            return
        profile = DoctorProfile(
            id=new_id(),
            userId=user.id,
            displayName=user.name,
            qualification="MBBS, MD",
            specialization="General Physician",
            timezone="Asia/Kolkata",
            onlineFee=500,
            clinicFee=700,
            durationMinutes=30,
        )
        db.add(profile)
        await db.commit()
        print("created profile:", profile.id, "for user:", user.id, user.email)

asyncio.run(main())
