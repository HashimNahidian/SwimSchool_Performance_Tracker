from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from db import get_db
from deps import require_roles
from models import (
    Attribute,
    Evaluation,
    Level,
    ReevaluationRequest,
    ReevaluationStatus,
    ScheduledEvaluation,
    ScheduledEvaluationStatus,
    Skill,
    SkillAttribute,
    User,
    UserRole,
)
from schemas import (
    AttributeOut,
    EvaluationCreate,
    EvaluationDetailOut,
    EvaluationSummaryOut,
    EvaluationUpdate,
    LevelOut,
    ReevaluationRequestOut,
    ScheduledEvaluationCreate,
    ScheduledEvaluationOut,
    ScheduledEvaluationUpdate,
    SkillOut,
    UserOut,
)
from services import (
    clear_reevaluation_for_skill,
    create_scheduled_evaluation,
    ensure_skill_in_school,
    ensure_user_role,
    evaluation_detail_row,
    evaluation_query_with_joins,
    evaluation_summary_row,
    get_scheduled_evaluation_or_404,
    get_scheduled_evaluations,
    recalculate_final_grade,
    reevaluation_request_row,
    scheduled_evaluation_row,
    sync_ratings,
    sync_reevaluation_state,
    update_scheduled_evaluation,
)


router = APIRouter(prefix="/supervisor", tags=["supervisor"])
supervisor_guard = Depends(require_roles(UserRole.SUPERVISOR))


@router.get("/levels", response_model=list[LevelOut], dependencies=[supervisor_guard])
def list_levels(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> list[LevelOut]:
    levels = db.scalars(
        select(Level)
        .where(Level.school_id == current_user.school_id, Level.is_active.is_(True))
        .order_by(Level.sort_order)
    ).all()
    return list(levels)


@router.get("/skills", response_model=list[SkillOut], dependencies=[supervisor_guard])
def list_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> list[SkillOut]:
    stmt = (
        select(Skill)
        .join(Level, Skill.level_id == Level.id)
        .where(
            Level.school_id == current_user.school_id,
            Level.is_active.is_(True),
            Skill.is_active.is_(True),
        )
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
    instructor_id: int | None = None,
    skill_id: int | None = None,
    needs_reevaluation: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> list[EvaluationSummaryOut]:
    stmt = evaluation_query_with_joins(current_user.school_id).where(Evaluation.supervisor_id == current_user.id)
    if instructor_id is not None:
        stmt = stmt.where(Evaluation.instructor_id == instructor_id)
    if skill_id is not None:
        stmt = stmt.where(Evaluation.skill_id == skill_id)
    if needs_reevaluation is not None:
        stmt = stmt.where(Evaluation.needs_reevaluation.is_(needs_reevaluation))
    evaluations = db.scalars(stmt).all()
    return [evaluation_summary_row(item) for item in evaluations]


@router.get("/scheduled-evaluations", response_model=list[ScheduledEvaluationOut], dependencies=[supervisor_guard])
def list_scheduled_evaluations(
    instructor_id: int | None = None,
    skill_id: int | None = None,
    status: ScheduledEvaluationStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> list[ScheduledEvaluationOut]:
    items = get_scheduled_evaluations(
        db,
        current_user.school_id,
        instructor_id=instructor_id,
        skill_id=skill_id,
        assigned_to_id=current_user.id,
        include_unassigned=True,
        status=status,
    )
    return [scheduled_evaluation_row(item) for item in items]


@router.post("/scheduled-evaluations", response_model=ScheduledEvaluationOut, dependencies=[supervisor_guard])
def create_my_scheduled_evaluation(
    payload: ScheduledEvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> ScheduledEvaluationOut:
    assigned_to_id = payload.assigned_to_id if payload.assigned_to_id is not None else current_user.id
    item = create_scheduled_evaluation(
        db,
        school_id=current_user.school_id,
        requested_by_id=current_user.id,
        payload=payload.model_copy(update={"assigned_to_id": assigned_to_id}),
    )
    return scheduled_evaluation_row(item)


@router.put("/scheduled-evaluations/{schedule_id}", response_model=ScheduledEvaluationOut, dependencies=[supervisor_guard])
def update_my_scheduled_evaluation(
    schedule_id: int,
    payload: ScheduledEvaluationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> ScheduledEvaluationOut:
    item = get_scheduled_evaluation_or_404(db, schedule_id, current_user.school_id)
    updated = update_scheduled_evaluation(db, item, payload)
    return scheduled_evaluation_row(updated)


@router.delete("/scheduled-evaluations/{schedule_id}", status_code=204, dependencies=[supervisor_guard])
def delete_my_scheduled_evaluation(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> None:
    item = get_scheduled_evaluation_or_404(db, schedule_id, current_user.school_id)
    db.delete(item)
    db.commit()


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
        scheduled_evaluation_id=payload.scheduled_evaluation_id,
        notes=payload.notes,
        duration_seconds=payload.duration_seconds,
        needs_reevaluation=payload.needs_reevaluation,
    )
    if payload.scheduled_evaluation_id is not None:
        schedule = get_scheduled_evaluation_or_404(db, payload.scheduled_evaluation_id, current_user.school_id)
        schedule.status = ScheduledEvaluationStatus.COMPLETED
        schedule.completed_at = datetime.now(timezone.utc)
    db.add(evaluation)
    db.flush()
    sync_ratings(db, evaluation, [(r.attribute_id, r.rating, r.comment) for r in payload.ratings])
    db.flush()
    recalculate_final_grade(db, evaluation)
    sync_reevaluation_state(db, evaluation, force=payload.needs_reevaluation, notes=payload.notes)
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
    evaluation.duration_seconds = payload.duration_seconds
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


@router.delete("/evaluations/{evaluation_id}", status_code=204, dependencies=[supervisor_guard])
def delete_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> None:
    evaluation = db.scalar(
        select(Evaluation).where(
            Evaluation.id == evaluation_id,
            Evaluation.school_id == current_user.school_id,
            Evaluation.supervisor_id == current_user.id,
        )
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    db.delete(evaluation)
    db.commit()


@router.get("/reevaluations", response_model=list[ReevaluationRequestOut], dependencies=[supervisor_guard])
def list_reevaluations(
    instructor_id: int | None = None,
    skill_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
) -> list[ReevaluationRequestOut]:
    stmt = (
        select(ReevaluationRequest)
        .where(
            ReevaluationRequest.school_id == current_user.school_id,
            ReevaluationRequest.status == ReevaluationStatus.OPEN,
        )
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
    requests = db.scalars(stmt).all()
    return [reevaluation_request_row(item) for item in requests]


@router.put("/reevaluations/{request_id}/complete", response_model=ReevaluationRequestOut, dependencies=[supervisor_guard])
def complete_reevaluation(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPERVISOR)),
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
    clear_reevaluation_for_skill(db, request.instructor_id, request.skill_id)

    db.commit()
    db.refresh(request)
    return reevaluation_request_row(request)
