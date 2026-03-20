import csv
import io
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from models import (
    Attribute,
    Evaluation,
    EvaluationRating,
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
    EvaluationDetailOut,
    EvaluationSummaryOut,
    ReevaluationRequestOut,
    RatingOut,
    ScheduledEvaluationCreate,
    ScheduledEvaluationOut,
    ScheduledEvaluationUpdate,
)

REEVALUATION_GRADE_THRESHOLD = 2


def ensure_user_role(db: Session, user_id: int, expected_role: UserRole, school_id: int) -> User:
    user = db.get(User, user_id)
    if not user or user.school_id != school_id or user.role != expected_role or not user.is_active:
        raise HTTPException(status_code=400, detail=f"User {user_id} is not an active {expected_role.value}")
    return user


def ensure_skill_in_school(db: Session, skill_id: int, school_id: int) -> Skill:
    skill = db.scalar(
        select(Skill)
        .join(Level, Skill.level_id == Level.id)
        .where(
            Skill.id == skill_id,
            Skill.is_active.is_(True),
            Level.school_id == school_id,
            Level.is_active.is_(True),
        )
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


def sync_ratings(db: Session, evaluation: Evaluation, ratings: list[tuple[int, int, str | None]]) -> None:
    current = {r.attribute_id: r for r in evaluation.ratings}
    incoming_ids = {attribute_id for attribute_id, _, _ in ratings}
    if len(incoming_ids) != len(ratings):
        raise HTTPException(status_code=400, detail="Duplicate attribute ratings are not allowed")

    # Validate each attribute is configured for this skill
    valid_attr_ids = set(
        db.scalars(
            select(SkillAttribute.attribute_id).where(SkillAttribute.skill_id == evaluation.skill_id)
        ).all()
    )
    invalid = incoming_ids - valid_attr_ids
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Attribute ids not configured for this skill: {sorted(invalid)}",
        )

    for attribute_id, value, comment in ratings:
        existing = current.get(attribute_id)
        if existing:
            existing.rating = value
            existing.comment = comment
        else:
            db.add(
                EvaluationRating(
                    evaluation_id=evaluation.id,
                    attribute_id=attribute_id,
                    rating=value,
                    comment=comment,
                )
            )

    for attribute_id, existing in current.items():
        if attribute_id not in incoming_ids:
            db.delete(existing)


def should_reevaluate(final_grade: int | None, force: bool = False) -> bool:
    if force:
        return True
    if final_grade is None:
        return False
    return final_grade <= REEVALUATION_GRADE_THRESHOLD


def _get_open_reevaluation_request(
    db: Session,
    instructor_id: int,
    skill_id: int,
) -> ReevaluationRequest | None:
    return db.scalar(
        select(ReevaluationRequest)
        .where(
            ReevaluationRequest.instructor_id == instructor_id,
            ReevaluationRequest.skill_id == skill_id,
            ReevaluationRequest.status == ReevaluationStatus.OPEN,
        )
    )


def _close_pending_reevaluation_requests(
    db: Session,
    instructor_id: int,
    skill_id: int,
    *,
    completed_at: datetime | None = None,
) -> None:
    pending = db.scalars(
        select(ReevaluationRequest)
        .where(
            ReevaluationRequest.instructor_id == instructor_id,
            ReevaluationRequest.skill_id == skill_id,
            ReevaluationRequest.status == ReevaluationStatus.OPEN,
        )
    ).all()
    closed_at = completed_at or datetime.now(timezone.utc)
    for req in pending:
        req.status = ReevaluationStatus.COMPLETED
        req.completed_at = closed_at


def clear_reevaluation_for_skill(
    db: Session,
    instructor_id: int,
    skill_id: int,
    current_evaluation_id: int | None = None,
) -> None:
    flagged = db.scalars(
        select(Evaluation).where(
            Evaluation.instructor_id == instructor_id,
            Evaluation.skill_id == skill_id,
            Evaluation.needs_reevaluation.is_(True),
        )
    ).all()
    for evaluation in flagged:
        if current_evaluation_id is not None and evaluation.id == current_evaluation_id:
            continue
        evaluation.needs_reevaluation = False
    _close_pending_reevaluation_requests(db, instructor_id, skill_id)


def _create_reevaluation_request_if_missing(
    db: Session,
    school_id: int,
    instructor_id: int,
    supervisor_id: int,
    skill_id: int,
    source_evaluation_id: int | None = None,
    notes: str | None = None,
) -> ReevaluationRequest:
    existing = _get_open_reevaluation_request(db, instructor_id, skill_id)
    if existing:
        if source_evaluation_id is not None:
            existing.source_evaluation_id = source_evaluation_id
        if notes:
            existing.notes = notes
        if supervisor_id is not None:
            existing.supervisor_id = supervisor_id
        return existing
    request = ReevaluationRequest(
        school_id=school_id,
        instructor_id=instructor_id,
        supervisor_id=supervisor_id,
        skill_id=skill_id,
        source_evaluation_id=source_evaluation_id,
        notes=notes,
        status=ReevaluationStatus.OPEN,
    )
    db.add(request)
    return request


def recalculate_final_grade(db: Session, evaluation: Evaluation) -> None:
    avg_rating = db.scalar(
        select(func.avg(EvaluationRating.rating)).where(EvaluationRating.evaluation_id == evaluation.id)
    )
    evaluation.final_grade = None if avg_rating is None else int(round(float(avg_rating)))


def sync_reevaluation_state(
    db: Session,
    evaluation: Evaluation,
    force: bool = False,
    notes: str | None = None,
) -> None:
    needs_flag = should_reevaluate(evaluation.final_grade, force)
    evaluation.needs_reevaluation = needs_flag
    if needs_flag:
        clear_reevaluation_for_skill(
            db,
            evaluation.instructor_id,
            evaluation.skill_id,
            current_evaluation_id=evaluation.id,
        )
        _create_reevaluation_request_if_missing(
            db,
            school_id=evaluation.school_id,
            instructor_id=evaluation.instructor_id,
            supervisor_id=evaluation.supervisor_id,
            skill_id=evaluation.skill_id,
            source_evaluation_id=evaluation.id,
            notes=notes,
        )
    else:
        clear_reevaluation_for_skill(db, evaluation.instructor_id, evaluation.skill_id)


def reevaluation_request_row(request: ReevaluationRequest) -> ReevaluationRequestOut:
    return ReevaluationRequestOut(
        id=request.id,
        school_id=request.school_id,
        instructor_id=request.instructor_id,
        instructor_name=request.instructor.full_name,
        supervisor_id=request.supervisor_id,
        supervisor_name=request.supervisor.full_name if request.supervisor else None,
        skill_id=request.skill_id,
        skill_name=request.skill.name,
        source_evaluation_id=request.source_evaluation_id,
        needs_reevaluation=request.status == ReevaluationStatus.OPEN,
        status=request.status,
        requested_at=request.requested_at,
        completed_at=request.completed_at,
        notes=request.notes,
    )


def evaluation_summary_row(evaluation: Evaluation) -> EvaluationSummaryOut:
    level = evaluation.skill.level
    return EvaluationSummaryOut(
        id=evaluation.id,
        instructor_id=evaluation.instructor_id,
        instructor_name=evaluation.instructor.full_name,
        supervisor_id=evaluation.supervisor_id,
        supervisor_name=evaluation.supervisor.full_name,
        level_id=level.id,
        level_name=level.name,
        skill_id=evaluation.skill_id,
        skill_name=evaluation.skill.name,
        scheduled_evaluation_id=evaluation.scheduled_evaluation_id,
        duration_seconds=evaluation.duration_seconds,
        final_grade=evaluation.final_grade,
        needs_reevaluation=evaluation.needs_reevaluation,
        instructor_acknowledged_at=evaluation.instructor_acknowledged_at,
        created_at=evaluation.created_at,
        updated_at=evaluation.updated_at,
    )


def evaluation_detail_row(evaluation: Evaluation) -> EvaluationDetailOut:
    return EvaluationDetailOut(
        **evaluation_summary_row(evaluation).model_dump(),
        notes=evaluation.notes,
        ratings=[
            RatingOut(
                attribute_id=rating.attribute_id,
                attribute_name=rating.attribute.name,
                rating=rating.rating,
                comment=rating.comment,
            )
            for rating in sorted(evaluation.ratings, key=lambda x: (x.attribute.sort_order, x.attribute.name))
        ],
    )


def evaluation_query_with_joins(school_id: int):
    return (
        select(Evaluation)
        .where(Evaluation.school_id == school_id)
        .options(
            joinedload(Evaluation.instructor),
            joinedload(Evaluation.supervisor),
            joinedload(Evaluation.skill).joinedload(Skill.level),
            selectinload(Evaluation.ratings).joinedload(EvaluationRating.attribute),
        )
        .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
    )


def evaluations_to_csv(evaluations: list[Evaluation]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "evaluation_id",
            "created_at",
            "updated_at",
            "instructor",
            "supervisor",
            "level",
            "skill",
            "attribute",
            "rating",
            "comment",
            "final_grade",
            "notes",
        ]
    )
    for evaluation in evaluations:
        level = evaluation.skill.level
        rows = sorted(evaluation.ratings, key=lambda x: (x.attribute.sort_order, x.attribute.name))
        if not rows:
            writer.writerow(
                [
                    evaluation.id,
                    evaluation.created_at.isoformat(),
                    evaluation.updated_at.isoformat(),
                    evaluation.instructor.full_name,
                    evaluation.supervisor.full_name,
                    level.name,
                    evaluation.skill.name,
                    "",
                    "",
                    "",
                    evaluation.final_grade if evaluation.final_grade is not None else "",
                    evaluation.notes or "",
                ]
            )
            continue

        for rating in rows:
            writer.writerow(
                [
                    evaluation.id,
                    evaluation.created_at.isoformat(),
                    evaluation.updated_at.isoformat(),
                    evaluation.instructor.full_name,
                    evaluation.supervisor.full_name,
                    level.name,
                    evaluation.skill.name,
                    rating.attribute.name,
                    rating.rating,
                    rating.comment or "",
                    evaluation.final_grade if evaluation.final_grade is not None else "",
                    evaluation.notes or "",
                ]
            )
    return output.getvalue()


def scheduled_evaluation_row(item: ScheduledEvaluation) -> ScheduledEvaluationOut:
    return ScheduledEvaluationOut(
        id=item.id,
        school_id=item.school_id,
        instructor_id=item.instructor_id,
        instructor_name=item.instructor.full_name,
        skill_id=item.skill_id,
        skill_name=item.skill.name,
        level_id=item.skill.level.id,
        level_name=item.skill.level.name,
        target_date=item.target_date,
        requested_by_id=item.requested_by_id,
        requested_by_name=item.requested_by.full_name,
        assigned_to_id=item.assigned_to_id,
        assigned_to_name=item.assigned_to.full_name if item.assigned_to else None,
        status=item.status,
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
        completed_at=item.completed_at,
    )


def scheduled_evaluation_query(school_id: int):
    return (
        select(ScheduledEvaluation)
        .where(ScheduledEvaluation.school_id == school_id)
        .options(
            joinedload(ScheduledEvaluation.instructor),
            joinedload(ScheduledEvaluation.skill).joinedload(Skill.level),
            joinedload(ScheduledEvaluation.requested_by),
            joinedload(ScheduledEvaluation.assigned_to),
        )
        .order_by(ScheduledEvaluation.target_date.asc(), ScheduledEvaluation.id.desc())
    )


def get_scheduled_evaluations(
    db: Session,
    school_id: int,
    *,
    instructor_id: int | None = None,
    skill_id: int | None = None,
    assigned_to_id: int | None = None,
    include_unassigned: bool = False,
    status: ScheduledEvaluationStatus | None = None,
) -> list[ScheduledEvaluation]:
    stmt = scheduled_evaluation_query(school_id)
    if instructor_id is not None:
        stmt = stmt.where(ScheduledEvaluation.instructor_id == instructor_id)
    if skill_id is not None:
        stmt = stmt.where(ScheduledEvaluation.skill_id == skill_id)
    if status is not None:
        stmt = stmt.where(ScheduledEvaluation.status == status)
    if assigned_to_id is not None:
        if include_unassigned:
            stmt = stmt.where(
                (ScheduledEvaluation.assigned_to_id == assigned_to_id) | (ScheduledEvaluation.assigned_to_id.is_(None))
            )
        else:
            stmt = stmt.where(ScheduledEvaluation.assigned_to_id == assigned_to_id)
    return db.scalars(stmt).all()


def _ensure_schedule_assignment_user(
    db: Session,
    *,
    user_id: int | None,
    school_id: int,
) -> User | None:
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if (
        not user
        or user.school_id != school_id
        or user.role not in {UserRole.SUPERVISOR, UserRole.MANAGER}
        or not user.is_active
    ):
        raise HTTPException(status_code=400, detail="Assigned user must be an active supervisor or manager")
    return user


def get_scheduled_evaluation_or_404(db: Session, schedule_id: int, school_id: int) -> ScheduledEvaluation:
    schedule = db.scalar(scheduled_evaluation_query(school_id).where(ScheduledEvaluation.id == schedule_id))
    if not schedule:
        raise HTTPException(status_code=404, detail="Scheduled evaluation not found")
    return schedule


def create_scheduled_evaluation(
    db: Session,
    *,
    school_id: int,
    requested_by_id: int,
    payload: ScheduledEvaluationCreate,
) -> ScheduledEvaluation:
    ensure_user_role(db, payload.instructor_id, UserRole.INSTRUCTOR, school_id)
    ensure_skill_in_school(db, payload.skill_id, school_id)
    _ensure_schedule_assignment_user(db, user_id=payload.assigned_to_id, school_id=school_id)
    item = ScheduledEvaluation(
        school_id=school_id,
        instructor_id=payload.instructor_id,
        skill_id=payload.skill_id,
        target_date=payload.target_date,
        requested_by_id=requested_by_id,
        assigned_to_id=payload.assigned_to_id,
        status=payload.status,
        notes=payload.notes,
    )
    if item.status == ScheduledEvaluationStatus.COMPLETED:
        item.completed_at = datetime.now(timezone.utc)
    db.add(item)
    db.commit()
    return get_scheduled_evaluation_or_404(db, item.id, school_id)


def assign_scheduled_evaluation(
    db: Session,
    schedule: ScheduledEvaluation,
    assigned_to_id: int | None,
) -> ScheduledEvaluation:
    _ensure_schedule_assignment_user(db, user_id=assigned_to_id, school_id=schedule.school_id)
    schedule.assigned_to_id = assigned_to_id
    return schedule


def update_scheduled_evaluation(
    db: Session,
    schedule: ScheduledEvaluation,
    payload: ScheduledEvaluationUpdate,
) -> ScheduledEvaluation:
    updates = payload.model_dump(exclude_unset=True)
    if "instructor_id" in updates and updates["instructor_id"] is not None:
        ensure_user_role(db, updates["instructor_id"], UserRole.INSTRUCTOR, schedule.school_id)
    if "skill_id" in updates and updates["skill_id"] is not None:
        ensure_skill_in_school(db, updates["skill_id"], schedule.school_id)
    if "assigned_to_id" in updates:
        assign_scheduled_evaluation(db, schedule, updates.pop("assigned_to_id"))
    previous_status = schedule.status
    for field, value in updates.items():
        setattr(schedule, field, value)
    if schedule.status == ScheduledEvaluationStatus.COMPLETED and previous_status != ScheduledEvaluationStatus.COMPLETED:
        schedule.completed_at = datetime.now(timezone.utc)
    elif schedule.status != ScheduledEvaluationStatus.COMPLETED:
        schedule.completed_at = None
    db.commit()
    return get_scheduled_evaluation_or_404(db, schedule.id, schedule.school_id)


def delete_scheduled_evaluation(db: Session, schedule: ScheduledEvaluation) -> None:
    db.delete(schedule)
    db.commit()


def complete_scheduled_evaluation(db: Session, schedule: ScheduledEvaluation) -> ScheduledEvaluation:
    schedule.status = ScheduledEvaluationStatus.COMPLETED
    schedule.completed_at = datetime.now(timezone.utc)
    db.commit()
    return get_scheduled_evaluation_or_404(db, schedule.id, schedule.school_id)
