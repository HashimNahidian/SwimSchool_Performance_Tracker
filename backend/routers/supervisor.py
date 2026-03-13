from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from deps import require_roles
from models import Attribute, Evaluation, Level, Skill, SkillAttribute, User, UserRole
from schemas import AttributeOut, EvaluationCreate, EvaluationDetailOut, EvaluationSummaryOut, EvaluationUpdate, LevelOut, SkillOut, UserOut
from services import (
    ensure_skill_in_school,
    ensure_user_role,
    evaluation_detail_row,
    evaluation_query_with_joins,
    evaluation_summary_row,
    sync_ratings,
)


router = APIRouter(prefix="/supervisor", tags=["supervisor"])
supervisor_guard = Depends(require_roles(UserRole.SUPERVISOR))


@router.get("/levels", response_model=list[LevelOut], dependencies=[supervisor_guard])
def list_levels(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> list[LevelOut]:
    levels = db.scalars(select(Level).where(Level.school_id == current_user.school_id).order_by(Level.sort_order)).all()
    return list(levels)


@router.get("/skills", response_model=list[SkillOut], dependencies=[supervisor_guard])
def list_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> list[SkillOut]:
    stmt = (
        select(Skill)
        .join(Level, Skill.level_id == Level.id)
        .where(Level.school_id == current_user.school_id)
        .order_by(Skill.sort_order)
    )
    skills = db.scalars(stmt).all()
    return list(skills)


@router.get("/instructors", response_model=list[UserOut], dependencies=[supervisor_guard])
def list_instructors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> list[UserOut]:
    users = db.scalars(
        select(User).where(
            User.school_id == current_user.school_id,
            User.role == UserRole.INSTRUCTOR,
            User.is_active.is_(True),
        ).order_by(User.full_name)
    ).all()
    return list(users)


@router.get("/skills/{skill_id}/attributes", response_model=list[AttributeOut], dependencies=[supervisor_guard])
def list_skill_attributes(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> list[Attribute]:
    skill = db.scalar(
        select(Skill)
        .join(Level, Skill.level_id == Level.id)
        .where(Skill.id == skill_id, Level.school_id == current_user.school_id)
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return db.scalars(
        select(Attribute)
        .join(SkillAttribute, Attribute.id == SkillAttribute.attribute_id)
        .where(SkillAttribute.skill_id == skill_id)
        .order_by(Attribute.sort_order.asc(), Attribute.name.asc())
    ).all()


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationDetailOut, dependencies=[supervisor_guard])
def get_my_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> EvaluationDetailOut:
    evaluation = db.scalar(
        evaluation_query_with_joins(current_user.school_id).where(
            Evaluation.id == evaluation_id,
            Evaluation.supervisor_id == current_user.id,
        )
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation_detail_row(evaluation)


@router.get("/evaluations", response_model=list[EvaluationSummaryOut], dependencies=[supervisor_guard])
def list_my_evaluations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> list[EvaluationSummaryOut]:
    stmt = evaluation_query_with_joins(current_user.school_id).where(Evaluation.supervisor_id == current_user.id)
    evaluations = db.scalars(stmt).all()
    return [evaluation_summary_row(item) for item in evaluations]


@router.post("/evaluations", response_model=EvaluationDetailOut, dependencies=[supervisor_guard])
def create_evaluation(
    payload: EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> EvaluationDetailOut:
    ensure_user_role(db, payload.instructor_id, UserRole.INSTRUCTOR, current_user.school_id)
    ensure_skill_in_school(db, payload.skill_id, current_user.school_id)

    evaluation = Evaluation(
        school_id=current_user.school_id,
        instructor_id=payload.instructor_id,
        supervisor_id=current_user.id,
        skill_id=payload.skill_id,
        notes=payload.notes,
    )
    db.add(evaluation)
    db.flush()
    sync_ratings(db, evaluation, [(r.attribute_id, r.rating, r.comment) for r in payload.ratings])
    db.commit()

    created = db.scalar(evaluation_query_with_joins(current_user.school_id).where(Evaluation.id == evaluation.id))
    if not created:
        raise HTTPException(status_code=500, detail="Failed to reload evaluation")
    return evaluation_detail_row(created)


@router.put("/evaluations/{evaluation_id}", response_model=EvaluationDetailOut, dependencies=[supervisor_guard])
def update_evaluation(
    evaluation_id: int,
    payload: EvaluationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> EvaluationDetailOut:
    evaluation = db.scalar(
        select(Evaluation).where(
            Evaluation.id == evaluation_id,
            Evaluation.school_id == current_user.school_id,
            Evaluation.supervisor_id == current_user.id,
        )
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    evaluation.notes = payload.notes
    if payload.ratings is not None:
        sync_ratings(db, evaluation, [(r.attribute_id, r.rating, r.comment) for r in payload.ratings])
    db.commit()

    full = db.scalar(evaluation_query_with_joins(current_user.school_id).where(Evaluation.id == evaluation.id))
    if not full:
        raise HTTPException(status_code=500, detail="Failed to reload evaluation")
    return evaluation_detail_row(full)
