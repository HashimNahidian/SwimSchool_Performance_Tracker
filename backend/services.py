import csv
import io

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from models import (
    Attribute,
    Evaluation,
    EvaluationRating,
    Level,
    Skill,
    SkillAttribute,
    User,
    UserRole,
)
from schemas import (
    EvaluationDetailOut,
    EvaluationSummaryOut,
    RatingOut,
)


def ensure_user_role(db: Session, user_id: int, expected_role: UserRole, school_id: int) -> User:
    user = db.get(User, user_id)
    if not user or user.school_id != school_id or user.role != expected_role or not user.is_active:
        raise HTTPException(status_code=400, detail=f"User {user_id} is not an active {expected_role.value}")
    return user


def ensure_skill_in_school(db: Session, skill_id: int, school_id: int) -> Skill:
    skill = db.scalar(
        select(Skill)
        .join(Level, Skill.level_id == Level.id)
        .where(Skill.id == skill_id, Level.school_id == school_id)
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
        final_grade=evaluation.final_grade,
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
