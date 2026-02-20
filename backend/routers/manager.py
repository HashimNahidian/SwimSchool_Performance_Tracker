from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from db import get_db
from deps import require_roles
from models import (
    Attribute,
    Evaluation,
    EvaluationStatus,
    Level,
    Skill,
    Template,
    TemplateAttribute,
    User,
    UserRole,
)
from schemas import (
    AttributeBase,
    AttributeOut,
    AttributeUpdate,
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
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return db.scalars(select(User).order_by(User.name.asc())).all()


@router.post("/users", response_model=UserOut, dependencies=[manager_guard])
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User.id).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=400, detail="Email already exists")
    user = User(
        name=payload.name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        active=payload.active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/levels", response_model=list[LevelOut], dependencies=[manager_guard])
def list_levels(db: Session = Depends(get_db)) -> list[Level]:
    return db.scalars(select(Level).order_by(Level.name.asc())).all()


@router.post("/levels", response_model=LevelOut, dependencies=[manager_guard])
def create_level(payload: LevelBase, db: Session = Depends(get_db)) -> Level:
    level = Level(name=payload.name.strip(), active=payload.active)
    db.add(level)
    db.commit()
    db.refresh(level)
    return level


@router.put("/levels/{level_id}", response_model=LevelOut, dependencies=[manager_guard])
def update_level(level_id: int, payload: LevelUpdate, db: Session = Depends(get_db)) -> Level:
    level = db.get(Level, level_id)
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(level, field, value)
    db.commit()
    db.refresh(level)
    return level


@router.get("/skills", response_model=list[SkillOut], dependencies=[manager_guard])
def list_skills(level_id: int | None = None, db: Session = Depends(get_db)) -> list[Skill]:
    stmt = select(Skill)
    if level_id:
        stmt = stmt.where(Skill.level_id == level_id)
    return db.scalars(stmt.order_by(Skill.name.asc())).all()


@router.post("/skills", response_model=SkillOut, dependencies=[manager_guard])
def create_skill(payload: SkillBase, db: Session = Depends(get_db)) -> Skill:
    if not db.get(Level, payload.level_id):
        raise HTTPException(status_code=404, detail="Level not found")
    skill = Skill(level_id=payload.level_id, name=payload.name.strip(), active=payload.active)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.put("/skills/{skill_id}", response_model=SkillOut, dependencies=[manager_guard])
def update_skill(skill_id: int, payload: SkillUpdate, db: Session = Depends(get_db)) -> Skill:
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    updates = payload.model_dump(exclude_unset=True)
    if "level_id" in updates and not db.get(Level, updates["level_id"]):
        raise HTTPException(status_code=404, detail="Level not found")
    for field, value in updates.items():
        setattr(skill, field, value)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/attributes", response_model=list[AttributeOut], dependencies=[manager_guard])
def list_attributes(db: Session = Depends(get_db)) -> list[Attribute]:
    return db.scalars(select(Attribute).order_by(Attribute.name.asc())).all()


@router.post("/attributes", response_model=AttributeOut, dependencies=[manager_guard])
def create_attribute(payload: AttributeBase, db: Session = Depends(get_db)) -> Attribute:
    attribute = Attribute(
        name=payload.name.strip(),
        description=payload.description,
        active=payload.active,
    )
    db.add(attribute)
    db.commit()
    db.refresh(attribute)
    return attribute


@router.put("/attributes/{attribute_id}", response_model=AttributeOut, dependencies=[manager_guard])
def update_attribute(
    attribute_id: int, payload: AttributeUpdate, db: Session = Depends(get_db)
) -> Attribute:
    attribute = db.get(Attribute, attribute_id)
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(attribute, field, value)
    db.commit()
    db.refresh(attribute)
    return attribute


@router.get("/templates", response_model=list[TemplateOut], dependencies=[manager_guard])
def list_templates(db: Session = Depends(get_db)) -> list[TemplateOut]:
    templates = db.scalars(
        select(Template)
        .options(selectinload(Template.template_attributes).joinedload(TemplateAttribute.attribute))
        .order_by(Template.name.asc())
    ).all()
    return [template_out(template) for template in templates]


@router.post("/templates", response_model=TemplateOut, dependencies=[manager_guard])
def create_template(payload: TemplateCreate, db: Session = Depends(get_db)) -> TemplateOut:
    if payload.level_id and not db.get(Level, payload.level_id):
        raise HTTPException(status_code=404, detail="Level not found")
    if payload.skill_id:
        skill = db.get(Skill, payload.skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        if payload.level_id and skill.level_id != payload.level_id:
            raise HTTPException(status_code=400, detail="Skill does not belong to level")

    template = Template(
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
def update_template(template_id: int, payload: TemplateUpdate, db: Session = Depends(get_db)) -> TemplateOut:
    template = db.get(Template, template_id)
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
    status_filter: EvaluationStatus | None = Query(default=None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> list[EvaluationSummaryOut]:
    stmt = evaluation_query_with_joins()
    filters = []
    if instructor_id:
        filters.append(Evaluation.instructor_id == instructor_id)
    if supervisor_id:
        filters.append(Evaluation.supervisor_id == supervisor_id)
    if level_id:
        filters.append(Evaluation.level_id == level_id)
    if skill_id:
        filters.append(Evaluation.skill_id == skill_id)
    if status_filter:
        filters.append(Evaluation.status == status_filter)
    if date_from:
        filters.append(Evaluation.session_date >= date_from)
    if date_to:
        filters.append(Evaluation.session_date <= date_to)
    if filters:
        stmt = stmt.where(and_(*filters))
    evaluations = db.scalars(stmt).all()
    return [evaluation_summary_row(item) for item in evaluations]


@router.get("/exports/evaluations.csv", dependencies=[manager_guard])
def export_evaluations_csv(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> Response:
    stmt = evaluation_query_with_joins()
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
