import logging
import smtplib
from datetime import date, datetime, timezone
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import asc, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from config import settings
from db import get_db
from deps import require_roles
from models import (
    Attribute,
    Evaluation,
    Level,
    ReevaluationRequest,
    ReevaluationStatus,
    Skill,
    SkillAttribute,
    User,
    UserRole,
)
from schemas import (
    AttributeCreate,
    AttributeOut,
    AttributeUpdate,
    EvaluationDetailOut,
    ReevaluationRequestOut,
    EvaluationSummaryOut,
    EvaluationUpdate,
    LevelBase,
    LevelOut,
    LevelUpdate,
    SkillAttributeIn,
    SkillBase,
    SkillOut,
    SkillUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
    ExportEmailRequest,
)
from security import hash_password
from services import (
    evaluation_detail_row,
    evaluation_query_with_joins,
    evaluation_summary_row,
    evaluations_to_csv,
    recalculate_final_grade,
    reevaluation_request_row,
    sync_ratings,
    sync_reevaluation_state,
)


router = APIRouter(prefix="/manager", tags=["manager"])
manager_guard = Depends(require_roles(UserRole.MANAGER))
logger = logging.getLogger(__name__)


def apply_evaluation_filters(
    stmt,
    *,
    instructor_id: int | None = None,
    supervisor_id: int | None = None,
    skill_id: int | None = None,
    final_grade: int | None = None,
    needs_reevaluation: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    filters = []
    if instructor_id:
        filters.append(Evaluation.instructor_id == instructor_id)
    if supervisor_id:
        filters.append(Evaluation.supervisor_id == supervisor_id)
    if skill_id:
        filters.append(Evaluation.skill_id == skill_id)
    if final_grade is not None:
        filters.append(Evaluation.final_grade == final_grade)
    if needs_reevaluation is not None:
        filters.append(Evaluation.needs_reevaluation.is_(needs_reevaluation))
    if date_from:
        filters.append(Evaluation.created_at >= date_from)
    if date_to:
        filters.append(Evaluation.created_at <= date_to)
    if filters:
        from sqlalchemy import and_
        stmt = stmt.where(and_(*filters))
    return stmt


def apply_evaluation_sorting(stmt, *, sort_by: str, sort_dir: str):
    sortable = {
        "id": Evaluation.id,
        "created_at": Evaluation.created_at,
        "updated_at": Evaluation.updated_at,
        "instructor_id": Evaluation.instructor_id,
        "supervisor_id": Evaluation.supervisor_id,
        "skill_id": Evaluation.skill_id,
        "final_grade": Evaluation.final_grade,
    }
    if sort_by not in sortable:
        raise HTTPException(status_code=400, detail="Invalid sort_by")
    if sort_dir not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Invalid sort_dir")
    order_col = sortable[sort_by]
    return stmt.order_by(None).order_by(asc(order_col) if sort_dir == "asc" else desc(order_col), desc(Evaluation.id))


def send_csv_email(recipients: list[str], subject: str, message: str, csv_text: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        logger.warning("Email export requested but SMTP is not configured")
        raise HTTPException(status_code=501, detail="Email not configured")

    email_message = EmailMessage()
    email_message["Subject"] = subject
    email_message["From"] = settings.smtp_from_email
    email_message["To"] = ", ".join(recipients)
    email_message.set_content(message)
    email_message.add_attachment(
        csv_text.encode("utf-8"),
        maintype="text",
        subtype="csv",
        filename="evaluations.csv",
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(email_message)
    except Exception as exc:
        logger.exception("Failed to send evaluation export email")
        raise HTTPException(status_code=500, detail="Failed to send email") from exc


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserOut], dependencies=[manager_guard])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[User]:
    return db.scalars(
        select(User).where(User.school_id == current_user.school_id).order_by(User.full_name.asc())
    ).all()


@router.post("/users", response_model=UserOut, dependencies=[manager_guard])
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> User:
    normalized_email = payload.email.strip().lower()
    if db.scalar(
        select(User.id).where(
            User.school_id == current_user.school_id,
            User.email == normalized_email,
        )
    ):
        raise HTTPException(status_code=400, detail="Email already exists")
    user = User(
        school_id=current_user.school_id,
        full_name=payload.full_name,
        email=normalized_email,
        phone=payload.phone.strip() if payload.phone else None,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserOut, dependencies=[manager_guard])
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> User:
    user = db.scalar(select(User).where(User.id == user_id, User.school_id == current_user.school_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates:
        normalized_email = updates["email"].strip().lower()
        existing = db.scalar(
            select(User.id).where(
                User.school_id == current_user.school_id,
                User.email == normalized_email,
                User.id != user.id,
            )
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        updates["email"] = normalized_email
    if "phone" in updates and updates["phone"] is not None:
        updates["phone"] = updates["phone"].strip() or None
    if "password" in updates:
        raw_password = updates.pop("password")
        if raw_password:
            user.password_hash = hash_password(raw_password)
    for field, value in updates.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204, dependencies=[manager_guard])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> None:
    user = db.scalar(select(User).where(User.id == user_id, User.school_id == current_user.school_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    try:
        db.delete(user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="User cannot be deleted because they are referenced by existing records",
        ) from exc


# ── Levels ────────────────────────────────────────────────────────────────────

@router.get("/levels", response_model=list[LevelOut], dependencies=[manager_guard])
def list_levels(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[Level]:
    return db.scalars(
        select(Level)
        .where(Level.school_id == current_user.school_id, Level.is_active.is_(True))
        .order_by(Level.sort_order.asc(), Level.name.asc())
    ).all()


@router.post("/levels", response_model=LevelOut, dependencies=[manager_guard])
def create_level(
    payload: LevelBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Level:
    level = Level(school_id=current_user.school_id, name=payload.name.strip(), sort_order=payload.sort_order)
    db.add(level)
    db.commit()
    db.refresh(level)
    return level


@router.put("/levels/{level_id}", response_model=LevelOut, dependencies=[manager_guard])
def update_level(
    level_id: int,
    payload: LevelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Level:
    level = db.scalar(
        select(Level).where(
            Level.id == level_id,
            Level.school_id == current_user.school_id,
            Level.is_active.is_(True),
        )
    )
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(level, field, value)
    db.commit()
    db.refresh(level)
    return level


@router.delete("/levels/{level_id}", status_code=204, dependencies=[manager_guard])
def delete_level(
    level_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> None:
    level = db.scalar(
        select(Level).where(
            Level.id == level_id,
            Level.school_id == current_user.school_id,
            Level.is_active.is_(True),
        )
    )
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    level.is_active = False
    for skill in db.scalars(select(Skill).where(Skill.level_id == level.id)).all():
        skill.is_active = False
    db.commit()


# ── Skills ────────────────────────────────────────────────────────────────────

@router.get("/skills", response_model=list[SkillOut], dependencies=[manager_guard])
def list_skills(
    level_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[Skill]:
    stmt = (
        select(Skill)
        .join(Level, Skill.level_id == Level.id)
        .where(
            Level.school_id == current_user.school_id,
            Level.is_active.is_(True),
            Skill.is_active.is_(True),
        )
    )
    if level_id:
        stmt = stmt.where(Skill.level_id == level_id)
    return db.scalars(stmt.order_by(Skill.sort_order.asc(), Skill.name.asc())).all()


@router.post("/skills", response_model=SkillOut, dependencies=[manager_guard])
def create_skill(
    payload: SkillBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Skill:
    level = db.scalar(
        select(Level).where(
            Level.id == payload.level_id,
            Level.school_id == current_user.school_id,
            Level.is_active.is_(True),
        )
    )
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    skill = Skill(
        level_id=payload.level_id,
        name=payload.name.strip(),
        sort_order=payload.sort_order,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.put("/skills/{skill_id}", response_model=SkillOut, dependencies=[manager_guard])
def update_skill(
    skill_id: int,
    payload: SkillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Skill:
    skill = db.scalar(
        select(Skill)
        .join(Level, Skill.level_id == Level.id)
        .where(
            Skill.id == skill_id,
            Skill.is_active.is_(True),
            Level.school_id == current_user.school_id,
            Level.is_active.is_(True),
        )
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    updates = payload.model_dump(exclude_unset=True)
    if "level_id" in updates and not db.scalar(
        select(Level).where(
            Level.id == updates["level_id"],
            Level.school_id == current_user.school_id,
            Level.is_active.is_(True),
        )
    ):
        raise HTTPException(status_code=404, detail="Level not found")
    for field, value in updates.items():
        setattr(skill, field, value)
    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/skills/{skill_id}", status_code=204, dependencies=[manager_guard])
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> None:
    skill = db.scalar(
        select(Skill)
        .join(Level, Skill.level_id == Level.id)
        .where(
            Skill.id == skill_id,
            Skill.is_active.is_(True),
            Level.school_id == current_user.school_id,
            Level.is_active.is_(True),
        )
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.is_active = False
    db.commit()


# ── Skill ↔ Attribute links ───────────────────────────────────────────────────

@router.get("/skills/{skill_id}/attributes", response_model=list[AttributeOut], dependencies=[manager_guard])
def list_skill_attributes(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[Attribute]:
    skill = db.scalar(
        select(Skill)
        .join(Level, Skill.level_id == Level.id)
        .where(
            Skill.id == skill_id,
            Skill.is_active.is_(True),
            Level.school_id == current_user.school_id,
            Level.is_active.is_(True),
        )
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return db.scalars(
        select(Attribute)
        .join(SkillAttribute, Attribute.id == SkillAttribute.attribute_id)
        .where(SkillAttribute.skill_id == skill_id, Attribute.is_active.is_(True))
        .order_by(Attribute.sort_order.asc(), Attribute.name.asc())
    ).all()


@router.post("/skills/{skill_id}/attributes", status_code=204, dependencies=[manager_guard])
def add_skill_attribute(
    skill_id: int,
    payload: SkillAttributeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> None:
    skill = db.scalar(
        select(Skill)
        .join(Level, Skill.level_id == Level.id)
        .where(
            Skill.id == skill_id,
            Skill.is_active.is_(True),
            Level.school_id == current_user.school_id,
            Level.is_active.is_(True),
        )
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    attribute = db.scalar(
        select(Attribute).where(
            Attribute.id == payload.attribute_id,
            Attribute.school_id == current_user.school_id,
            Attribute.is_active.is_(True),
        )
    )
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    existing = db.scalar(
        select(SkillAttribute).where(
            SkillAttribute.skill_id == skill_id,
            SkillAttribute.attribute_id == payload.attribute_id,
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="Attribute already linked to this skill")
    db.add(SkillAttribute(skill_id=skill_id, attribute_id=payload.attribute_id))
    db.commit()


@router.delete("/skills/{skill_id}/attributes/{attribute_id}", status_code=204, dependencies=[manager_guard])
def remove_skill_attribute(
    skill_id: int,
    attribute_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> None:
    skill = db.scalar(
        select(Skill)
        .join(Level, Skill.level_id == Level.id)
        .where(
            Skill.id == skill_id,
            Skill.is_active.is_(True),
            Level.school_id == current_user.school_id,
            Level.is_active.is_(True),
        )
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    link = db.scalar(
        select(SkillAttribute).where(
            SkillAttribute.skill_id == skill_id,
            SkillAttribute.attribute_id == attribute_id,
        )
    )
    if not link:
        raise HTTPException(status_code=404, detail="Attribute not linked to this skill")
    db.delete(link)
    db.commit()


# ── Attributes ────────────────────────────────────────────────────────────────

@router.get("/attributes", response_model=list[AttributeOut], dependencies=[manager_guard])
def list_attributes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[Attribute]:
    return db.scalars(
        select(Attribute)
        .where(Attribute.school_id == current_user.school_id, Attribute.is_active.is_(True))
        .order_by(Attribute.sort_order.asc(), Attribute.name.asc())
    ).all()


@router.post("/attributes", response_model=AttributeOut, dependencies=[manager_guard])
def create_attribute(
    payload: AttributeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Attribute:
    attribute = Attribute(
        school_id=current_user.school_id,
        name=payload.name.strip(),
        description=payload.description,
        sort_order=payload.sort_order,
    )
    db.add(attribute)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Attribute name already exists") from exc
    db.refresh(attribute)
    return attribute


@router.put("/attributes/{attribute_id}", response_model=AttributeOut, dependencies=[manager_guard])
def update_attribute(
    attribute_id: int,
    payload: AttributeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Attribute:
    attribute = db.scalar(
        select(Attribute).where(
            Attribute.id == attribute_id,
            Attribute.school_id == current_user.school_id,
            Attribute.is_active.is_(True),
        )
    )
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(attribute, field, value)
    db.commit()
    db.refresh(attribute)
    return attribute


@router.delete("/attributes/{attribute_id}", status_code=204, dependencies=[manager_guard])
def delete_attribute(
    attribute_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> None:
    attribute = db.scalar(
        select(Attribute).where(
            Attribute.id == attribute_id,
            Attribute.school_id == current_user.school_id,
            Attribute.is_active.is_(True),
        )
    )
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    attribute.is_active = False
    db.commit()


# ── Evaluations ───────────────────────────────────────────────────────────────

@router.get("/evaluations/{evaluation_id}", response_model=EvaluationDetailOut, dependencies=[manager_guard])
def get_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> EvaluationDetailOut:
    evaluation = db.scalar(
        evaluation_query_with_joins(current_user.school_id).where(Evaluation.id == evaluation_id)
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation_detail_row(evaluation)


@router.put("/evaluations/{evaluation_id}", response_model=EvaluationDetailOut, dependencies=[manager_guard])
def update_evaluation(
    evaluation_id: int,
    payload: EvaluationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> EvaluationDetailOut:
    evaluation = db.scalar(
        select(Evaluation).where(
            Evaluation.id == evaluation_id,
            Evaluation.school_id == current_user.school_id,
        )
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    evaluation.notes = payload.notes
    if payload.ratings is not None:
        sync_ratings(db, evaluation, [(r.attribute_id, r.rating, r.comment) for r in payload.ratings])
    db.flush()
    recalculate_final_grade(db, evaluation)
    sync_reevaluation_state(
        db,
        evaluation,
        force=bool(payload.needs_reevaluation),
        notes=payload.notes,
    )
    db.commit()

    full = db.scalar(evaluation_query_with_joins(current_user.school_id).where(Evaluation.id == evaluation.id))
    if not full:
        raise HTTPException(status_code=500, detail="Failed to reload evaluation")
    return evaluation_detail_row(full)


@router.delete("/evaluations/{evaluation_id}", status_code=204, dependencies=[manager_guard])
def delete_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> None:
    evaluation = db.scalar(
        select(Evaluation).where(
            Evaluation.id == evaluation_id,
            Evaluation.school_id == current_user.school_id,
        )
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    db.delete(evaluation)
    db.commit()


@router.get("/evaluations", response_model=list[EvaluationSummaryOut], dependencies=[manager_guard])
def list_evaluations(
    instructor_id: int | None = None,
    supervisor_id: int | None = None,
    skill_id: int | None = None,
    final_grade: int | None = Query(default=None, ge=1, le=5),
    needs_reevaluation: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[EvaluationSummaryOut]:
    stmt = evaluation_query_with_joins(current_user.school_id)
    stmt = apply_evaluation_filters(
        stmt,
        instructor_id=instructor_id,
        supervisor_id=supervisor_id,
        skill_id=skill_id,
        final_grade=final_grade,
        needs_reevaluation=needs_reevaluation,
        date_from=date_from,
        date_to=date_to,
    )
    stmt = apply_evaluation_sorting(stmt, sort_by=sort_by, sort_dir=sort_dir)
    evaluations = db.scalars(stmt.limit(limit).offset(offset)).all()
    return [evaluation_summary_row(item) for item in evaluations]


@router.get("/reevaluations", response_model=list[ReevaluationRequestOut], dependencies=[manager_guard])
def list_reevaluations(
    instructor_id: int | None = None,
    skill_id: int | None = None,
    status: ReevaluationStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[ReevaluationRequestOut]:
    stmt = (
        select(ReevaluationRequest)
        .where(ReevaluationRequest.school_id == current_user.school_id)
        .options(
            joinedload(ReevaluationRequest.instructor),
            joinedload(ReevaluationRequest.supervisor),
            joinedload(ReevaluationRequest.skill),
        )
        .order_by(ReevaluationRequest.requested_at.desc(), ReevaluationRequest.id.desc())
    )
    if instructor_id is not None:
        stmt = stmt.where(ReevaluationRequest.instructor_id == instructor_id)
    if skill_id is not None:
        stmt = stmt.where(ReevaluationRequest.skill_id == skill_id)
    if status is not None:
        stmt = stmt.where(ReevaluationRequest.status == status)
    requests = db.scalars(stmt).all()
    return [reevaluation_request_row(item) for item in requests]


@router.put("/reevaluations/{request_id}/complete", response_model=ReevaluationRequestOut, dependencies=[manager_guard])
def complete_reevaluation(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> ReevaluationRequestOut:
    request = db.scalar(
        select(ReevaluationRequest)
        .where(
            ReevaluationRequest.id == request_id,
            ReevaluationRequest.school_id == current_user.school_id,
            ReevaluationRequest.status == ReevaluationStatus.OPEN,
        )
        .options(
            joinedload(ReevaluationRequest.instructor),
            joinedload(ReevaluationRequest.supervisor),
            joinedload(ReevaluationRequest.skill),
        )
    )
    if not request:
        raise HTTPException(status_code=404, detail="Reevaluation request not found")

    request.status = ReevaluationStatus.COMPLETED
    request.completed_at = datetime.now(timezone.utc)

    latest_evaluation = db.scalar(
        select(Evaluation)
        .where(
            Evaluation.school_id == current_user.school_id,
            Evaluation.instructor_id == request.instructor_id,
            Evaluation.skill_id == request.skill_id,
        )
        .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
    )
    if latest_evaluation:
        latest_evaluation.needs_reevaluation = False

    db.commit()
    db.refresh(request)
    return reevaluation_request_row(request)


@router.get("/exports/evaluations.csv", dependencies=[manager_guard])
def export_evaluations_csv(
    instructor_id: int | None = None,
    supervisor_id: int | None = None,
    skill_id: int | None = None,
    final_grade: int | None = Query(default=None, ge=1, le=5),
    needs_reevaluation: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Response:
    stmt = evaluation_query_with_joins(current_user.school_id)
    stmt = apply_evaluation_filters(
        stmt,
        instructor_id=instructor_id,
        supervisor_id=supervisor_id,
        skill_id=skill_id,
        final_grade=final_grade,
        needs_reevaluation=needs_reevaluation,
        date_from=date_from,
        date_to=date_to,
    )
    stmt = apply_evaluation_sorting(stmt, sort_by=sort_by, sort_dir=sort_dir)
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)
    evaluations = db.scalars(stmt).all()
    csv_text = evaluations_to_csv(evaluations)
    headers = {"Content-Disposition": "attachment; filename=evaluations.csv"}
    return Response(content=csv_text, media_type="text/csv", headers=headers)


@router.post("/exports/evaluations/email", dependencies=[manager_guard])
def email_evaluations_csv(
    payload: ExportEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> dict[str, str]:
    filters = payload.filters
    stmt = evaluation_query_with_joins(current_user.school_id)
    if filters:
        stmt = apply_evaluation_filters(
            stmt,
            instructor_id=filters.instructor_id,
            supervisor_id=filters.supervisor_id,
            skill_id=filters.skill_id,
            final_grade=filters.final_grade,
            needs_reevaluation=filters.needs_reevaluation,
            date_from=filters.date_from,
            date_to=filters.date_to,
        )
        stmt = apply_evaluation_sorting(
            stmt,
            sort_by=filters.sort_by or "created_at",
            sort_dir=filters.sort_dir or "desc",
        )
        if filters.limit is not None:
            stmt = stmt.limit(filters.limit)
        if filters.offset is not None:
            stmt = stmt.offset(filters.offset)
    evaluations = db.scalars(stmt).all()
    csv_text = evaluations_to_csv(evaluations)
    send_csv_email(
        recipients=[str(item) for item in payload.to],
        subject=payload.subject or "Propel Swim Evaluations Export",
        message=payload.message or "Attached is the evaluations export CSV.",
        csv_text=csv_text,
    )
    return {"detail": "Email sent"}
