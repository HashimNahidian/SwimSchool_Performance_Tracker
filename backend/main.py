import base64
import csv
import hashlib
import hmac
import io
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, asc, desc, select
from sqlalchemy.orm import Session, joinedload

import models
from db import get_db
from security import hash_password, verify_password

app = FastAPI(title="Propel Swim Evaluation API", version="1.0.0")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "8"))
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "10"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
_login_attempt_timestamps: dict[str, list[float]] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: models.UserRole
    active: bool = True


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: models.UserRole
    active: bool


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LevelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    active: bool = True


class LevelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    active: bool | None = None


class LevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    active: bool


class SkillCreate(BaseModel):
    level_id: int
    name: str = Field(min_length=1, max_length=100)
    active: bool = True


class SkillUpdate(BaseModel):
    level_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    active: bool | None = None


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level_id: int
    name: str
    active: bool


class AttributeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    active: bool = True


class AttributeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    active: bool | None = None


class AttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    active: bool


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    level_id: int | None = None
    skill_id: int | None = None
    active: bool = True
    attribute_ids: list[int] = Field(min_length=1)


class TemplateAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attribute_id: int
    sort_order: int


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    level_id: int | None
    skill_id: int | None
    active: bool
    template_attributes: list[TemplateAttributeOut]


class RatingInput(BaseModel):
    attribute_id: int
    rating_value: int = Field(ge=1, le=3)


class EvaluationCreate(BaseModel):
    instructor_id: int
    level_id: int | None = None
    skill_id: int | None = None
    session_label: str | None = Field(default=None, max_length=120)
    session_date: date
    notes: str | None = None
    ratings: list[RatingInput] = Field(default_factory=list)


class EvaluationUpdateDraft(BaseModel):
    level_id: int | None = None
    skill_id: int | None = None
    session_label: str | None = Field(default=None, max_length=120)
    session_date: date | None = None
    notes: str | None = None
    ratings: list[RatingInput] | None = None


class EvaluationRatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attribute_id: int
    rating_value: int


class EvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instructor_id: int
    supervisor_id: int
    level_id: int | None
    skill_id: int | None
    session_label: str | None
    session_date: date
    notes: str | None
    status: models.EvaluationStatus
    created_at: datetime
    submitted_at: datetime | None
    ratings: list[EvaluationRatingOut]


class TrendPoint(BaseModel):
    period: str
    evaluation_count: int
    average_rating: float


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + pad)


def create_access_token(user_id: int, role: models.UserRole) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)).timestamp()),
    }
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64url(sig)}"


def decode_access_token(token: str) -> dict:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url(expected_sig), sig_b64):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")
        payload = json.loads(_b64url_decode(payload_b64))
        if int(payload["exp"]) < int(datetime.now(timezone.utc).timestamp()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth payload") from exc


def log_audit(db: Session, actor_user_id: int | None, action: str, entity_type: str, entity_id: str | None = None, details: str | None = None) -> None:
    db.add(
        models.AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> models.User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    user_id = int(payload["sub"])
    user = db.get(models.User, user_id)
    if not user or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_roles(*allowed_roles: models.UserRole):
    def dependency(user: Annotated[models.User, Depends(get_current_user)]) -> models.User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")
        return user

    return dependency


def _replace_ratings(db: Session, evaluation: models.Evaluation, ratings: list[RatingInput]) -> None:
    existing_ids = set(db.scalars(select(models.Attribute.id)).all())
    for rating in ratings:
        if rating.attribute_id not in existing_ids:
            raise HTTPException(status_code=400, detail=f"Attribute {rating.attribute_id} does not exist")
    evaluation.ratings.clear()
    evaluation.ratings.extend(
        models.EvaluationRating(attribute_id=rating.attribute_id, rating_value=rating.rating_value) for rating in ratings
    )


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce_login_rate_limit(client_ip: str) -> None:
    now = time.time()
    window_start = now - LOGIN_RATE_LIMIT_WINDOW_SECONDS
    timestamps = [ts for ts in _login_attempt_timestamps.get(client_ip, []) if ts >= window_start]
    if len(timestamps) >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )
    timestamps.append(now)
    _login_attempt_timestamps[client_ip] = timestamps


@app.get("/")
def root():
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Annotated[Session, Depends(get_db)]):
    enforce_login_rate_limit(get_client_ip(request))
    user = db.scalar(select(models.User).where(models.User.email == payload.email))
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login")
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, user=user)


@app.post("/users", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[models.User, Depends(require_roles(models.UserRole.manager))],
):
    existing = db.scalar(select(models.User).where(models.User.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    data = payload.model_dump(exclude={"password"})
    user = models.User(**data, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users", response_model=list[UserOut])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[models.User, Depends(require_roles(models.UserRole.manager))],
    role: models.UserRole | None = None,
):
    stmt = select(models.User)
    if role:
        stmt = stmt.where(models.User.role == role)
    return list(db.scalars(stmt.order_by(models.User.name)).all())


@app.get("/instructors", response_model=list[UserOut])
def list_instructors(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[models.User, Depends(require_roles(models.UserRole.manager, models.UserRole.supervisor))],
):
    stmt = select(models.User).where(models.User.role == models.UserRole.instructor, models.User.active == True)  # noqa: E712
    return list(db.scalars(stmt.order_by(models.User.name)).all())


@app.get("/supervisors", response_model=list[UserOut])
def list_supervisors(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[models.User, Depends(get_current_user)],
):
    stmt = select(models.User).where(models.User.role == models.UserRole.supervisor, models.User.active == True)  # noqa: E712
    return list(db.scalars(stmt.order_by(models.User.name)).all())


@app.post("/levels", response_model=LevelOut)
def create_level(
    payload: LevelCreate,
    db: Annotated[Session, Depends(get_db)],
    manager: Annotated[models.User, Depends(require_roles(models.UserRole.manager))],
):
    if db.scalar(select(models.Level).where(models.Level.name == payload.name)):
        raise HTTPException(status_code=400, detail="Level name already exists")
    level = models.Level(**payload.model_dump())
    db.add(level)
    log_audit(db, manager.id, "CREATE", "level", details=payload.name)
    db.commit()
    db.refresh(level)
    return level


@app.get("/levels", response_model=list[LevelOut])
def list_levels(
    db: Annotated[Session, Depends(get_db)],
    active: bool | None = None,
):
    stmt = select(models.Level)
    if active is not None:
        stmt = stmt.where(models.Level.active == active)
    return list(db.scalars(stmt.order_by(models.Level.name)).all())


@app.patch("/levels/{level_id}", response_model=LevelOut)
def update_level(
    level_id: int,
    payload: LevelUpdate,
    db: Annotated[Session, Depends(get_db)],
    manager: Annotated[models.User, Depends(require_roles(models.UserRole.manager))],
):
    level = db.get(models.Level, level_id)
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(level, key, value)
    log_audit(db, manager.id, "UPDATE", "level", entity_id=str(level.id))
    db.commit()
    db.refresh(level)
    return level


@app.post("/skills", response_model=SkillOut)
def create_skill(
    payload: SkillCreate,
    db: Annotated[Session, Depends(get_db)],
    manager: Annotated[models.User, Depends(require_roles(models.UserRole.manager))],
):
    if not db.get(models.Level, payload.level_id):
        raise HTTPException(status_code=404, detail="Level not found")
    skill = models.Skill(**payload.model_dump())
    db.add(skill)
    log_audit(db, manager.id, "CREATE", "skill", details=payload.name)
    db.commit()
    db.refresh(skill)
    return skill


@app.get("/skills", response_model=list[SkillOut])
def list_skills(
    db: Annotated[Session, Depends(get_db)],
    level_id: int | None = None,
    active: bool | None = None,
):
    stmt = select(models.Skill)
    if level_id is not None:
        stmt = stmt.where(models.Skill.level_id == level_id)
    if active is not None:
        stmt = stmt.where(models.Skill.active == active)
    return list(db.scalars(stmt.order_by(models.Skill.name)).all())


@app.patch("/skills/{skill_id}", response_model=SkillOut)
def update_skill(
    skill_id: int,
    payload: SkillUpdate,
    db: Annotated[Session, Depends(get_db)],
    manager: Annotated[models.User, Depends(require_roles(models.UserRole.manager))],
):
    skill = db.get(models.Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    data = payload.model_dump(exclude_unset=True)
    if "level_id" in data and data["level_id"] is not None and not db.get(models.Level, data["level_id"]):
        raise HTTPException(status_code=404, detail="Level not found")
    for key, value in data.items():
        setattr(skill, key, value)
    log_audit(db, manager.id, "UPDATE", "skill", entity_id=str(skill.id))
    db.commit()
    db.refresh(skill)
    return skill


@app.post("/attributes", response_model=AttributeOut)
def create_attribute(
    payload: AttributeCreate,
    db: Annotated[Session, Depends(get_db)],
    manager: Annotated[models.User, Depends(require_roles(models.UserRole.manager))],
):
    if db.scalar(select(models.Attribute).where(models.Attribute.name == payload.name)):
        raise HTTPException(status_code=400, detail="Attribute name already exists")
    attribute = models.Attribute(**payload.model_dump())
    db.add(attribute)
    log_audit(db, manager.id, "CREATE", "attribute", details=payload.name)
    db.commit()
    db.refresh(attribute)
    return attribute


@app.get("/attributes", response_model=list[AttributeOut])
def list_attributes(
    db: Annotated[Session, Depends(get_db)],
    active: bool | None = None,
):
    stmt = select(models.Attribute)
    if active is not None:
        stmt = stmt.where(models.Attribute.active == active)
    return list(db.scalars(stmt.order_by(models.Attribute.name)).all())


@app.patch("/attributes/{attribute_id}", response_model=AttributeOut)
def update_attribute(
    attribute_id: int,
    payload: AttributeUpdate,
    db: Annotated[Session, Depends(get_db)],
    manager: Annotated[models.User, Depends(require_roles(models.UserRole.manager))],
):
    attribute = db.get(models.Attribute, attribute_id)
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(attribute, key, value)
    log_audit(db, manager.id, "UPDATE", "attribute", entity_id=str(attribute.id))
    db.commit()
    db.refresh(attribute)
    return attribute


@app.post("/templates", response_model=TemplateOut)
def create_template(
    payload: TemplateCreate,
    db: Annotated[Session, Depends(get_db)],
    manager: Annotated[models.User, Depends(require_roles(models.UserRole.manager))],
):
    if payload.level_id is not None and not db.get(models.Level, payload.level_id):
        raise HTTPException(status_code=404, detail="Level not found")
    if payload.skill_id is not None and not db.get(models.Skill, payload.skill_id):
        raise HTTPException(status_code=404, detail="Skill not found")
    attributes = list(db.scalars(select(models.Attribute).where(models.Attribute.id.in_(payload.attribute_ids))).all())
    if len(attributes) != len(set(payload.attribute_ids)):
        raise HTTPException(status_code=400, detail="One or more attribute_ids are invalid")
    template = models.Template(
        name=payload.name,
        level_id=payload.level_id,
        skill_id=payload.skill_id,
        active=payload.active,
    )
    template.template_attributes = [
        models.TemplateAttribute(attribute_id=attr_id, sort_order=idx + 1) for idx, attr_id in enumerate(payload.attribute_ids)
    ]
    db.add(template)
    log_audit(db, manager.id, "CREATE", "template", details=payload.name)
    db.commit()
    db.refresh(template)
    return template


@app.get("/templates", response_model=list[TemplateOut])
def list_templates(
    db: Annotated[Session, Depends(get_db)],
    level_id: int | None = None,
    skill_id: int | None = None,
    active: bool | None = None,
):
    stmt = select(models.Template).options(joinedload(models.Template.template_attributes))
    if level_id is not None:
        stmt = stmt.where(models.Template.level_id == level_id)
    if skill_id is not None:
        stmt = stmt.where(models.Template.skill_id == skill_id)
    if active is not None:
        stmt = stmt.where(models.Template.active == active)
    return list(db.scalars(stmt.order_by(models.Template.name)).unique().all())


def resolve_template(db: Session, level_id: int | None, skill_id: int | None) -> models.Template | None:
    conditions = []
    if level_id is not None:
        conditions.append(models.Template.level_id == level_id)
    if skill_id is not None:
        conditions.append(models.Template.skill_id == skill_id)

    stmt = select(models.Template).options(joinedload(models.Template.template_attributes)).where(models.Template.active == True)  # noqa: E712
    if conditions:
        stmt = stmt.where(and_(*conditions))
    return db.scalar(stmt.order_by(models.Template.id.desc()))


def apply_evaluation_filters(
    stmt,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    level_id: int | None = None,
    skill_id: int | None = None,
    supervisor_id: int | None = None,
    instructor_id: int | None = None,
    status_filter: models.EvaluationStatus | None = None,
):
    if date_from:
        stmt = stmt.where(models.Evaluation.session_date >= date_from)
    if date_to:
        stmt = stmt.where(models.Evaluation.session_date <= date_to)
    if level_id:
        stmt = stmt.where(models.Evaluation.level_id == level_id)
    if skill_id:
        stmt = stmt.where(models.Evaluation.skill_id == skill_id)
    if supervisor_id:
        stmt = stmt.where(models.Evaluation.supervisor_id == supervisor_id)
    if instructor_id:
        stmt = stmt.where(models.Evaluation.instructor_id == instructor_id)
    if status_filter:
        stmt = stmt.where(models.Evaluation.status == status_filter)
    return stmt


def apply_evaluation_sort(stmt, sort_by: str, sort_dir: str):
    sortable_columns = {
        "id": models.Evaluation.id,
        "created_at": models.Evaluation.created_at,
        "session_date": models.Evaluation.session_date,
        "submitted_at": models.Evaluation.submitted_at,
        "status": models.Evaluation.status,
    }
    if sort_by not in sortable_columns:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by: {sort_by}")
    if sort_dir not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail=f"Invalid sort_dir: {sort_dir}")
    column = sortable_columns[sort_by]
    return stmt.order_by(asc(column) if sort_dir == "asc" else desc(column))


@app.post("/evaluations/draft", response_model=EvaluationOut)
def create_evaluation_draft(
    payload: EvaluationCreate,
    db: Annotated[Session, Depends(get_db)],
    supervisor: Annotated[models.User, Depends(require_roles(models.UserRole.supervisor))],
):
    instructor = db.get(models.User, payload.instructor_id)
    if not instructor or instructor.role != models.UserRole.instructor or not instructor.active:
        raise HTTPException(status_code=400, detail="instructor_id must reference an active INSTRUCTOR")
    if payload.level_id is not None and not db.get(models.Level, payload.level_id):
        raise HTTPException(status_code=404, detail="Level not found")
    if payload.skill_id is not None and not db.get(models.Skill, payload.skill_id):
        raise HTTPException(status_code=404, detail="Skill not found")

    evaluation = models.Evaluation(
        instructor_id=payload.instructor_id,
        supervisor_id=supervisor.id,
        level_id=payload.level_id,
        skill_id=payload.skill_id,
        session_label=payload.session_label,
        session_date=payload.session_date,
        notes=payload.notes,
        status=models.EvaluationStatus.draft,
    )
    _replace_ratings(db, evaluation, payload.ratings)
    db.add(evaluation)
    log_audit(db, supervisor.id, "CREATE_DRAFT", "evaluation")
    db.commit()
    db.refresh(evaluation)
    return evaluation


@app.patch("/evaluations/{evaluation_id}/draft", response_model=EvaluationOut)
def update_evaluation_draft(
    evaluation_id: int,
    payload: EvaluationUpdateDraft,
    db: Annotated[Session, Depends(get_db)],
    supervisor: Annotated[models.User, Depends(require_roles(models.UserRole.supervisor))],
):
    evaluation = db.get(models.Evaluation, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if evaluation.supervisor_id != supervisor.id:
        raise HTTPException(status_code=403, detail="Can only edit your own drafts")
    if evaluation.status != models.EvaluationStatus.draft:
        raise HTTPException(status_code=400, detail="Only DRAFT evaluations can be edited")

    data = payload.model_dump(exclude_unset=True)
    ratings = data.pop("ratings", None)
    for key, value in data.items():
        setattr(evaluation, key, value)
    if ratings is not None:
        _replace_ratings(db, evaluation, [RatingInput(**rating) for rating in ratings])
    log_audit(db, supervisor.id, "UPDATE_DRAFT", "evaluation", entity_id=str(evaluation.id))
    db.commit()
    db.refresh(evaluation)
    return evaluation


@app.post("/evaluations/{evaluation_id}/submit", response_model=EvaluationOut)
def submit_evaluation(
    evaluation_id: int,
    db: Annotated[Session, Depends(get_db)],
    supervisor: Annotated[models.User, Depends(require_roles(models.UserRole.supervisor))],
):
    evaluation = db.get(models.Evaluation, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if evaluation.supervisor_id != supervisor.id:
        raise HTTPException(status_code=403, detail="Can only submit your own evaluations")
    if evaluation.status != models.EvaluationStatus.draft:
        raise HTTPException(status_code=400, detail="Evaluation is already submitted")

    template = resolve_template(db, evaluation.level_id, evaluation.skill_id)
    if template and template.template_attributes:
        required_ids = {ta.attribute_id for ta in template.template_attributes}
        rated_ids = {rating.attribute_id for rating in evaluation.ratings}
        if not required_ids.issubset(rated_ids):
            raise HTTPException(status_code=400, detail="Missing one or more required template ratings")

    evaluation.status = models.EvaluationStatus.submitted
    evaluation.submitted_at = datetime.now(timezone.utc)
    log_audit(db, supervisor.id, "SUBMIT", "evaluation", entity_id=str(evaluation.id))
    db.commit()
    db.refresh(evaluation)
    return evaluation


@app.get("/evaluations/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation(
    evaluation_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    evaluation = db.scalar(
        select(models.Evaluation)
        .options(joinedload(models.Evaluation.ratings))
        .where(models.Evaluation.id == evaluation_id)
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if user.role == models.UserRole.instructor and evaluation.instructor_id != user.id:
        raise HTTPException(status_code=403, detail="You can only view your own evaluations")
    if user.role == models.UserRole.supervisor and evaluation.supervisor_id != user.id:
        raise HTTPException(status_code=403, detail="You can only view your own evaluations")
    return evaluation


@app.get("/me/evaluations", response_model=list[EvaluationOut])
def list_my_evaluations(
    db: Annotated[Session, Depends(get_db)],
    instructor: Annotated[models.User, Depends(require_roles(models.UserRole.instructor))],
    date_from: date | None = None,
    date_to: date | None = None,
    level_id: int | None = None,
    skill_id: int | None = None,
    supervisor_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="session_date"),
    sort_dir: str = Query(default="desc"),
):
    stmt = (
        select(models.Evaluation)
        .options(joinedload(models.Evaluation.ratings))
        .where(models.Evaluation.instructor_id == instructor.id, models.Evaluation.status == models.EvaluationStatus.submitted)
    )
    stmt = apply_evaluation_filters(
        stmt,
        date_from=date_from,
        date_to=date_to,
        level_id=level_id,
        skill_id=skill_id,
        supervisor_id=supervisor_id,
        status_filter=models.EvaluationStatus.submitted,
    )
    stmt = apply_evaluation_sort(stmt, sort_by=sort_by, sort_dir=sort_dir)
    return list(db.scalars(stmt.offset(offset).limit(limit)).unique().all())


@app.get("/me/evaluations/trends", response_model=list[TrendPoint])
def my_evaluation_trends(
    db: Annotated[Session, Depends(get_db)],
    instructor: Annotated[models.User, Depends(require_roles(models.UserRole.instructor))],
    date_from: date | None = None,
    date_to: date | None = None,
    level_id: int | None = None,
    skill_id: int | None = None,
    supervisor_id: int | None = None,
):
    stmt = (
        select(models.Evaluation)
        .options(joinedload(models.Evaluation.ratings))
        .where(models.Evaluation.instructor_id == instructor.id, models.Evaluation.status == models.EvaluationStatus.submitted)
    )
    stmt = apply_evaluation_filters(
        stmt,
        date_from=date_from,
        date_to=date_to,
        level_id=level_id,
        skill_id=skill_id,
        supervisor_id=supervisor_id,
        status_filter=models.EvaluationStatus.submitted,
    )
    evaluations = list(db.scalars(stmt).unique().all())

    period_totals: dict[str, float] = {}
    period_counts: dict[str, int] = {}
    for evaluation in evaluations:
        if not evaluation.ratings:
            continue
        period = evaluation.session_date.strftime("%Y-%m")
        avg_for_eval = sum(r.rating_value for r in evaluation.ratings) / len(evaluation.ratings)
        period_totals[period] = period_totals.get(period, 0.0) + avg_for_eval
        period_counts[period] = period_counts.get(period, 0) + 1

    trends = [
        TrendPoint(
            period=period,
            evaluation_count=period_counts[period],
            average_rating=round(period_totals[period] / period_counts[period], 2),
        )
        for period in sorted(period_totals.keys())
    ]
    return trends


@app.get("/manager/evaluations", response_model=list[EvaluationOut])
def manager_list_evaluations(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[models.User, Depends(require_roles(models.UserRole.manager))],
    date_from: date | None = None,
    date_to: date | None = None,
    level_id: int | None = None,
    skill_id: int | None = None,
    supervisor_id: int | None = None,
    instructor_id: int | None = None,
    status_filter: models.EvaluationStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
):
    stmt = select(models.Evaluation).options(joinedload(models.Evaluation.ratings))
    stmt = apply_evaluation_filters(
        stmt,
        date_from=date_from,
        date_to=date_to,
        level_id=level_id,
        skill_id=skill_id,
        supervisor_id=supervisor_id,
        instructor_id=instructor_id,
        status_filter=status_filter,
    )
    stmt = apply_evaluation_sort(stmt, sort_by=sort_by, sort_dir=sort_dir)
    return list(db.scalars(stmt.offset(offset).limit(limit)).unique().all())


@app.get("/supervisor/evaluations", response_model=list[EvaluationOut])
def supervisor_list_evaluations(
    db: Annotated[Session, Depends(get_db)],
    supervisor: Annotated[models.User, Depends(require_roles(models.UserRole.supervisor))],
    status_filter: models.EvaluationStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
):
    stmt = (
        select(models.Evaluation)
        .options(joinedload(models.Evaluation.ratings))
        .where(models.Evaluation.supervisor_id == supervisor.id)
    )
    stmt = apply_evaluation_filters(stmt, status_filter=status_filter)
    stmt = apply_evaluation_sort(stmt, sort_by=sort_by, sort_dir=sort_dir)
    return list(db.scalars(stmt.offset(offset).limit(limit)).unique().all())


@app.get("/exports/evaluations.csv")
def export_evaluations_csv(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[models.User, Depends(require_roles(models.UserRole.manager))],
    date_from: date | None = None,
    date_to: date | None = None,
    level_id: int | None = None,
    skill_id: int | None = None,
    supervisor_id: int | None = None,
    instructor_id: int | None = None,
    status_filter: models.EvaluationStatus | None = Query(default=None, alias="status"),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
):
    stmt = select(models.Evaluation).options(joinedload(models.Evaluation.ratings))
    stmt = apply_evaluation_filters(
        stmt,
        date_from=date_from,
        date_to=date_to,
        level_id=level_id,
        skill_id=skill_id,
        supervisor_id=supervisor_id,
        instructor_id=instructor_id,
        status_filter=status_filter,
    )
    stmt = apply_evaluation_sort(stmt, sort_by=sort_by, sort_dir=sort_dir)
    evaluations = list(db.scalars(stmt).unique().all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "evaluation_id",
            "instructor_id",
            "supervisor_id",
            "level_id",
            "skill_id",
            "session_label",
            "session_date",
            "status",
            "submitted_at",
            "notes",
            "ratings",
        ]
    )
    for ev in evaluations:
        ratings_value = "; ".join(f"{rating.attribute_id}:{rating.rating_value}" for rating in ev.ratings)
        writer.writerow(
            [
                ev.id,
                ev.instructor_id,
                ev.supervisor_id,
                ev.level_id,
                ev.skill_id,
                ev.session_label or "",
                ev.session_date.isoformat(),
                ev.status.value,
                ev.submitted_at.isoformat() if ev.submitted_at else "",
                (ev.notes or "").replace("\n", " ").strip(),
                ratings_value,
            ]
        )

    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    headers = {"Content-Disposition": f'attachment; filename="evaluations_{timestamp}.csv"'}
    return StreamingResponse(output, media_type="text/csv", headers=headers)
