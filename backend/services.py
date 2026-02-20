import csv
import io
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, joinedload, selectinload

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
    EvaluationDetailOut,
    EvaluationSummaryOut,
    RatingOut,
    TemplateAttributeOut,
    TemplateOut,
)


def ensure_user_role(db: Session, user_id: int, expected_role: UserRole) -> User:
    user = db.get(User, user_id)
    if not user or user.role != expected_role or not user.active:
        raise HTTPException(status_code=400, detail=f"User {user_id} is not an active {expected_role.value}")
    return user


def ensure_level_skill_compatible(db: Session, level_id: int, skill_id: int) -> tuple[Level, Skill]:
    level = db.get(Level, level_id)
    skill = db.get(Skill, skill_id)
    if not level or not level.active:
        raise HTTPException(status_code=404, detail="Level not found or inactive")
    if not skill or not skill.active:
        raise HTTPException(status_code=404, detail="Skill not found or inactive")
    if skill.level_id != level.id:
        raise HTTPException(status_code=400, detail="Skill does not belong to level")
    return level, skill


def resolve_template(db: Session, level_id: int, skill_id: int, template_id: int | None) -> Template | None:
    if template_id is not None:
        template = db.get(Template, template_id)
        if not template or not template.active:
            raise HTTPException(status_code=404, detail="Template not found or inactive")
        return template

    exact = db.scalar(
        select(Template).where(
            and_(
                Template.active.is_(True),
                Template.level_id == level_id,
                Template.skill_id == skill_id,
            )
        )
    )
    if exact:
        return exact

    fallback = db.scalar(
        select(Template).where(
            and_(
                Template.active.is_(True),
                Template.level_id == level_id,
                Template.skill_id.is_(None),
            )
        )
    )
    return fallback


def sync_ratings(db: Session, evaluation: Evaluation, ratings: list[tuple[int, int]]) -> None:
    current = {r.attribute_id: r for r in evaluation.ratings}
    incoming_ids = {attribute_id for attribute_id, _ in ratings}
    if len(incoming_ids) != len(ratings):
        raise HTTPException(status_code=400, detail="Duplicate attribute ratings are not allowed")

    attributes = db.scalars(select(Attribute).where(Attribute.id.in_(incoming_ids))).all() if incoming_ids else []
    found_ids = {attr.id for attr in attributes}
    missing = incoming_ids - found_ids
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown attribute ids: {sorted(missing)}")

    for attribute_id, value in ratings:
        existing = current.get(attribute_id)
        if existing:
            existing.rating_value = value
        else:
            db.add(EvaluationRating(evaluation_id=evaluation.id, attribute_id=attribute_id, rating_value=value))

    for attribute_id, existing in current.items():
        if attribute_id not in incoming_ids:
            db.delete(existing)


def submit_evaluation(evaluation: Evaluation) -> None:
    if evaluation.status == EvaluationStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Evaluation already submitted")
    evaluation.status = EvaluationStatus.SUBMITTED
    evaluation.submitted_at = datetime.now(timezone.utc)


def evaluation_summary_row(evaluation: Evaluation) -> EvaluationSummaryOut:
    return EvaluationSummaryOut(
        id=evaluation.id,
        instructor_id=evaluation.instructor_id,
        instructor_name=evaluation.instructor.name,
        supervisor_id=evaluation.supervisor_id,
        supervisor_name=evaluation.supervisor.name,
        level_id=evaluation.level_id,
        level_name=evaluation.level.name,
        skill_id=evaluation.skill_id,
        skill_name=evaluation.skill.name,
        session_label=evaluation.session_label,
        session_date=evaluation.session_date,
        status=evaluation.status,
        submitted_at=evaluation.submitted_at,
    )


def evaluation_detail_row(evaluation: Evaluation) -> EvaluationDetailOut:
    return EvaluationDetailOut(
        **evaluation_summary_row(evaluation).model_dump(),
        notes=evaluation.notes,
        ratings=[
            RatingOut(
                attribute_id=rating.attribute_id,
                attribute_name=rating.attribute.name,
                rating_value=rating.rating_value,
            )
            for rating in sorted(evaluation.ratings, key=lambda x: x.attribute.name.lower())
        ],
    )


def template_out(template: Template) -> TemplateOut:
    attrs = [
        TemplateAttributeOut(
            attribute_id=item.attribute_id,
            attribute_name=item.attribute.name,
            sort_order=item.sort_order,
        )
        for item in sorted(template.template_attributes, key=lambda x: x.sort_order)
    ]
    return TemplateOut(
        id=template.id,
        name=template.name,
        level_id=template.level_id,
        skill_id=template.skill_id,
        active=template.active,
        attributes=attrs,
    )


def template_attributes_replace(db: Session, template: Template, attributes: list[tuple[int, int]]) -> None:
    if not attributes:
        raise HTTPException(status_code=400, detail="Template must contain at least one attribute")

    sort_orders = {order for _, order in attributes}
    if len(sort_orders) != len(attributes):
        raise HTTPException(status_code=400, detail="Duplicate sort_order values are not allowed")

    attribute_ids = [attribute_id for attribute_id, _ in attributes]
    found_ids = set(
        db.scalars(select(Attribute.id).where(Attribute.id.in_(attribute_ids), Attribute.active.is_(True))).all()
    )
    missing = set(attribute_ids) - found_ids
    if missing:
        raise HTTPException(status_code=400, detail=f"Inactive or unknown attribute ids: {sorted(missing)}")

    template.template_attributes.clear()
    for attribute_id, order in attributes:
        template.template_attributes.append(
            TemplateAttribute(attribute_id=attribute_id, sort_order=order)
        )


def evaluation_query_with_joins():
    return (
        select(Evaluation)
        .options(
            joinedload(Evaluation.instructor),
            joinedload(Evaluation.supervisor),
            joinedload(Evaluation.level),
            joinedload(Evaluation.skill),
            selectinload(Evaluation.ratings).joinedload(EvaluationRating.attribute),
        )
        .order_by(Evaluation.session_date.desc(), Evaluation.id.desc())
    )


def evaluations_to_csv(evaluations: list[Evaluation]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "evaluation_id",
            "session_label",
            "session_date",
            "status",
            "instructor",
            "supervisor",
            "level",
            "skill",
            "attribute",
            "rating_value",
            "notes",
            "submitted_at",
        ]
    )
    for evaluation in evaluations:
        rows = sorted(evaluation.ratings, key=lambda x: x.attribute.name.lower())
        if not rows:
            writer.writerow(
                [
                    evaluation.id,
                    evaluation.session_label,
                    evaluation.session_date.isoformat(),
                    evaluation.status.value,
                    evaluation.instructor.name,
                    evaluation.supervisor.name,
                    evaluation.level.name,
                    evaluation.skill.name,
                    "",
                    "",
                    evaluation.notes or "",
                    evaluation.submitted_at.isoformat() if evaluation.submitted_at else "",
                ]
            )
            continue

        for rating in rows:
            writer.writerow(
                [
                    evaluation.id,
                    evaluation.session_label,
                    evaluation.session_date.isoformat(),
                    evaluation.status.value,
                    evaluation.instructor.name,
                    evaluation.supervisor.name,
                    evaluation.level.name,
                    evaluation.skill.name,
                    rating.attribute.name,
                    rating.rating_value,
                    evaluation.notes or "",
                    evaluation.submitted_at.isoformat() if evaluation.submitted_at else "",
                ]
            )
    return output.getvalue()
