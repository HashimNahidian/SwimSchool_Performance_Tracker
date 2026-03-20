from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from db import get_db
from deps import require_roles
from models import Evaluation, User, UserRole
from schemas import EvaluationDetailOut, EvaluationSummaryOut
from services import evaluation_detail_row, evaluation_query_with_joins, evaluation_summary_row


router = APIRouter(prefix="/instructor", tags=["instructor"])
instructor_guard = Depends(require_roles(UserRole.INSTRUCTOR))


@router.get("/evaluations", response_model=list[EvaluationSummaryOut], dependencies=[instructor_guard])
def list_my_evaluations(
    date_from: date | None = None,
    date_to: date | None = None,
    skill_id: int | None = None,
    supervisor_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INSTRUCTOR)),
) -> list[EvaluationSummaryOut]:
    stmt = evaluation_query_with_joins(current_user.school_id).where(Evaluation.instructor_id == current_user.id)
    filters = []
    if date_from:
        filters.append(Evaluation.created_at >= date_from)
    if date_to:
        filters.append(Evaluation.created_at <= date_to)
    if skill_id:
        filters.append(Evaluation.skill_id == skill_id)
    if supervisor_id:
        filters.append(Evaluation.supervisor_id == supervisor_id)
    if filters:
        stmt = stmt.where(and_(*filters))
    evaluations = db.scalars(stmt).all()
    return [evaluation_summary_row(item) for item in evaluations]


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=EvaluationDetailOut,
    dependencies=[instructor_guard],
)
def get_my_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INSTRUCTOR)),
) -> EvaluationDetailOut:
    evaluation = db.scalar(
        evaluation_query_with_joins(current_user.school_id).where(
            Evaluation.id == evaluation_id,
            Evaluation.instructor_id == current_user.id,
        )
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation_detail_row(evaluation)


@router.post(
    "/evaluations/{evaluation_id}/acknowledge",
    response_model=EvaluationDetailOut,
    dependencies=[instructor_guard],
)
def acknowledge_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INSTRUCTOR)),
) -> EvaluationDetailOut:
    evaluation = db.get(Evaluation, evaluation_id)
    if not evaluation or evaluation.school_id != current_user.school_id:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if evaluation.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot acknowledge another instructor's evaluation")

    evaluation.instructor_acknowledged_at = datetime.now(timezone.utc)
    db.commit()

    full = db.scalar(
        evaluation_query_with_joins(current_user.school_id).where(
            Evaluation.id == evaluation_id,
            Evaluation.instructor_id == current_user.id,
        )
    )
    if not full:
        raise HTTPException(status_code=500, detail="Failed to reload evaluation")
    return evaluation_detail_row(full)
