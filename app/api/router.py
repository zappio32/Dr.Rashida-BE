from fastapi import APIRouter

from app.api.routes import admin, appointments, auth, availability, doctor, documents, health, notifications, payments, public

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(public.router)
api_router.include_router(appointments.router)
api_router.include_router(availability.router)
api_router.include_router(admin.router)
api_router.include_router(doctor.router)
api_router.include_router(documents.router)
api_router.include_router(notifications.router)
api_router.include_router(payments.router)
