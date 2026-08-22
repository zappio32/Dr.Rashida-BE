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

DOCTOR_A = "c1a029c62529a198e4e8d49bcb2d"
DOCTOR_B = "c1a028b4c9f8931c0a240b023ea9"
SERVICE_ID = "c1a02953acaf4b25d890d92c36af"
DATE = "2026-08-24"

async def main():
    Session = get_async_sessionmaker()
    async with Session() as db:
        patient = (await db.execute(select(User).where(User.role == Role.PATIENT).limit(1))).scalar_one_or_none()
    token = create_session_token(user_id=patient.id, role="PATIENT", name=patient.name, email=patient.email)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies={"dra_session": token}) as client:
        r = await client.post(
            "/api/appointments",
            json={
                "serviceId": SERVICE_ID,
                "doctorId": DOCTOR_A,
                "consultationType": "CLINIC",
                "localDate": DATE,
                "localTime": "10:30",
            },
        )
        print("book doctorA 10:30 ->", r.status_code, r.text)

        # double-booking attempt: same doctor/date/time again
        r2 = await client.post(
            "/api/appointments",
            json={
                "serviceId": SERVICE_ID,
                "doctorId": DOCTOR_A,
                "consultationType": "CLINIC",
                "localDate": DATE,
                "localTime": "10:30",
            },
        )
        print("double-book doctorA 10:30 ->", r2.status_code, r2.text)

        r3 = await client.get("/api/availability", params={"date": DATE, "serviceId": SERVICE_ID, "doctorId": DOCTOR_A})
        print("availability doctorA after booking ->", r3.status_code, r3.json())

        r4 = await client.get("/api/availability", params={"date": DATE, "serviceId": SERVICE_ID, "doctorId": DOCTOR_B})
        print("availability doctorB after doctorA booking ->", r4.status_code, r4.json())

asyncio.run(main())
