from datetime import date, datetime, timezone
from pathlib import Path
import sys

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
    school = models.School(name=name, active=True)
    db.add(school)
    db.flush()
    return school


def create_user(
    db: Session,
    name: str,
    email: str,
    role: models.UserRole,
    school_id: int,
) -> models.User:
    user = models.User(
        school_id=school_id,
        name=name,
        email=email,
        password_hash=hash_password("TestPass123!"),
        role=role,
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
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
    response = client.post("/manager/levels", headers=supervisor_headers, json={"name": "Beginner", "active": True})
    assert response.status_code == 403

    manager_headers = auth_headers(client, "manager@test.local")
    success = client.post("/manager/levels", headers=manager_headers, json={"name": "Beginner", "active": True})
    assert success.status_code == 200


def test_login_rate_limit_blocks_excessive_attempts(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager-rate@test.local", models.UserRole.MANAGER, school.id)
    auth_router.login_limiter.max_requests = 2
    auth_router.login_limiter.window_seconds = 60
    headers = {"X-Forwarded-For": "1.2.3.4"}

    invalid_1 = client.post("/auth/login", headers=headers, json={"email": "manager-rate@test.local", "password": "bad-pass"})
    assert invalid_1.status_code == 401
    invalid_2 = client.post("/auth/login", headers=headers, json={"email": "manager-rate@test.local", "password": "bad-pass"})
    assert invalid_2.status_code == 401
    blocked = client.post("/auth/login", headers=headers, json={"email": "manager-rate@test.local", "password": "TestPass123!"})
    assert blocked.status_code == 429


def test_supervisor_submit_flow_and_instructor_visibility(client: TestClient, db_session: Session):
    school = create_school(db_session)
    supervisor = create_user(db_session, "Supervisor", "supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "instructor@test.local", models.UserRole.INSTRUCTOR, school.id)
    create_user(db_session, "Other Instructor", "other@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Beginner", active=True)
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(school_id=school.id, level_id=level.id, name="Freestyle", active=True)
    db_session.add(skill)
    db_session.flush()
    attr1 = models.Attribute(name="Safety", description="desc", active=True)
    attr2 = models.Attribute(name="Technique", description="desc", active=True)
    db_session.add_all([attr1, attr2])
    db_session.flush()
    template = models.Template(
        school_id=school.id, name="Template A", level_id=level.id, skill_id=skill.id, active=True
    )
    db_session.add(template)
    db_session.flush()
    db_session.add_all(
        [
            models.TemplateAttribute(template_id=template.id, attribute_id=attr1.id, sort_order=1),
            models.TemplateAttribute(template_id=template.id, attribute_id=attr2.id, sort_order=2),
        ]
    )
    db_session.commit()

    supervisor_headers = auth_headers(client, "supervisor@test.local")
    draft_response = client.post(
        "/supervisor/evaluations",
        headers=supervisor_headers,
        json={
            "instructor_id": instructor.id,
            "level_id": level.id,
            "skill_id": skill.id,
            "session_label": "Session A",
            "session_date": date.today().isoformat(),
            "notes": "Draft notes",
            "ratings": [
                {"attribute_id": attr1.id, "rating_value": 2},
                {"attribute_id": attr2.id, "rating_value": 3},
            ],
        },
    )
    assert draft_response.status_code == 200
    evaluation_id = draft_response.json()["id"]
    assert draft_response.json()["status"] == "DRAFT"

    submit_response = client.post(f"/supervisor/evaluations/{evaluation_id}/submit", headers=supervisor_headers)
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "SUBMITTED"

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


def test_submit_rejects_missing_required_template_ratings(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Supervisor", "supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Intermediate", active=True)
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(school_id=school.id, level_id=level.id, name="Backstroke", active=True)
    db_session.add(skill)
    db_session.flush()
    attr1 = models.Attribute(name="Timing", description="desc", active=True)
    attr2 = models.Attribute(name="Power", description="desc", active=True)
    db_session.add_all([attr1, attr2])
    db_session.flush()
    template = models.Template(
        school_id=school.id, name="Template B", level_id=level.id, skill_id=skill.id, active=True
    )
    db_session.add(template)
    db_session.flush()
    db_session.add_all(
        [
            models.TemplateAttribute(template_id=template.id, attribute_id=attr1.id, sort_order=1),
            models.TemplateAttribute(template_id=template.id, attribute_id=attr2.id, sort_order=2),
        ]
    )
    db_session.commit()

    supervisor_headers = auth_headers(client, "supervisor@test.local")
    draft = client.post(
        "/supervisor/evaluations",
        headers=supervisor_headers,
        json={
            "instructor_id": instructor.id,
            "level_id": level.id,
            "skill_id": skill.id,
            "session_label": "Session B",
            "session_date": date.today().isoformat(),
            "notes": "Partial ratings",
            "ratings": [
                {"attribute_id": attr1.id, "rating_value": 2},
            ],
        },
    )
    assert draft.status_code == 200
    evaluation_id = draft.json()["id"]

    submit = client.post(f"/supervisor/evaluations/{evaluation_id}/submit", headers=supervisor_headers)
    assert submit.status_code == 200
    assert submit.json()["status"] == "SUBMITTED"


def test_manager_csv_export_returns_data(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager@test.local", models.UserRole.MANAGER, school.id)
    supervisor = create_user(db_session, "Supervisor", "supervisor@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "instructor@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Advanced", active=True)
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(school_id=school.id, level_id=level.id, name="Butterfly", active=True)
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(name="Form", description="desc", active=True)
    db_session.add(attr)
    db_session.flush()

    evaluation = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        level_id=level.id,
        skill_id=skill.id,
        session_label="Export Session",
        session_date=date.today(),
        notes="Ready for export",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime.now(timezone.utc),
    )
    evaluation.ratings = [models.EvaluationRating(attribute_id=attr.id, rating_value=3)]
    db_session.add(evaluation)
    db_session.commit()

    manager_headers = auth_headers(client, "manager@test.local")
    export_response = client.get("/manager/exports/evaluations.csv", headers=manager_headers)
    assert export_response.status_code == 200
    assert "text/csv" in export_response.headers["content-type"]
    body = export_response.text
    assert "evaluation_id" in body
    assert "Export Session" in body


def test_manager_evaluations_support_pagination_sort_and_filters(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager2@test.local", models.UserRole.MANAGER, school.id)
    supervisor = create_user(db_session, "Supervisor", "supervisor2@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "instructor2@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Level A", active=True)
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(school_id=school.id, level_id=level.id, name="Skill A", active=True)
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(name="Attr A", description="desc", active=True)
    db_session.add(attr)
    db_session.flush()

    ev1 = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        level_id=level.id,
        skill_id=skill.id,
        session_label="Eval 1",
        session_date=date(2026, 1, 10),
        notes="older",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime.now(timezone.utc),
    )
    ev1.ratings = [models.EvaluationRating(attribute_id=attr.id, rating_value=2)]
    ev2 = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        level_id=level.id,
        skill_id=skill.id,
        session_label="Eval 2",
        session_date=date(2026, 1, 20),
        notes="newer",
        status=models.EvaluationStatus.DRAFT,
    )
    ev2.ratings = [models.EvaluationRating(attribute_id=attr.id, rating_value=3)]
    db_session.add_all([ev1, ev2])
    db_session.commit()

    manager_headers = auth_headers(client, "manager2@test.local")
    response = client.get(
        "/manager/evaluations?status=SUBMITTED&sort_by=session_date&sort_dir=asc&limit=1&offset=0",
        headers=manager_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["session_label"] == "Eval 1"

    export = client.get(
        "/manager/exports/evaluations.csv?status=SUBMITTED&sort_by=session_date&sort_dir=asc",
        headers=manager_headers,
    )
    assert export.status_code == 200
    csv_data = export.text
    assert "Eval 1" in csv_data
    assert "Eval 2" not in csv_data


def test_instructor_supervisor_filter_and_trends(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager3@test.local", models.UserRole.MANAGER, school.id)
    supervisor_a = create_user(db_session, "Supervisor A", "supervisorA@test.local", models.UserRole.SUPERVISOR, school.id)
    supervisor_b = create_user(db_session, "Supervisor B", "supervisorB@test.local", models.UserRole.SUPERVISOR, school.id)
    instructor = create_user(db_session, "Instructor", "instructor3@test.local", models.UserRole.INSTRUCTOR, school.id)

    level = models.Level(school_id=school.id, name="Level Trend", active=True)
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(school_id=school.id, level_id=level.id, name="Skill Trend", active=True)
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(name="Attr Trend", description="desc", active=True)
    db_session.add(attr)
    db_session.flush()

    ev_a = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor_a.id,
        level_id=level.id,
        skill_id=skill.id,
        session_label="Trend A",
        session_date=date(2026, 2, 1),
        notes="A",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime.now(timezone.utc),
    )
    ev_a.ratings = [models.EvaluationRating(attribute_id=attr.id, rating_value=3)]
    ev_b = models.Evaluation(
        school_id=school.id,
        instructor_id=instructor.id,
        supervisor_id=supervisor_b.id,
        level_id=level.id,
        skill_id=skill.id,
        session_label="Trend B",
        session_date=date(2026, 2, 10),
        notes="B",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime.now(timezone.utc),
    )
    ev_b.ratings = [models.EvaluationRating(attribute_id=attr.id, rating_value=1)]
    db_session.add_all([ev_a, ev_b])
    db_session.commit()

    headers = auth_headers(client, "instructor3@test.local")
    filtered = client.get(f"/instructor/evaluations?supervisor_id={supervisor_a.id}", headers=headers)
    assert filtered.status_code == 200
    payload = filtered.json()
    assert len(payload) == 1
    assert payload[0]["session_label"] == "Trend A"


def test_manager_can_update_template_attributes_and_active_state(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager4@test.local", models.UserRole.MANAGER, school.id)
    level = models.Level(school_id=school.id, name="Template Level", active=True)
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(school_id=school.id, level_id=level.id, name="Template Skill", active=True)
    db_session.add(skill)
    db_session.flush()
    attr_a = models.Attribute(name="Attr T A", description="a", active=True)
    attr_b = models.Attribute(name="Attr T B", description="b", active=True)
    db_session.add_all([attr_a, attr_b])
    db_session.flush()

    template = models.Template(
        school_id=school.id, name="Template To Update", level_id=level.id, skill_id=skill.id, active=True
    )
    db_session.add(template)
    db_session.flush()
    db_session.add(models.TemplateAttribute(template_id=template.id, attribute_id=attr_a.id, sort_order=1))
    db_session.commit()

    headers = auth_headers(client, "manager4@test.local")
    updated = client.put(
        f"/manager/templates/{template.id}",
        headers=headers,
        json={"active": False, "attributes": [{"attribute_id": attr_b.id, "sort_order": 2}]},
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["active"] is False
    assert len(payload["attributes"]) == 1
    assert payload["attributes"][0]["attribute_id"] == attr_b.id


def test_manager_can_update_user_with_phone(client: TestClient, db_session: Session):
    school = create_school(db_session)
    create_user(db_session, "Manager", "manager5@test.local", models.UserRole.MANAGER, school.id)
    target = create_user(db_session, "Coach User", "coach@test.local", models.UserRole.INSTRUCTOR, school.id)

    headers = auth_headers(client, "manager5@test.local")
    response = client.put(
        f"/manager/users/{target.id}",
        headers=headers,
        json={
            "name": "Coach Updated",
            "email": "coach.updated@test.local",
            "phone": "555-0102",
            "role": "SUPERVISOR",
            "active": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Coach Updated"
    assert payload["email"] == "coach.updated@test.local"
    assert payload["phone"] == "555-0102"
    assert payload["role"] == "SUPERVISOR"
    assert payload["active"] is False


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
