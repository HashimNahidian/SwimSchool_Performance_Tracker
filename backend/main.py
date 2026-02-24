import logging
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import settings
from db import SessionLocal
from logging_utils import configure_logging
from models import AuditLog
from routers import auth, instructor, manager, supervisor
from security import decode_access_token


app = FastAPI(title="Propel Swim Academy Evaluation API", version="1.0.0")
configure_logging()
logger = logging.getLogger("propel.api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(manager.router)
app.include_router(supervisor.router)
app.include_router(instructor.router)


@app.middleware("http")
async def request_logging_and_audit(request, call_next):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        "request_complete",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": client_ip,
        },
    )

    if settings.enable_audit_log and request.url.path not in {"/health/live", "/health/ready"}:
        user_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
            try:
                payload = decode_access_token(token)
                user_id = int(payload.get("sub", "0"))
            except Exception:  # noqa: BLE001
                user_id = None
        with SessionLocal() as db:
            db.add(
                AuditLog(
                    user_id=user_id if user_id and user_id > 0 else None,
                    action="request",
                    method=request.method,
                    path=request.url.path[:255],
                    status_code=response.status_code,
                    client_ip=client_ip[:64],
                )
            )
            db.commit()
    return response


@app.on_event("startup")
def validate_runtime_configuration() -> None:
    if settings.app_env == "production" and settings.secret_key == "dev-secret-change-in-production":
        raise RuntimeError("SECRET_KEY must be set in production")
    if settings.app_env == "production" and "*" in settings.cors_origins:
        raise RuntimeError("CORS_ORIGINS cannot contain wildcard in production")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready"}
