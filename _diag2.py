"""Temporary diagnostic — exercises the admin appointment-configuration endpoints in-process against the live DB (read-only where possible)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:yEwuwhZUShgmZImJasaAsVzYvwWoNizF@sakura.proxy.rlwy.net:35155/railway")

import httpx
from sqlalchemy import select

from app.core.security import create_session_token
from app.db.database import get_async_sessionmaker
from app.models.user import User
from app.models.enums import Role
from app.main import app


async def main() -> None:
    Session = get_async_sessionmaker()
    async with Session() as db:
        admin = (await db.execute(select(User).where(User.role == Role.ADMIN).limit(1))).scalar_one_or_none()
        doctor = (await db.execute(select(User).where(User.role == Role.DOCTOR).limit(1))).scalar_one_or_none()
    if not admin:
        print("no admin user found")
        return
    token = create_session_token(user_id=admin.id, role="ADMIN", name=admin.name, email=admin.email)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies={"dra_session": token}) as client:
        endpoints = [
            "/api/admin/dashboard-summary",
            "/api/admin/departments",
            "/api/admin/doctors",
            "/api/admin/services",
        ]
        for ep in endpoints:
            try:
                r = await client.get(ep)
                print(ep, "->", r.status_code, r.text[:300])
            except Exception as e:
                print(ep, "-> EXCEPTION", repr(e))

        # doctor-scoped endpoints need a doctor id
        if doctor:
            for ep in [
                f"/api/admin/doctors/{doctor.id}/availability-rules",
                f"/api/admin/doctors/{doctor.id}/holidays",
                f"/api/admin/doctors/{doctor.id}/blocked-slots",
            ]:
                try:
                    r = await client.get(ep)
                    print(ep, "->", r.status_code, r.text[:300])
                except Exception as e:
                    print(ep, "-> EXCEPTION", repr(e))

        # public patient-facing endpoints (no auth)
        for ep in ["/api/public/departments", "/api/public/doctors", "/api/public/services"]:
            try:
                r = await client.get(ep)
                print(ep, "->", r.status_code, r.text[:300])
            except Exception as e:
                print(ep, "-> EXCEPTION", repr(e))

        if doctor:
            try:
                r = await client.get("/api/availability", params={"date": "2026-08-24", "serviceId": "none", "doctorId": doctor.id})
                print("/api/availability ->", r.status_code, r.text[:300])
            except Exception as e:
                print("/api/availability -> EXCEPTION", repr(e))


asyncio.run(main())
