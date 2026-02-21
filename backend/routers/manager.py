from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, asc, desc, select
from sqlalchemy.orm import Session, selectinload

from db import get_db
from deps import require_roles
from models import (
    Attribute,
    Evaluation,
    EvaluationRating,
    EvaluationStatus,
    Level,
    Skill,
    Template,
    TemplateAttribute,
    User,
    UserRole,
)
from schemas import (
    AttributeOut,
    EvaluationSummaryOut,
    LevelBase,
    LevelOut,
    LevelUpdate,
    SkillBase,
    SkillOut,
    SkillUpdate,
    TemplateCreate,
    TemplateOut,
    TemplateUpdate,
    UserCreate,
    UserOut,
)
from security import hash_password
from services import (
    evaluation_query_with_joins,
    evaluation_summary_row,
    evaluations_to_csv,
    template_attributes_replace,
    template_out,
)


router = APIRouter(prefix="/manager", tags=["manager"])
manager_guard = Depends(require_roles(UserRole.MANAGER))


@router.get("/users", response_model=list[UserOut], dependencies=[manager_guard])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[User]:
    return db.scalars(
        select(User).where(User.school_id == current_user.school_id).order_by(User.name.asc())
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
        name=payload.name,
        email=normalized_email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        active=payload.active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/levels", response_model=list[LevelOut], dependencies=[manager_guard])
def list_levels(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[Level]:
    return db.scalars(
        select(Level).where(Level.school_id == current_user.school_id).order_by(Level.name.asc())
    ).all()


@router.post("/levels", response_model=LevelOut, dependencies=[manager_guard])
def create_level(
    payload: LevelBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Level:
    level = Level(school_id=current_user.school_id, name=payload.name.strip(), active=payload.active)
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
    level = db.scalar(select(Level).where(Level.id == level_id, Level.school_id == current_user.school_id))
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(level, field, value)
    db.commit()
    db.refresh(level)
    return level


@router.get("/skills", response_model=list[SkillOut], dependencies=[manager_guard])
def list_skills(
    level_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[Skill]:
    stmt = select(Skill).where(Skill.school_id == current_user.school_id)
    if level_id:
        stmt = stmt.where(Skill.level_id == level_id)
    return db.scalars(stmt.order_by(Skill.name.asc())).all()


@router.get("/attributes", response_model=list[AttributeOut], dependencies=[manager_guard])
def list_attributes(db: Session = Depends(get_db)) -> list[Attribute]:
    return db.scalars(select(Attribute).where(Attribute.active.is_(True)).order_by(Attribute.name.asc())).all()


@router.post("/skills", response_model=SkillOut, dependencies=[manager_guard])
def create_skill(
    payload: SkillBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Skill:
    level = db.scalar(select(Level).where(Level.id == payload.level_id, Level.school_id == current_user.school_id))
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    skill = Skill(
        school_id=current_user.school_id,
        level_id=payload.level_id,
        name=payload.name.strip(),
        description=payload.description,
        active=payload.active,
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
    skill = db.scalar(select(Skill).where(Skill.id == skill_id, Skill.school_id == current_user.school_id))
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    updates = payload.model_dump(exclude_unset=True)
    if "level_id" in updates and not db.scalar(
        select(Level).where(Level.id == updates["level_id"], Level.school_id == current_user.school_id)
    ):
        raise HTTPException(status_code=404, detail="Level not found")
    for field, value in updates.items():
        setattr(skill, field, value)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/templates", response_model=list[TemplateOut], dependencies=[manager_guard])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[TemplateOut]:
    templates = db.scalars(
        select(Template)
        .where(Template.school_id == current_user.school_id)
        .options(selectinload(Template.template_attributes).joinedload(TemplateAttribute.attribute))
        .order_by(Template.name.asc())
    ).all()
    return [template_out(template) for template in templates]


@router.post("/templates", response_model=TemplateOut, dependencies=[manager_guard])
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> TemplateOut:
    if payload.level_id and not db.scalar(
        select(Level).where(Level.id == payload.level_id, Level.school_id == current_user.school_id)
    ):
        raise HTTPException(status_code=404, detail="Level not found")
    if payload.skill_id:
        skill = db.scalar(select(Skill).where(Skill.id == payload.skill_id, Skill.school_id == current_user.school_id))
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        if payload.level_id and skill.level_id != payload.level_id:
            raise HTTPException(status_code=400, detail="Skill does not belong to level")

    template = Template(
        school_id=current_user.school_id,
        name=payload.name.strip(),
        level_id=payload.level_id,
        skill_id=payload.skill_id,
        active=payload.active,
    )
    db.add(template)
    db.flush()
    template_attributes_replace(
        db, template, [(x.attribute_id, x.sort_order) for x in payload.attributes]
    )
    db.commit()
    db.refresh(template)
    return template_out(template)


@router.put("/templates/{template_id}", response_model=TemplateOut, dependencies=[manager_guard])
def update_template(
    template_id: int,
    payload: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> TemplateOut:
    template = db.scalar(
        select(Template).where(Template.id == template_id, Template.school_id == current_user.school_id)
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    updates = payload.model_dump(exclude_unset=True, exclude={"attributes"})
    for field, value in updates.items():
        setattr(template, field, value)
    if payload.attributes is not None:
        template_attributes_replace(
            db, template, [(x.attribute_id, x.sort_order) for x in payload.attributes]
        )
    db.commit()
    db.refresh(template)
    return template_out(template)


@router.get("/evaluations", response_model=list[EvaluationSummaryOut], dependencies=[manager_guard])
def list_evaluations(
    instructor_id: int | None = None,
    supervisor_id: int | None = None,
    level_id: int | None = None,
    skill_id: int | None = None,
    rating_value: int | None = Query(default=None, ge=1, le=3),
    status_filter: EvaluationStatus | None = Query(default=None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = Query(default="submitted_at"),
    sort_dir: str = Query(default="desc"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[EvaluationSummaryOut]:
    stmt = evaluation_query_with_joins(current_user.school_id)
    filters = []
    if instructor_id:
        filters.append(Evaluation.instructor_id == instructor_id)
    if supervisor_id:
        filters.append(Evaluation.supervisor_id == supervisor_id)
    if level_id:
        filters.append(Evaluation.level_id == level_id)
    if skill_id:
        filters.append(Evaluation.skill_id == skill_id)
    if rating_value is not None:
        rating_subq = select(EvaluationRating.evaluation_id).where(
            EvaluationRating.rating_value == rating_value
        )
        filters.append(Evaluation.id.in_(rating_subq))
    if status_filter:
        filters.append(Evaluation.status == status_filter)
    if date_from:
        filters.append(Evaluation.session_date >= date_from)
    if date_to:
        filters.append(Evaluation.session_date <= date_to)
    if filters:
        stmt = stmt.where(and_(*filters))
    sortable = {
        "id": Evaluation.id,
        "session_date": Evaluation.session_date,
        "submitted_at": Evaluation.submitted_at,
        "instructor_id": Evaluation.instructor_id,
        "supervisor_id": Evaluation.supervisor_id,
        "level_id": Evaluation.level_id,
        "skill_id": Evaluation.skill_id,
    }
    if sort_by not in sortable:
        raise HTTPException(status_code=400, detail="Invalid sort_by")
    if sort_dir not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Invalid sort_dir")
    order_col = sortable[sort_by]
    stmt = stmt.order_by(asc(order_col) if sort_dir == "asc" else desc(order_col), desc(Evaluation.id))
    evaluations = db.scalars(stmt.limit(limit).offset(offset)).all()
    return [evaluation_summary_row(item) for item in evaluations]


@router.get("/exports/evaluations.csv", dependencies=[manager_guard])
def export_evaluations_csv(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Response:
    stmt = evaluation_query_with_joins(current_user.school_id)
    filters = []
    if date_from:
        filters.append(Evaluation.session_date >= date_from)
    if date_to:
        filters.append(Evaluation.session_date <= date_to)
    if filters:
        stmt = stmt.where(and_(*filters))
    evaluations = db.scalars(stmt).all()
    csv_text = evaluations_to_csv(evaluations)
    headers = {"Content-Disposition": "attachment; filename=evaluations.csv"}
    return Response(content=csv_text, media_type="text/csv", headers=headers)
