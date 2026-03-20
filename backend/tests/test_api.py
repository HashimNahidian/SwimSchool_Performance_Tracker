from pathlib import Path
import sys
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(str(Path(__file__).resolve().parents[1]))

import main
import models
from db import Base, get_db
from routers import auth as auth_router
from security import hash_password


TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db_session() -> Session:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


def create_school(db: Session, name: str = "Test School") -> models.School:
    school = models.School(name=name)
    db.add(school)
    db.flush()
    return school


def create_user(
    db: Session,
    name: str,
    email: str,
    role: models.UserRole,
    school_id: int,
    username: str | None = None,
) -> models.User:
    user = models.User(
        school_id=school_id,
        full_name=name,
        username=username or email.split("@")[0].lower(),
        email=email,
        password_hash=hash_password("TestPass123!"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(client: TestClient, identifier: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": identifier, "password": "TestPass123!"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_login_rate_limit():
    limiter = auth_router.login_limiter
    original_max = limiter.max_requests
    original_window = limiter.window_seconds
    limiter._events.clear()
    yield
    limiter._events.clear()
    limiter.max_requests = original_max
    limiter.window_seconds = original_window


def test_manager_only_endpoint_rejects_supervisor(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager@test.local", models.UserRole.MANAGER, school.id)
    create_user(db_session, "Supervisor", "supervisor@test.local", models.UserRole.SUPERVISOR, school.id)

    supervisor_headers = auth_headers(client, "supervisor@test.local")
    response = client.post("/manager/levels", headers=supervisor_headers, json={"name": "Beginner"})
    assert response.status_code == 403

    manager_headers = auth_headers(client, "manager@test.local")
    success = client.post("/manager/levels", headers=manager_headers, json={"name": "Beginner"})
    assert success.status_code == 200


def test_login_rate_limit_blocks_excessive_attempts(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager-rate@test.local", models.UserRole.MANAGER, school.id)
    auth_router.login_limiter.max_requests = 2
    auth_router.login_limiter.window_seconds = 60
    headers = {"X-Forwarded-For": "1.2.3.4"}

    invalid_1 = client.post("/auth/login", headers=headers, json={"username": "manager-rate", "password": "bad-pass"})
    assert invalid_1.status_code == 401
    invalid_2 = client.post("/auth/login", headers=headers, json={"username": "manager-rate", "password": "bad-pass"})
    assert invalid_2.status_code == 401
    blocked = client.post("/auth/login", headers=headers, json={"username": "manager-rate", "password": "TestPass123!"})
    assert blocked.status_code == 429


def test_login_accepts_username_as_primary_identifier(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(
        db_session,
        "Manager Username",
        "manager.username@test.local",
        models.UserRole.MANAGER,
        school.id,
        username="manager_username",
    )

    response = client.post("/auth/login", json={"username": "manager_username", "password": "TestPass123!"})
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_login_still_accepts_email_fallback(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(
        db_session,
        "Manager Fallback",
        "manager.fallback@test.local",
        models.UserRole.MANAGER,
        school.id,
        username="manager_fallback",
    )

    response = client.post("/auth/login", json={"email": "manager.fallback@test.local", "password": "TestPass123!"})
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_supervisor_submit_flow_and_instructor_visibility(client: TestClient, db_session: Session):
    school = create_school(db_session)
    supervisor = create_user(db_session, "Supervisor", "supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "instructor@test.local", models.UserRole.INSTRUCTOR, school.id)
    create_user(db_session, "Other Instructor", "other@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Beginner")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Freestyle")
    db_session.add(skill)
    db_session.flush()
    attr1 = models.Attribute(school_id=school.id, name="Safety", description="desc")
    attr2 = models.Attribute(school_id=school.id, name="Technique", description="desc")
    db_session.add_all([attr1, attr2])
    db_session.flush()
    db_session.add_all([
        models.SkillAttribute(skill_id=skill.id, attribute_id=attr1.id),
        models.SkillAttribute(skill_id=skill.id, attribute_id=attr2.id),
    ])
    db_session.commit()

    supervisor_headers = auth_headers(client, "supervisor@test.local")
    create_response = client.post(
        "/supervisor/evaluations",
        headers=supervisor_headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "notes": "Test notes",
            "ratings": [
                {"attribute_id": attr1.id, "rating": 2},
                {"attribute_id": attr2.id, "rating": 3},
            ],
        },
    )
    assert create_response.status_code == 200
    evaluation_id = create_response.json()["id"]

    instructor_headers = auth_headers(client, "instructor@test.local")
    list_response = client.get("/instructor/evaluations", headers=instructor_headers)
    assert list_response.status_code == 200
    returned_ids = [item["id"] for item in list_response.json()]
    assert evaluation_id in returned_ids

    details_response = client.get(f"/instructor/evaluations/{evaluation_id}", headers=instructor_headers)
    assert details_response.status_code == 200

    other_headers = auth_headers(client, "other@test.local")
    forbidden = client.get(f"/instructor/evaluations/{evaluation_id}", headers=other_headers)
    assert forbidden.status_code == 404

    owner_eval = db_session.get(models.Evaluation, evaluation_id)
    assert owner_eval is not None
    assert owner_eval.supervisor_id == supervisor.id


def test_create_evaluation_rejects_attribute_not_linked_to_skill(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Supervisor", "supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Intermediate")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Backstroke")
    db_session.add(skill)
    db_session.flush()
    attr_linked = models.Attribute(school_id=school.id, name="Timing", description="desc")
    attr_unlinked = models.Attribute(school_id=school.id, name="Power", description="desc")
    db_session.add_all([attr_linked, attr_unlinked])
    db_session.flush()
    db_session.add(models.SkillAttribute(skill_id=skill.id, attribute_id=attr_linked.id))
    db_session.commit()

    supervisor_headers = auth_headers(client, "supervisor@test.local")
    response = client.post(
        "/supervisor/evaluations",
        headers=supervisor_headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "notes": "Test",
            "ratings": [
                {"attribute_id": attr_linked.id, "rating": 3},
                {"attribute_id": attr_unlinked.id, "rating": 2},
            ],
        },
    )
    assert response.status_code == 400


def test_supervisor_create_evaluation_persists_duration_seconds(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Supervisor", "duration.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "duration.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Duration Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Duration Skill")
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(school_id=school.id, name="Duration Attribute", description="desc")
    db_session.add(attr)
    db_session.flush()
    db_session.add(models.SkillAttribute(skill_id=skill.id, attribute_id=attr.id))
    db_session.commit()

    headers = auth_headers(client, "duration.supervisor@test.local")
    response = client.post(
        "/supervisor/evaluations",
        headers=headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "notes": "Timed session",
            "duration_seconds": 125,
            "ratings": [
                {"attribute_id": attr.id, "rating": 4},
            ],
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["duration_seconds"] == 125

    evaluation = db_session.get(models.Evaluation, payload["id"])
    assert evaluation is not None
    assert evaluation.duration_seconds == 125


def test_manager_csv_export_returns_data(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager@test.local", models.UserRole.MANAGER, school.id)
    supervisor = create_user(db_session, "Supervisor", "supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Advanced")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Butterfly")
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(school_id=school.id, name="Form", description="desc")
    db_session.add(attr)
    db_session.flush()
    db_session.add(models.SkillAttribute(skill_id=skill.id, attribute_id=attr.id))
    db_session.flush()

    evaluation = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        skill_id=skill.id,
        notes="Ready for export",
    )
    db_session.add(evaluation)
    db_session.flush()
    evaluation.ratings = [models.EvaluationRating(attribute_id=attr.id, rating=3)]
    db_session.commit()

    manager_headers = auth_headers(client, "manager@test.local")
    export_response = client.get("/manager/exports/evaluations.csv", headers=manager_headers)
    assert export_response.status_code == 200
    assert "text/csv" in export_response.headers["content-type"]
    body = export_response.text
    assert "evaluation_id" in body
    assert "Ready for export" in body


def test_manager_evaluations_support_pagination_sort_and_filters(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager2@test.local", models.UserRole.MANAGER, school.id)
    supervisor = create_user(db_session, "Supervisor", "supervisor2@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "instructor2@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Level A")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Skill A")
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(school_id=school.id, name="Attr A", description="desc")
    db_session.add(attr)
    db_session.flush()
    db_session.add(models.SkillAttribute(skill_id=skill.id, attribute_id=attr.id))
    db_session.flush()

    ev1 = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        skill_id=skill.id,
        notes="older",
        final_grade=2,
    )
    ev2 = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        skill_id=skill.id,
        notes="newer",
        final_grade=3,
    )
    db_session.add_all([ev1, ev2])
    db_session.commit()

    manager_headers = auth_headers(client, "manager2@test.local")
    response = client.get(
        "/manager/evaluations?sort_by=final_grade&sort_dir=asc&limit=1&offset=0",
        headers=manager_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["final_grade"] == 2

    export = client.get(
        f"/manager/exports/evaluations.csv?sort_by=final_grade&sort_dir=asc",
        headers=manager_headers,
    )
    assert export.status_code == 200
    csv_data = export.text
    assert "older" in csv_data
    assert "newer" in csv_data


def test_instructor_supervisor_filter_and_trends(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager3@test.local", models.UserRole.MANAGER, school.id)
    supervisor_a = create_user(db_session, "Supervisor A", "supervisorA@test.local", models.UserRole.SUPERVISOR, school.id)
    supervisor_b = create_user(db_session, "Supervisor B", "supervisorB@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "instructor3@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Level Trend")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Skill Trend")
    db_session.add(skill)
    db_session.flush()

    ev_a = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor_a.id,
        skill_id=skill.id,
        notes="A",
    )
    ev_b = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor_b.id,
        skill_id=skill.id,
        notes="B",
    )
    db_session.add_all([ev_a, ev_b])
    db_session.commit()

    headers = auth_headers(client, "instructor3@test.local")
    filtered = client.get(f"/instructor/evaluations?supervisor_id={supervisor_a.id}", headers=headers)
    assert filtered.status_code == 200
    payload = filtered.json()
    assert len(payload) == 1
    assert payload[0]["supervisor_id"] == supervisor_a.id


def test_instructor_can_acknowledge_their_own_evaluation(client: TestClient, db_session: Session):
    school = create_school(db_session)
    supervisor = create_user(db_session, "Supervisor", "ack.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "ack.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Ack Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Ack Skill")
    db_session.add(skill)
    db_session.flush()
    evaluation = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        skill_id=skill.id,
        final_grade=4,
        notes="Please review",
    )
    db_session.add(evaluation)
    db_session.commit()

    headers = auth_headers(client, "ack.instructor@test.local")
    response = client.post(f"/instructor/evaluations/{evaluation.id}/acknowledge", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["instructor_acknowledged_at"] is not None

    db_session.refresh(evaluation)
    assert evaluation.instructor_acknowledged_at is not None


def test_instructor_cannot_acknowledge_another_instructors_evaluation(client: TestClient, db_session: Session):
    school = create_school(db_session)
    supervisor = create_user(db_session, "Supervisor", "ack2.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    owner = create_user(db_session, "Owner Instructor", "ack2.owner@test.local", models.UserRole.INSTRUCTOR, school.id)
    other = create_user(db_session, "Other Instructor", "ack2.other@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Ack Restrict Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Ack Restrict Skill")
    db_session.add(skill)
    db_session.flush()
    evaluation = models.Evaluation(
        school_id=school.id,
        instructor_id=owner.id,
        supervisor_id=supervisor.id,
        skill_id=skill.id,
        final_grade=3,
    )
    db_session.add(evaluation)
    db_session.commit()

    headers = auth_headers(client, "ack2.other@test.local")
    response = client.post(f"/instructor/evaluations/{evaluation.id}/acknowledge", headers=headers)
    assert response.status_code == 403


def test_supervisor_cannot_acknowledge_instructor_evaluation(client: TestClient, db_session: Session):
    school = create_school(db_session)
    supervisor = create_user(db_session, "Supervisor", "ack3.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "ack3.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Ack Role Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Ack Role Skill")
    db_session.add(skill)
    db_session.flush()
    evaluation = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        skill_id=skill.id,
        final_grade=5,
    )
    db_session.add(evaluation)
    db_session.commit()

    headers = auth_headers(client, "ack3.supervisor@test.local")
    response = client.post(f"/instructor/evaluations/{evaluation.id}/acknowledge", headers=headers)
    assert response.status_code == 403


def test_manager_can_manage_skill_attributes(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager4@test.local", models.UserRole.MANAGER, school.id)
    level = models.Level(school_id=school.id, name="Template Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Template Skill")
    db_session.add(skill)
    db_session.flush()
    attr_a = models.Attribute(school_id=school.id, name="Attr T A", description="a")
    attr_b = models.Attribute(school_id=school.id, name="Attr T B", description="b")
    db_session.add_all([attr_a, attr_b])
    db_session.flush()
    db_session.add(models.SkillAttribute(skill_id=skill.id, attribute_id=attr_a.id))
    db_session.commit()

    headers = auth_headers(client, "manager4@test.local")

    # Verify only attr_a is linked
    get_response = client.get(f"/manager/skills/{skill.id}/attributes", headers=headers)
    assert get_response.status_code == 200
    linked_ids = [a["id"] for a in get_response.json()]
    assert attr_a.id in linked_ids
    assert attr_b.id not in linked_ids

    # Add attr_b
    add_response = client.post(
        f"/manager/skills/{skill.id}/attributes",
        headers=headers,
        json={"attribute_id": attr_b.id},
    )
    assert add_response.status_code == 204

    # Verify both are linked
    get_response2 = client.get(f"/manager/skills/{skill.id}/attributes", headers=headers)
    assert get_response2.status_code == 200
    linked_ids2 = [a["id"] for a in get_response2.json()]
    assert attr_a.id in linked_ids2
    assert attr_b.id in linked_ids2

    # Remove attr_b
    del_response = client.delete(f"/manager/skills/{skill.id}/attributes/{attr_b.id}", headers=headers)
    assert del_response.status_code == 204

    # Verify only attr_a remains
    get_response3 = client.get(f"/manager/skills/{skill.id}/attributes", headers=headers)
    assert get_response3.status_code == 200
    linked_ids3 = [a["id"] for a in get_response3.json()]
    assert attr_a.id in linked_ids3
    assert attr_b.id not in linked_ids3


def test_manager_delete_level_archives_level_and_skills_but_keeps_evaluations(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "archive.level.manager@test.local", models.UserRole.MANAGER, school.id)
    supervisor = create_user(db_session, "Supervisor", "archive.level.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "archive.level.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Archive Me")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Archived Skill")
    db_session.add(skill)
    db_session.flush()
    evaluation = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        skill_id=skill.id,
        final_grade=3,
        notes="should survive",
    )
    db_session.add(evaluation)
    db_session.commit()

    headers = auth_headers(client, "archive.level.manager@test.local")
    delete_response = client.delete(f"/manager/levels/{level.id}", headers=headers)
    assert delete_response.status_code == 204

    db_session.refresh(level)
    db_session.refresh(skill)
    assert level.is_active is False
    assert skill.is_active is False
    assert db_session.get(models.Evaluation, evaluation.id) is not None

    levels_response = client.get("/manager/levels", headers=headers)
    assert levels_response.status_code == 200
    assert all(item["id"] != level.id for item in levels_response.json())

    skills_response = client.get("/manager/skills", headers=headers)
    assert skills_response.status_code == 200
    assert all(item["id"] != skill.id for item in skills_response.json())

    evaluation_response = client.get(f"/manager/evaluations/{evaluation.id}", headers=headers)
    assert evaluation_response.status_code == 200
    assert evaluation_response.json()["skill_name"] == "Archived Skill"


def test_manager_delete_attribute_archives_attribute_but_keeps_evaluations(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "archive.attribute.manager@test.local", models.UserRole.MANAGER, school.id)
    supervisor = create_user(db_session, "Supervisor", "archive.attribute.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "archive.attribute.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Attribute Archive Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Attribute Archive Skill")
    db_session.add(skill)
    db_session.flush()
    attribute = models.Attribute(school_id=school.id, name="Archive Attribute", description="desc")
    db_session.add(attribute)
    db_session.flush()
    db_session.add(models.SkillAttribute(skill_id=skill.id, attribute_id=attribute.id))
    db_session.flush()
    evaluation = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        skill_id=skill.id,
        final_grade=4,
        notes="attribute should survive",
    )
    db_session.add(evaluation)
    db_session.flush()
    db_session.add(
        models.EvaluationRating(evaluation_id=evaluation.id, attribute_id=attribute.id, rating=4, comment="saved")
    )
    db_session.commit()

    headers = auth_headers(client, "archive.attribute.manager@test.local")
    delete_response = client.delete(f"/manager/attributes/{attribute.id}", headers=headers)
    assert delete_response.status_code == 204

    db_session.refresh(attribute)
    assert attribute.is_active is False
    assert db_session.get(models.Evaluation, evaluation.id) is not None

    attributes_response = client.get("/manager/attributes", headers=headers)
    assert attributes_response.status_code == 200
    assert all(item["id"] != attribute.id for item in attributes_response.json())

    skill_attributes_response = client.get(f"/manager/skills/{skill.id}/attributes", headers=headers)
    assert skill_attributes_response.status_code == 200
    assert all(item["id"] != attribute.id for item in skill_attributes_response.json())

    evaluation_response = client.get(f"/manager/evaluations/{evaluation.id}", headers=headers)
    assert evaluation_response.status_code == 200
    assert evaluation_response.json()["ratings"][0]["attribute_name"] == "Archive Attribute"


def test_manager_can_update_user_with_phone(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager5@test.local", models.UserRole.MANAGER, school.id)
    target = create_user(db_session, "Coach User", "coach@test.local", models.UserRole.INSTRUCTOR, school.id)

    headers = auth_headers(client, "manager5@test.local")
    response = client.put(
        f"/manager/users/{target.id}",
        headers=headers,
        json={
            "full_name": "Coach Updated",
            "username": "coach_updated",
            "email": "coach.updated@test.local",
            "phone": "555-0102",
            "role": "SUPERVISOR",
            "is_active": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["full_name"] == "Coach Updated"
    assert payload["username"] == "coach_updated"
    assert payload["email"] == "coach.updated@test.local"
    assert payload["phone"] == "555-0102"
    assert payload["role"] == "SUPERVISOR"
    assert payload["is_active"] is False


def test_manager_can_create_user_with_username(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager.create.user@test.local", models.UserRole.MANAGER, school.id)

    headers = auth_headers(client, "manager.create.user")
    response = client.post(
        "/manager/users",
        headers=headers,
        json={
            "full_name": "Coach Create",
            "username": "coach_create",
            "email": "coach.create@test.local",
            "phone": "555-0110",
            "password": "TestPass123!",
            "role": "INSTRUCTOR",
            "is_active": True,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["username"] == "coach_create"
    assert payload["email"] == "coach.create@test.local"


def test_manager_can_delete_user(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager6@test.local", models.UserRole.MANAGER, school.id)
    target = create_user(db_session, "Delete User", "delete.me@test.local", models.UserRole.INSTRUCTOR, school.id)

    headers = auth_headers(client, "manager6@test.local")
    delete_response = client.delete(f"/manager/users/{target.id}", headers=headers)
    assert delete_response.status_code == 204

    users_response = client.get("/manager/users", headers=headers)
    assert users_response.status_code == 200
    emails = [item["email"] for item in users_response.json()]
    assert "delete.me@test.local" not in emails


def test_manager_can_create_update_and_delete_scheduled_evaluation(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "schedule.manager@test.local", models.UserRole.MANAGER, school.id)
    supervisor = create_user(db_session, "Supervisor", "schedule.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "schedule.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Schedule Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Schedule Skill")
    db_session.add(skill)
    db_session.commit()

    headers = auth_headers(client, "schedule.manager@test.local")
    created = client.post(
        "/manager/scheduled-evaluations",
        headers=headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "target_date": "2026-03-25",
            "assigned_to_id": supervisor.id,
            "notes": "First-time eval",
        },
    )
    assert created.status_code == 200, created.text
    payload = created.json()
    assert payload["assigned_to_id"] == supervisor.id
    assert payload["status"] == "PENDING"

    listed = client.get("/manager/scheduled-evaluations", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(
        f"/manager/scheduled-evaluations/{payload['id']}",
        headers=headers,
        json={"status": "IN_PROGRESS"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "IN_PROGRESS"

    deleted = client.delete(f"/manager/scheduled-evaluations/{payload['id']}", headers=headers)
    assert deleted.status_code == 204

    relisted = client.get("/manager/scheduled-evaluations", headers=headers)
    assert relisted.status_code == 200
    assert relisted.json() == []


def test_supervisor_creating_evaluation_from_schedule_marks_schedule_completed(client: TestClient, db_session: Session):
    school = create_school(db_session)
    supervisor = create_user(db_session, "Supervisor", "scheduled.eval.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "scheduled.eval.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Scheduled Eval Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Scheduled Eval Skill")
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(school_id=school.id, name="Scheduled Eval Attribute", description="desc")
    db_session.add(attr)
    db_session.flush()
    db_session.add(models.SkillAttribute(skill_id=skill.id, attribute_id=attr.id))
    db_session.commit()

    headers = auth_headers(client, "scheduled.eval.supervisor@test.local")
    scheduled = client.post(
        "/supervisor/scheduled-evaluations",
        headers=headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "target_date": "2026-03-25",
            "notes": "Scheduled first eval",
        },
    )
    assert scheduled.status_code == 200, scheduled.text
    schedule_id = scheduled.json()["id"]

    created = client.post(
        "/supervisor/evaluations",
        headers=headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "scheduled_evaluation_id": schedule_id,
            "duration_seconds": 90,
            "ratings": [{"attribute_id": attr.id, "rating": 4}],
            "notes": "Completed scheduled eval",
        },
    )
    assert created.status_code == 200, created.text
    created_payload = created.json()
    assert created_payload["scheduled_evaluation_id"] == schedule_id

    schedule = db_session.get(models.ScheduledEvaluation, schedule_id)
    assert schedule is not None
    assert schedule.status == models.ScheduledEvaluationStatus.COMPLETED
    assert schedule.completed_at is not None


def test_supervisor_lists_assigned_and_unassigned_scheduled_evaluations_only_for_school(client: TestClient, db_session: Session):
    school = create_school(db_session)
    other_school = create_school(db_session, "Other School")
    supervisor = create_user(db_session, "Supervisor", "schedule.scope.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    other_supervisor = create_user(db_session, "Other Supervisor", "schedule.scope.other@test.local", models.UserRole.SUPERVISOR, school.id)
    foreign_supervisor = create_user(db_session, "Foreign Supervisor", "schedule.scope.foreign@test.local", models.UserRole.SUPERVISOR, other_school.id)
    instructor = create_user(db_session, "Instructor", "schedule.scope.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)
    other_instructor = create_user(db_session, "Other Instructor", "schedule.scope.instructor2@test.local", models.UserRole.INSTRUCTOR, other_school.id)

    level = models.Level(school_id=school.id, name="Scoped Level")
    other_level = models.Level(school_id=other_school.id, name="Other Scoped Level")
    db_session.add_all([level, other_level])
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Scoped Skill")
    other_skill = models.Skill(level_id=other_level.id, name="Other Scoped Skill")
    db_session.add_all([skill, other_skill])
    db_session.flush()

    db_session.add_all(
        [
            models.ScheduledEvaluation(
                school_id=school.id,
                instructor_id=instructor.id,
                skill_id=skill.id,
                target_date=date(2026, 3, 25),
                requested_by_id=supervisor.id,
                assigned_to_id=supervisor.id,
            ),
            models.ScheduledEvaluation(
                school_id=school.id,
                instructor_id=instructor.id,
                skill_id=skill.id,
                target_date=date(2026, 3, 26),
                requested_by_id=supervisor.id,
                assigned_to_id=None,
            ),
            models.ScheduledEvaluation(
                school_id=school.id,
                instructor_id=instructor.id,
                skill_id=skill.id,
                target_date=date(2026, 3, 27),
                requested_by_id=supervisor.id,
                assigned_to_id=other_supervisor.id,
            ),
            models.ScheduledEvaluation(
                school_id=other_school.id,
                instructor_id=other_instructor.id,
                skill_id=other_skill.id,
                target_date=date(2026, 3, 28),
                requested_by_id=foreign_supervisor.id,
                assigned_to_id=None,
            ),
        ]
    )
    db_session.commit()

    headers = auth_headers(client, "schedule.scope.supervisor@test.local")
    listed = client.get("/supervisor/scheduled-evaluations", headers=headers)
    assert listed.status_code == 200
    payload = listed.json()
    assert len(payload) == 2
    assert all(item["assigned_to_id"] in {None, supervisor.id} for item in payload)


def test_low_grade_evaluation_creates_reevaluation_request(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Supervisor", "reeval.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "reeval.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Reeval Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Reeval Skill")
    db_session.add(skill)
    db_session.flush()
    attr_a = models.Attribute(school_id=school.id, name="Consistency", description="desc")
    attr_b = models.Attribute(school_id=school.id, name="Technique", description="desc")
    db_session.add_all([attr_a, attr_b])
    db_session.flush()
    db_session.add_all(
        [
            models.SkillAttribute(skill_id=skill.id, attribute_id=attr_a.id),
            models.SkillAttribute(skill_id=skill.id, attribute_id=attr_b.id),
        ]
    )
    db_session.commit()

    headers = auth_headers(client, "reeval.supervisor@test.local")
    response = client.post(
        "/supervisor/evaluations",
        headers=headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "notes": "Needs extra work",
            "ratings": [
                {"attribute_id": attr_a.id, "rating": 1},
                {"attribute_id": attr_b.id, "rating": 2},
            ],
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["final_grade"] == 2
    assert payload["needs_reevaluation"] is True

    evaluation = db_session.get(models.Evaluation, payload["id"])
    assert evaluation is not None
    assert evaluation.needs_reevaluation is True

    request = db_session.query(models.ReevaluationRequest).filter_by(
        instructor_id=instructor.id,
        skill_id=skill.id,
        status=models.ReevaluationStatus.OPEN,
    ).one()
    assert request.source_evaluation_id == evaluation.id
    assert request.notes == "Needs extra work"

    flagged = client.get("/supervisor/evaluations?needs_reevaluation=true", headers=headers)
    assert flagged.status_code == 200
    flagged_payload = flagged.json()
    assert len(flagged_payload) == 1
    assert flagged_payload[0]["id"] == evaluation.id


def test_follow_up_evaluation_closes_open_reevaluation_request(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Supervisor", "reeval2.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "reeval2.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Follow Up Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Follow Up Skill")
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(school_id=school.id, name="Control", description="desc")
    db_session.add(attr)
    db_session.flush()
    db_session.add(models.SkillAttribute(skill_id=skill.id, attribute_id=attr.id))
    db_session.commit()

    headers = auth_headers(client, "reeval2.supervisor@test.local")
    first = client.post(
        "/supervisor/evaluations",
        headers=headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "ratings": [{"attribute_id": attr.id, "rating": 2}],
            "notes": "Needs follow up",
        },
    )
    assert first.status_code == 200, first.text

    first_request = db_session.query(models.ReevaluationRequest).filter_by(
        instructor_id=instructor.id,
        skill_id=skill.id,
        status=models.ReevaluationStatus.OPEN,
    ).one()

    second = client.post(
        "/supervisor/evaluations",
        headers=headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "ratings": [{"attribute_id": attr.id, "rating": 4}],
            "notes": "Improved",
        },
    )
    assert second.status_code == 200, second.text
    second_payload = second.json()
    assert second_payload["final_grade"] == 4
    assert second_payload["needs_reevaluation"] is False

    first_evaluation = db_session.get(models.Evaluation, first.json()["id"])
    assert first_evaluation is not None
    assert first_evaluation.needs_reevaluation is False

    db_session.refresh(first_request)
    assert first_request.status == models.ReevaluationStatus.COMPLETED
    assert first_request.completed_at is not None
    assert db_session.query(models.ReevaluationRequest).filter_by(
        instructor_id=instructor.id,
        skill_id=skill.id,
        status=models.ReevaluationStatus.OPEN,
    ).count() == 0

    flagged = client.get("/supervisor/evaluations?needs_reevaluation=true", headers=headers)
    assert flagged.status_code == 200
    assert flagged.json() == []


def test_follow_up_evaluation_with_source_id_clears_previous_reevaluation(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Supervisor", "reeval.source.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "reeval.source.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Source Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Source Skill")
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(school_id=school.id, name="Source Control", description="desc")
    db_session.add(attr)
    db_session.flush()
    db_session.add(models.SkillAttribute(skill_id=skill.id, attribute_id=attr.id))
    db_session.commit()

    headers = auth_headers(client, "reeval.source.supervisor@test.local")
    first = client.post(
        "/supervisor/evaluations",
        headers=headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "ratings": [{"attribute_id": attr.id, "rating": 2}],
            "notes": "Needs follow up",
        },
    )
    assert first.status_code == 200, first.text
    first_id = first.json()["id"]

    second = client.post(
        "/supervisor/evaluations",
        headers=headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "source_evaluation_id": first_id,
            "ratings": [{"attribute_id": attr.id, "rating": 4}],
            "notes": "Follow-up complete",
        },
    )
    assert second.status_code == 200, second.text
    second_payload = second.json()
    assert second_payload["needs_reevaluation"] is False

    first_evaluation = db_session.get(models.Evaluation, first_id)
    assert first_evaluation is not None
    assert first_evaluation.needs_reevaluation is False

    flagged = client.get("/supervisor/evaluations?needs_reevaluation=true", headers=headers)
    assert flagged.status_code == 200
    assert flagged.json() == []


def test_updating_evaluation_to_passing_grade_completes_reevaluation_request(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "reeval.manager@test.local", models.UserRole.MANAGER, school.id)
    supervisor = create_user(db_session, "Supervisor", "reeval.update.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "reeval.update.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Update Reeval Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Update Reeval Skill")
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(school_id=school.id, name="Recovery", description="desc")
    db_session.add(attr)
    db_session.flush()
    db_session.add(models.SkillAttribute(skill_id=skill.id, attribute_id=attr.id))
    db_session.commit()

    supervisor_headers = auth_headers(client, "reeval.update.supervisor@test.local")
    created = client.post(
        "/supervisor/evaluations",
        headers=supervisor_headers,
        json={
            "instructor_id": instructor.id,
            "skill_id": skill.id,
            "needs_reevaluation": True,
            "notes": "Manager should follow up",
            "ratings": [{"attribute_id": attr.id, "rating": 2}],
        },
    )
    assert created.status_code == 200, created.text
    created_payload = created.json()
    assert created_payload["needs_reevaluation"] is True

    request = db_session.query(models.ReevaluationRequest).filter_by(
        instructor_id=instructor.id,
        skill_id=skill.id,
        status=models.ReevaluationStatus.OPEN,
    ).one()

    manager_headers = auth_headers(client, "reeval.manager@test.local")
    updated = client.put(
        f"/manager/evaluations/{created_payload['id']}",
        headers=manager_headers,
        json={
            "notes": "Improved enough",
            "ratings": [{"attribute_id": attr.id, "rating": 4}],
            "needs_reevaluation": False,
        },
    )
    assert updated.status_code == 200, updated.text
    updated_payload = updated.json()
    assert updated_payload["final_grade"] == 4
    assert updated_payload["needs_reevaluation"] is False

    evaluation = db_session.get(models.Evaluation, created_payload["id"])
    assert evaluation is not None
    assert evaluation.needs_reevaluation is False

    db_session.refresh(request)
    assert request.status == models.ReevaluationStatus.COMPLETED
    assert request.completed_at is not None


def test_manager_can_delete_evaluation_and_missing_returns_404(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "delete.eval.manager@test.local", models.UserRole.MANAGER, school.id)
    supervisor = create_user(db_session, "Supervisor", "delete.eval.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "delete.eval.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Delete Eval Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Delete Eval Skill")
    db_session.add(skill)
    db_session.flush()
    evaluation = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        skill_id=skill.id,
        final_grade=3,
        notes="delete me",
    )
    db_session.add(evaluation)
    db_session.commit()

    headers = auth_headers(client, "delete.eval.manager@test.local")

    missing = client.delete("/manager/evaluations/999999", headers=headers)
    assert missing.status_code == 404

    deleted = client.delete(f"/manager/evaluations/{evaluation.id}", headers=headers)
    assert deleted.status_code == 204
    assert db_session.get(models.Evaluation, evaluation.id) is None


def test_manager_evaluations_can_filter_needs_reevaluation(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager.reeval@test.local", models.UserRole.MANAGER, school.id)
    supervisor = create_user(db_session, "Supervisor", "manager.reeval.supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "manager.reeval.instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Manager Reeval Level")
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Manager Reeval Skill")
    db_session.add(skill)
    db_session.flush()

    flagged = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        skill_id=skill.id,
        final_grade=2,
        needs_reevaluation=True,
        notes="flagged",
    )
    clear = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        skill_id=skill.id,
        final_grade=4,
        needs_reevaluation=False,
        notes="clear",
    )
    db_session.add_all([flagged, clear])
    db_session.commit()

    headers = auth_headers(client, "manager.reeval@test.local")
    response = client.get("/manager/evaluations?needs_reevaluation=true", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == flagged.id
    assert payload[0]["needs_reevaluation"] is True
