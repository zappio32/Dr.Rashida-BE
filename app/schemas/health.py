from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    ok: bool
    database: str
    environment: str | None = None
