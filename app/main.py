from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Dr. Rashida Ahmad API", version="1.0.0")

allow_origins = settings.cors_origins_list
if "*" in allow_origins:
    # Wildcard origins cannot be combined with cookie-based auth.
    raise RuntimeError("CORS_ORIGINS must list explicit origins; '*' is not allowed with credentialed requests.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root() -> dict:
    return {"service": "dr-rashida-ahmad-backend", "docs": "/docs"}
