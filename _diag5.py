import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:yEwuwhZUShgmZImJasaAsVzYvwWoNizF@sakura.proxy.rlwy.net:35155/railway")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
import asyncio
import httpx
from sqlalchemy import select
from app.core.security import create_session_token
from app.db.database import get_async_sessionmaker
from app.models.user import User
from app.models.enums import Role
from app.main import app

DOCTOR_A = "c1a029c62529a198e4e8d49bcb2d"  # Dr.Rashida (Gyno dept)
DOCTOR_B = "c1a028b4c9f8931c0a240b023ea9"  # repaired doctor
SERVICE_ID = "c1a02953acaf4b25d890d92c36af"  # General
DATE = "2026-08-24"  # Monday

async def main():
    Session = get_async_sessionmaker()
    async with Session() as db:
        admin = (await db.execute(select(User).where(User.role == Role.ADMIN).limit(1))).scalar_one_or_none()
    token = create_session_token(user_id=admin.id, role="ADMIN", name=admin.name, email=admin.email)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies={"dra_session": token}) as client:
        for doc, start, end in [(DOCTOR_A, "09:00", "13:00"), (DOCTOR_B, "09:00", "13:00")]:
            r = await client.post(
                f"/api/admin/doctors/{doc}/availability-rules",
                json={"weekday": 1, "startTime": start, "endTime": end, "slotMinutes": 30, "active": True},
            )
            print("create rule", doc, r.status_code, r.text)

        for doc in [DOCTOR_A, DOCTOR_B]:
            r = await client.get("/api/availability", params={"date": DATE, "serviceId": SERVICE_ID, "doctorId": doc})
            print("availability before booking", doc, r.status_code, r.json())

asyncio.run(main())
