from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

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
        supervisor_1 = get_or_create_user(
            db,
            name="Sam Supervisor",
            email="supervisor@propel.local",
            password="Propel123!",
            role=models.UserRole.SUPERVISOR,
            school_id=school.id,
        )
        supervisor_2 = get_or_create_user(
            db,
            name="Lisa Park",
            email="supervisor2@propel.local",
            password="Propel123!",
            role=models.UserRole.SUPERVISOR,
            school_id=school.id,
        )
        instructor_1 = get_or_create_user(
            db,
            name="Sarah Johnson",
            email="instructor1@propel.local",
            password="Propel123!",
            role=models.UserRole.INSTRUCTOR,
            school_id=school.id,
        )
        instructor_2 = get_or_create_user(
            db,
            name="Mike Chen",
            email="instructor2@propel.local",
            password="Propel123!",
            role=models.UserRole.INSTRUCTOR,
            school_id=school.id,
        )
        instructor_3 = get_or_create_user(
            db,
            name="Emma Davis",
            email="instructor3@propel.local",
            password="Propel123!",
            role=models.UserRole.INSTRUCTOR,
            school_id=school.id,
        )

        beginner = get_or_create_level(db, school.id, "Level 1 — Beginner")
        intermediate = get_or_create_level(db, school.id, "Level 2 — Intermediate")
        advanced = get_or_create_level(db, school.id, "Level 3 — Advanced")
        competitive = get_or_create_level(db, school.id, "Level 4 — Competitive")

        freestyle = get_or_create_skill(db, school.id, beginner.id, "Freestyle")
        water_safety = get_or_create_skill(db, school.id, beginner.id, "Water Safety")
        backstroke = get_or_create_skill(db, school.id, intermediate.id, "Backstroke")
        breaststroke = get_or_create_skill(db, school.id, intermediate.id, "Breaststroke")
        butterfly = get_or_create_skill(db, school.id, advanced.id, "Butterfly")
        turns_starts = get_or_create_skill(db, school.id, advanced.id, "Turns & Starts")
        race_strategy = get_or_create_skill(db, school.id, competitive.id, "Race Strategy")
        endurance = get_or_create_skill(db, school.id, competitive.id, "Endurance Training")

        attributes = [
            get_or_create_attribute(db, "Water Safety", "Maintains safe pool behavior and awareness."),
            get_or_create_attribute(db, "Stroke Technique", "Demonstrates proper body position and arm path."),
            get_or_create_attribute(db, "Breathing Rhythm", "Coordinates breathing with stroke cycle."),
            get_or_create_attribute(db, "Communication", "Explains cues clearly and constructively."),
            get_or_create_attribute(db, "Class Management", "Manages group pacing and transitions effectively."),
        ]
        a_safety, a_stroke, a_breath, a_comm, a_mgmt = attributes

        get_or_create_template(db, name="Beginner Freestyle", level_id=beginner.id, skill_id=freestyle.id, school_id=school.id, attribute_ids=[a_safety.id, a_stroke.id, a_breath.id, a_comm.id])
        get_or_create_template(db, name="Beginner Water Safety", level_id=beginner.id, skill_id=water_safety.id, school_id=school.id, attribute_ids=[a_safety.id, a_comm.id, a_mgmt.id])
        get_or_create_template(db, name="Intermediate Backstroke", level_id=intermediate.id, skill_id=backstroke.id, school_id=school.id, attribute_ids=[a_stroke.id, a_breath.id, a_comm.id])
        get_or_create_template(db, name="Intermediate Breaststroke", level_id=intermediate.id, skill_id=breaststroke.id, school_id=school.id, attribute_ids=[a_stroke.id, a_breath.id, a_comm.id])
        get_or_create_template(db, name="Advanced Butterfly", level_id=advanced.id, skill_id=butterfly.id, school_id=school.id, attribute_ids=[a_stroke.id, a_breath.id, a_comm.id, a_mgmt.id])
        get_or_create_template(db, name="Advanced Turns & Starts", level_id=advanced.id, skill_id=turns_starts.id, school_id=school.id, attribute_ids=[a_stroke.id, a_comm.id, a_mgmt.id])
        get_or_create_template(db, name="Competitive Race Strategy", level_id=competitive.id, skill_id=race_strategy.id, school_id=school.id, attribute_ids=[a_stroke.id, a_comm.id, a_mgmt.id])
        get_or_create_template(db, name="Competitive Endurance", level_id=competitive.id, skill_id=endurance.id, school_id=school.id, attribute_ids=[a_safety.id, a_stroke.id, a_breath.id, a_mgmt.id])

        today = date.today()

        def days_ago(n: int) -> date:
            return today - timedelta(days=n)

        def make_eval(db, *, instructor, supervisor, level, skill, label, days, ratings_map, notes=""):
            existing = db.scalar(
                select(models.Evaluation).where(
                    models.Evaluation.instructor_id == instructor.id,
                    models.Evaluation.supervisor_id == supervisor.id,
                    models.Evaluation.session_label == label,
                )
            )
            if existing:
                return
            ev = models.Evaluation(
                school_id=school.id,
                instructor_id=instructor.id,
                supervisor_id=supervisor.id,
                level_id=level.id,
                skill_id=skill.id,
                session_label=label,
                session_date=days_ago(days),
                notes=notes,
                status=models.EvaluationStatus.SUBMITTED,
                submitted_at=datetime.now(timezone.utc) - timedelta(days=days),
            )
            ev.ratings = [models.EvaluationRating(attribute_id=attr_id, rating_value=val) for attr_id, val in ratings_map.items()]
            db.add(ev)

        # Sarah Johnson evaluations
        make_eval(db, instructor=instructor_1, supervisor=supervisor_1, level=beginner, skill=freestyle, label="Morning Lanes A", days=63, ratings_map={a_safety.id: 3, a_stroke.id: 2, a_breath.id: 2, a_comm.id: 3}, notes="Strong opener, good corrections.")
        make_eval(db, instructor=instructor_1, supervisor=supervisor_1, level=intermediate, skill=backstroke, label="Afternoon Session B", days=56, ratings_map={a_stroke.id: 2, a_breath.id: 3, a_comm.id: 2}, notes="Timing drills need more work.")
        make_eval(db, instructor=instructor_1, supervisor=supervisor_2, level=beginner, skill=water_safety, label="Safety Review", days=49, ratings_map={a_safety.id: 3, a_comm.id: 3, a_mgmt.id: 2})
        make_eval(db, instructor=instructor_1, supervisor=supervisor_1, level=advanced, skill=butterfly, label="Advanced Class", days=35, ratings_map={a_stroke.id: 2, a_breath.id: 2, a_comm.id: 3, a_mgmt.id: 2})
        make_eval(db, instructor=instructor_1, supervisor=supervisor_2, level=intermediate, skill=breaststroke, label="Breaststroke Clinic", days=21, ratings_map={a_stroke.id: 3, a_breath.id: 3, a_comm.id: 3})
        make_eval(db, instructor=instructor_1, supervisor=supervisor_1, level=advanced, skill=turns_starts, label="Technique Block", days=7, ratings_map={a_stroke.id: 2, a_comm.id: 2, a_mgmt.id: 3})

        # Mike Chen evaluations
        make_eval(db, instructor=instructor_2, supervisor=supervisor_1, level=competitive, skill=race_strategy, label="Competition Prep", days=61, ratings_map={a_stroke.id: 3, a_comm.id: 3, a_mgmt.id: 3}, notes="Excellent race strategy delivery.")
        make_eval(db, instructor=instructor_2, supervisor=supervisor_2, level=advanced, skill=turns_starts, label="Technique Session", days=54, ratings_map={a_stroke.id: 2, a_comm.id: 2, a_mgmt.id: 2})
        make_eval(db, instructor=instructor_2, supervisor=supervisor_1, level=competitive, skill=endurance, label="Endurance Block", days=34, ratings_map={a_safety.id: 3, a_stroke.id: 3, a_breath.id: 2, a_mgmt.id: 3})
        make_eval(db, instructor=instructor_2, supervisor=supervisor_2, level=intermediate, skill=backstroke, label="Backstroke Workshop", days=20, ratings_map={a_stroke.id: 2, a_breath.id: 2, a_comm.id: 3})
        make_eval(db, instructor=instructor_2, supervisor=supervisor_1, level=competitive, skill=race_strategy, label="Sprint Drills", days=8, ratings_map={a_stroke.id: 3, a_comm.id: 3, a_mgmt.id: 2})

        # Emma Davis evaluations
        make_eval(db, instructor=instructor_3, supervisor=supervisor_2, level=beginner, skill=freestyle, label="Beginner Intro", days=64, ratings_map={a_safety.id: 2, a_stroke.id: 2, a_breath.id: 2, a_comm.id: 2}, notes="First session, room to grow.")
        make_eval(db, instructor=instructor_3, supervisor=supervisor_1, level=beginner, skill=water_safety, label="Water Safety 101", days=57, ratings_map={a_safety.id: 3, a_comm.id: 3, a_mgmt.id: 3})
        make_eval(db, instructor=instructor_3, supervisor=supervisor_2, level=intermediate, skill=breaststroke, label="Stroke Refinement", days=43, ratings_map={a_stroke.id: 3, a_breath.id: 2, a_comm.id: 3})
        make_eval(db, instructor=instructor_3, supervisor=supervisor_1, level=intermediate, skill=backstroke, label="Backstroke Basics", days=30, ratings_map={a_stroke.id: 2, a_breath.id: 2, a_comm.id: 2})
        make_eval(db, instructor=instructor_3, supervisor=supervisor_2, level=advanced, skill=butterfly, label="Butterfly Workshop", days=16, ratings_map={a_stroke.id: 3, a_breath.id: 3, a_comm.id: 3, a_mgmt.id: 3}, notes="Excellent session.")
        make_eval(db, instructor=instructor_3, supervisor=supervisor_1, level=beginner, skill=freestyle, label="Splash & Learn", days=7, ratings_map={a_safety.id: 3, a_stroke.id: 3, a_breath.id: 2, a_comm.id: 3})

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
    print("Login credentials (password: Propel123!):")
    print("- manager@propel.local  (Manager)")
    print("- supervisor@propel.local  (Supervisor — Sam Supervisor)")
    print("- supervisor2@propel.local  (Supervisor — Lisa Park)")
    print("- instructor1@propel.local  (Instructor — Sarah Johnson)")
    print("- instructor2@propel.local  (Instructor — Mike Chen)")
    print("- instructor3@propel.local  (Instructor — Emma Davis)")


if __name__ == "__main__":
    seed()
