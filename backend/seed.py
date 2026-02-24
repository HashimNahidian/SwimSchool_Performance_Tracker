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
    school_id: int,
    active: bool = True,
) -> models.User:
    normalized_email = email.strip().lower()
    user = db.scalar(select(models.User).where(models.User.email == normalized_email))
    if user:
        user.name = name
        user.role = role
        user.active = active
        user.email = normalized_email
        user.password_hash = hash_password(password)
        return user
    user = models.User(
        school_id=school_id,
        name=name,
        email=normalized_email,
        password_hash=hash_password(password),
        role=role,
        active=active,
    )
    db.add(user)
    db.flush()
    return user


def get_or_create_level(db, school_id: int, name: str) -> models.Level:
    level = db.scalar(
        select(models.Level).where(models.Level.school_id == school_id, models.Level.name == name)
    )
    if level:
        level.active = True
        return level
    level = models.Level(school_id=school_id, name=name, active=True)
    db.add(level)
    db.flush()
    return level


def get_or_create_skill(db, school_id: int, level_id: int, name: str) -> models.Skill:
    skill = db.scalar(
        select(models.Skill).where(
            models.Skill.school_id == school_id,
            models.Skill.level_id == level_id,
            models.Skill.name == name,
        )
    )
    if skill:
        skill.active = True
        return skill
    skill = models.Skill(school_id=school_id, level_id=level_id, name=name, active=True)
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
    school_id: int,
    attribute_ids: list[int],
) -> models.Template:
    template = db.scalar(
        select(models.Template).where(
            models.Template.name == name,
            models.Template.school_id == school_id,
            models.Template.level_id == level_id,
            models.Template.skill_id == skill_id,
        )
    )
    if not template:
        template = models.Template(
            school_id=school_id,
            name=name,
            level_id=level_id,
            skill_id=skill_id,
            active=True,
        )
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
        school = db.scalar(select(models.School).where(models.School.name == "Default School"))
        if not school:
            school = models.School(name="Default School", active=True)
            db.add(school)
            db.flush()

        manager = get_or_create_user(
            db,
            name="Mia Manager",
            email="manager@propel.local",
            password="Propel123!",
            role=models.UserRole.MANAGER,
            school_id=school.id,
        )
        supervisor = get_or_create_user(
            db,
            name="Sam Supervisor",
            email="supervisor@propel.local",
            password="Propel123!",
            role=models.UserRole.SUPERVISOR,
            school_id=school.id,
        )
        instructor_1 = get_or_create_user(
            db,
            name="Ivy Instructor",
            email="instructor1@propel.local",
            password="Propel123!",
            role=models.UserRole.INSTRUCTOR,
            school_id=school.id,
        )
        instructor_2 = get_or_create_user(
            db,
            name="Ian Instructor",
            email="instructor2@propel.local",
            password="Propel123!",
            role=models.UserRole.INSTRUCTOR,
            school_id=school.id,
        )

        beginner = get_or_create_level(db, school.id, "Beginner")
        intermediate = get_or_create_level(db, school.id, "Intermediate")

        freestyle = get_or_create_skill(db, school.id, beginner.id, "Freestyle Basics")
        backstroke = get_or_create_skill(db, school.id, intermediate.id, "Backstroke")

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
            school_id=school.id,
            attribute_ids=[attributes[0].id, attributes[1].id, attributes[2].id],
        )
        get_or_create_template(
            db,
            name="Intermediate Backstroke Template",
            level_id=intermediate.id,
            skill_id=backstroke.id,
            school_id=school.id,
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
                school_id=school.id,
                instructor_id=instructor_1.id,
                supervisor_id=supervisor.id,
                level_id=beginner.id,
                skill_id=freestyle.id,
                session_label="Seed Session 1",
                session_date=date.today(),
                notes="Solid class delivery with clear corrections.",
                status=models.EvaluationStatus.SUBMITTED,
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
                school_id=school.id,
                instructor_id=instructor_2.id,
                supervisor_id=supervisor.id,
                level_id=intermediate.id,
                skill_id=backstroke.id,
                session_label="Seed Draft",
                session_date=date.today(),
                notes="Draft for supervisor workflow testing.",
                status=models.EvaluationStatus.DRAFT,
            )
            draft.ratings = [
                models.EvaluationRating(attribute_id=attributes[0].id, rating_value=2),
                models.EvaluationRating(attribute_id=attributes[1].id, rating_value=2),
                models.EvaluationRating(attribute_id=attributes[3].id, rating_value=1),
            ]
            db.add(draft)

        db.add(
            models.AuditLog(
                user_id=manager.id,
                action="SEED",
                method="SEED",
                path="/seed",
                status_code=200,
                client_ip="127.0.0.1",
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
