from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from deps import require_roles
from models import Evaluation, EvaluationStatus, User, UserRole
from schemas import EvaluationCreate, EvaluationDetailOut, EvaluationSummaryOut, EvaluationUpdate, TemplateOut
from services import (
    ensure_level_skill_compatible,
    ensure_user_role,
    evaluation_detail_row,
    evaluation_query_with_joins,
    evaluation_summary_row,
    resolve_template,
    submit_evaluation,
    template_out,
    sync_ratings,
)


router = APIRouter(prefix="/supervisor", tags=["supervisor"])
supervisor_guard = Depends(require_roles(UserRole.SUPERVISOR))


@router.get("/templates/resolve", response_model=TemplateOut, dependencies=[supervisor_guard])
def resolve_evaluation_template(
    level_id: int,
    skill_id: int,
    db: Session = Depends(get_db),
) -> TemplateOut:
    ensure_level_skill_compatible(db, level_id, skill_id)
    template = resolve_template(db, level_id, skill_id, template_id=None)
    if not template:
        raise HTTPException(status_code=404, detail="No active template found for level/skill")
    db.refresh(template)
    return template_out(template)


@router.get("/evaluations", response_model=list[EvaluationSummaryOut], dependencies=[supervisor_guard])
def list_my_evaluations(
    db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.SUPERVISOR))
) -> list[EvaluationSummaryOut]:
    stmt = evaluation_query_with_joins().where(Evaluation.supervisor_id == current_user.id)
    evaluations = db.scalars(stmt).all()
    return [evaluation_summary_row(item) for item in evaluations]


@router.post("/evaluations", response_model=EvaluationDetailOut, dependencies=[supervisor_guard])
def create_evaluation(
    payload: EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> EvaluationDetailOut:
    ensure_user_role(db, payload.instructor_id, UserRole.INSTRUCTOR)
    ensure_level_skill_compatible(db, payload.level_id, payload.skill_id)
    template = resolve_template(db, payload.level_id, payload.skill_id, payload.template_id)

    evaluation = Evaluation(
        instructor_id=payload.instructor_id,
        supervisor_id=current_user.id,
        level_id=payload.level_id,
        skill_id=payload.skill_id,
        template_id=template.id if template else None,
        session_label=payload.session_label.strip(),
        session_date=payload.session_date,
        notes=payload.notes,
        status=EvaluationStatus.DRAFT,
    )
    db.add(evaluation)
    db.flush()
    sync_ratings(db, evaluation, [(r.attribute_id, r.rating_value) for r in payload.ratings])
    db.commit()

    stmt = evaluation_query_with_joins().where(Evaluation.id == evaluation.id)
    created = db.scalar(stmt)
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
            Evaluation.supervisor_id == current_user.id,
        )
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if evaluation.status == EvaluationStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Cannot modify a submitted evaluation")

    evaluation.notes = payload.notes
    if payload.ratings is not None:
        sync_ratings(db, evaluation, [(r.attribute_id, r.rating_value) for r in payload.ratings])
    db.commit()

    full = db.scalar(evaluation_query_with_joins().where(Evaluation.id == evaluation.id))
    if not full:
        raise HTTPException(status_code=500, detail="Failed to reload evaluation")
    return evaluation_detail_row(full)


@router.post(
    "/evaluations/{evaluation_id}/submit",
    response_model=EvaluationDetailOut,
    dependencies=[supervisor_guard],
)
def submit_my_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> EvaluationDetailOut:
    evaluation = db.scalar(
        select(Evaluation).where(
            Evaluation.id == evaluation_id,
            Evaluation.supervisor_id == current_user.id,
        )
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    submit_evaluation(evaluation)
    db.commit()

    full = db.scalar(evaluation_query_with_joins().where(Evaluation.id == evaluation.id))
    if not full:
        raise HTTPException(status_code=500, detail="Failed to reload evaluation")
    return evaluation_detail_row(full)
