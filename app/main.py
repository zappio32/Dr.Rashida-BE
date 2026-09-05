from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Keep FastAPI's default `detail` shape (loc/msg/type) so existing clients keep working,
    # and add a flattened `errors` list with field name + readable message for easier display.
    raw_errors = jsonable_encoder(exc.errors())
    for error in raw_errors:
        error.pop("input", None)
    errors = [
        {"field": ".".join(str(part) for part in err["loc"] if part != "body"), "message": err["msg"], "type": err["type"]}
        for err in raw_errors
    ]
    return JSONResponse(
        status_code=422,
        content={"detail": raw_errors, "message": "Validation failed. Please check the highlighted fields.", "errors": errors},
    )


@app.get("/")
def root() -> dict:
    return {"service": "dr-rashida-ahmad-backend", "docs": "/docs"}
