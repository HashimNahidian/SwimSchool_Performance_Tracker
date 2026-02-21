from __future__ import annotations

from datetime import date, datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import select

import models
from db import SessionLocal
from security import hash_password


def get_or_create_user(
    db,
    *,
    name: str,
    email: str,
    password: str,
    role: models.UserRole,
    active: bool = True,
) -> models.User:
    user = db.scalar(select(models.User).where(models.User.email == email))
    if user:
        user.name = name
        user.role = role
        user.active = active
        user.password_hash = hash_password(password)
        return user
    user = models.User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        active=active,
    )
    db.add(user)
    db.flush()
    return user


def get_or_create_level(db, name: str) -> models.Level:
    level = db.scalar(select(models.Level).where(models.Level.name == name))
    if level:
        level.active = True
        return level
    level = models.Level(name=name, active=True)
    db.add(level)
    db.flush()
    return level


def get_or_create_skill(db, level_id: int, name: str) -> models.Skill:
    skill = db.scalar(select(models.Skill).where(models.Skill.level_id == level_id, models.Skill.name == name))
    if skill:
        skill.active = True
        return skill
    skill = models.Skill(level_id=level_id, name=name, active=True)
    db.add(skill)
    db.flush()
    return skill


def get_or_create_attribute(db, name: str, description: str) -> models.Attribute:
    attribute = db.scalar(select(models.Attribute).where(models.Attribute.name == name))
    if attribute:
        attribute.description = description
        attribute.active = True
        return attribute
    attribute = models.Attribute(name=name, description=description, active=True)
    db.add(attribute)
    db.flush()
    return attribute


def get_or_create_template(
    db,
    *,
    name: str,
    level_id: int | None,
    skill_id: int | None,
    attribute_ids: list[int],
) -> models.Template:
    template = db.scalar(
        select(models.Template).where(
            models.Template.name == name,
            models.Template.level_id == level_id,
            models.Template.skill_id == skill_id,
        )
    )
    if not template:
        template = models.Template(name=name, level_id=level_id, skill_id=skill_id, active=True)
        db.add(template)
        db.flush()

    existing = {ta.attribute_id: ta for ta in template.template_attributes}
    for idx, attribute_id in enumerate(attribute_ids, start=1):
        if attribute_id in existing:
            existing[attribute_id].sort_order = idx
        else:
            db.add(models.TemplateAttribute(template_id=template.id, attribute_id=attribute_id, sort_order=idx))

    delete_ids = set(existing.keys()) - set(attribute_ids)
    if delete_ids:
        for ta in template.template_attributes:
            if ta.attribute_id in delete_ids:
                db.delete(ta)

    return template


def seed() -> None:
    load_dotenv()
    with SessionLocal() as db:
        manager = get_or_create_user(
            db,
            name="Mia Manager",
            email="manager@propel.local",
            password="Propel123!",
            role=models.UserRole.manager,
        )
        supervisor = get_or_create_user(
            db,
            name="Sam Supervisor",
            email="supervisor@propel.local",
            password="Propel123!",
            role=models.UserRole.supervisor,
        )
        instructor_1 = get_or_create_user(
            db,
            name="Ivy Instructor",
            email="instructor1@propel.local",
            password="Propel123!",
            role=models.UserRole.instructor,
        )
        instructor_2 = get_or_create_user(
            db,
            name="Ian Instructor",
            email="instructor2@propel.local",
            password="Propel123!",
            role=models.UserRole.instructor,
        )

        beginner = get_or_create_level(db, "Beginner")
        intermediate = get_or_create_level(db, "Intermediate")

        freestyle = get_or_create_skill(db, beginner.id, "Freestyle Basics")
        backstroke = get_or_create_skill(db, intermediate.id, "Backstroke")

        attributes = [
            get_or_create_attribute(db, "Water Safety", "Maintains safe pool behavior and awareness."),
            get_or_create_attribute(db, "Stroke Technique", "Demonstrates proper body position and arm path."),
            get_or_create_attribute(db, "Breathing Rhythm", "Coordinates breathing with stroke cycle."),
            get_or_create_attribute(db, "Communication", "Explains cues clearly and constructively."),
        ]

        get_or_create_template(
            db,
            name="Beginner Freestyle Template",
            level_id=beginner.id,
            skill_id=freestyle.id,
            attribute_ids=[attributes[0].id, attributes[1].id, attributes[2].id],
        )
        get_or_create_template(
            db,
            name="Intermediate Backstroke Template",
            level_id=intermediate.id,
            skill_id=backstroke.id,
            attribute_ids=[attributes[0].id, attributes[1].id, attributes[3].id],
        )

        existing_eval = db.scalar(
            select(models.Evaluation).where(
                models.Evaluation.instructor_id == instructor_1.id,
                models.Evaluation.supervisor_id == supervisor.id,
                models.Evaluation.session_label == "Seed Session 1",
            )
        )
        if not existing_eval:
            evaluation = models.Evaluation(
                instructor_id=instructor_1.id,
                supervisor_id=supervisor.id,
                level_id=beginner.id,
                skill_id=freestyle.id,
                session_label="Seed Session 1",
                session_date=date.today(),
                notes="Solid class delivery with clear corrections.",
                status=models.EvaluationStatus.submitted,
                submitted_at=datetime.now(timezone.utc),
            )
            evaluation.ratings = [
                models.EvaluationRating(attribute_id=attributes[0].id, rating_value=3),
                models.EvaluationRating(attribute_id=attributes[1].id, rating_value=2),
                models.EvaluationRating(attribute_id=attributes[2].id, rating_value=2),
            ]
            db.add(evaluation)

        existing_draft = db.scalar(
            select(models.Evaluation).where(
                models.Evaluation.instructor_id == instructor_2.id,
                models.Evaluation.supervisor_id == supervisor.id,
                models.Evaluation.session_label == "Seed Draft",
            )
        )
        if not existing_draft:
            draft = models.Evaluation(
                instructor_id=instructor_2.id,
                supervisor_id=supervisor.id,
                level_id=intermediate.id,
                skill_id=backstroke.id,
                session_label="Seed Draft",
                session_date=date.today(),
                notes="Draft for supervisor workflow testing.",
                status=models.EvaluationStatus.draft,
            )
            draft.ratings = [
                models.EvaluationRating(attribute_id=attributes[0].id, rating_value=2),
                models.EvaluationRating(attribute_id=attributes[1].id, rating_value=2),
                models.EvaluationRating(attribute_id=attributes[3].id, rating_value=1),
            ]
            db.add(draft)

        db.add(
            models.AuditLog(
                actor_user_id=manager.id,
                action="SEED",
                entity_type="system",
                details="Seed data applied",
            )
        )
        db.commit()

    print("Seed complete.")
    print("Login emails:")
    print("- manager@propel.local")
    print("- supervisor@propel.local")
    print("- instructor1@propel.local")
    print("- instructor2@propel.local")
    print("Seed password for all users: Propel123!")


if __name__ == "__main__":
    seed()
