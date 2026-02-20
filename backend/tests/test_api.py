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
from db import Base
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

    main.app.dependency_overrides[main.get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


def create_user(db: Session, name: str, email: str, role: models.UserRole) -> models.User:
    user = models.User(
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


def test_manager_only_endpoint_rejects_supervisor(client: TestClient, db_session: Session):
    create_user(db_session, "Manager", "manager@test.local", models.UserRole.manager)
    create_user(db_session, "Supervisor", "supervisor@test.local", models.UserRole.supervisor)

    supervisor_headers = auth_headers(client, "supervisor@test.local")
    response = client.post("/levels", headers=supervisor_headers, json={"name": "Beginner", "active": True})
    assert response.status_code == 403

    manager_headers = auth_headers(client, "manager@test.local")
    success = client.post("/levels", headers=manager_headers, json={"name": "Beginner", "active": True})
    assert success.status_code == 200


def test_supervisor_submit_flow_and_instructor_visibility(client: TestClient, db_session: Session):
    supervisor = create_user(db_session, "Supervisor", "supervisor@test.local", models.UserRole.supervisor)
    instructor = create_user(db_session, "Instructor", "instructor@test.local", models.UserRole.instructor)
    create_user(db_session, "Other Instructor", "other@test.local", models.UserRole.instructor)

    level = models.Level(name="Beginner", active=True)
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Freestyle", active=True)
    db_session.add(skill)
    db_session.flush()
    attr1 = models.Attribute(name="Safety", description="desc", active=True)
    attr2 = models.Attribute(name="Technique", description="desc", active=True)
    db_session.add_all([attr1, attr2])
    db_session.flush()
    template = models.Template(name="Template A", level_id=level.id, skill_id=skill.id, active=True)
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
        "/evaluations/draft",
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

    submit_response = client.post(f"/evaluations/{evaluation_id}/submit", headers=supervisor_headers)
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "SUBMITTED"

    instructor_headers = auth_headers(client, "instructor@test.local")
    list_response = client.get("/me/evaluations", headers=instructor_headers)
    assert list_response.status_code == 200
    returned_ids = [item["id"] for item in list_response.json()]
    assert evaluation_id in returned_ids

    details_response = client.get(f"/evaluations/{evaluation_id}", headers=instructor_headers)
    assert details_response.status_code == 200

    other_headers = auth_headers(client, "other@test.local")
    forbidden = client.get(f"/evaluations/{evaluation_id}", headers=other_headers)
    assert forbidden.status_code == 403

    owner_eval = db_session.get(models.Evaluation, evaluation_id)
    assert owner_eval is not None
    assert owner_eval.supervisor_id == supervisor.id


def test_submit_rejects_missing_required_template_ratings(client: TestClient, db_session: Session):
    create_user(db_session, "Supervisor", "supervisor@test.local", models.UserRole.supervisor)
    instructor = create_user(db_session, "Instructor", "instructor@test.local", models.UserRole.instructor)

    level = models.Level(name="Intermediate", active=True)
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Backstroke", active=True)
    db_session.add(skill)
    db_session.flush()
    attr1 = models.Attribute(name="Timing", description="desc", active=True)
    attr2 = models.Attribute(name="Power", description="desc", active=True)
    db_session.add_all([attr1, attr2])
    db_session.flush()
    template = models.Template(name="Template B", level_id=level.id, skill_id=skill.id, active=True)
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
        "/evaluations/draft",
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

    submit = client.post(f"/evaluations/{evaluation_id}/submit", headers=supervisor_headers)
    assert submit.status_code == 400
    assert "Missing one or more required template ratings" in submit.json()["detail"]


def test_manager_csv_export_returns_data(client: TestClient, db_session: Session):
    manager = create_user(db_session, "Manager", "manager@test.local", models.UserRole.manager)
    supervisor = create_user(db_session, "Supervisor", "supervisor@test.local", models.UserRole.supervisor)
    instructor = create_user(db_session, "Instructor", "instructor@test.local", models.UserRole.instructor)

    level = models.Level(name="Advanced", active=True)
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Butterfly", active=True)
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(name="Form", description="desc", active=True)
    db_session.add(attr)
    db_session.flush()

    evaluation = models.Evaluation(
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        level_id=level.id,
        skill_id=skill.id,
        session_label="Export Session",
        session_date=date.today(),
        notes="Ready for export",
        status=models.EvaluationStatus.submitted,
        submitted_at=datetime.now(timezone.utc),
    )
    evaluation.ratings = [models.EvaluationRating(attribute_id=attr.id, rating_value=3)]
    db_session.add(evaluation)
    db_session.add(
        models.AuditLog(
            actor_user_id=manager.id,
            action="TEST_EXPORT",
            entity_type="evaluation",
            entity_id="1",
        )
    )
    db_session.commit()

    manager_headers = auth_headers(client, "manager@test.local")
    export_response = client.get("/exports/evaluations.csv", headers=manager_headers)
    assert export_response.status_code == 200
    assert "text/csv" in export_response.headers["content-type"]
    body = export_response.text
    assert "evaluation_id" in body
    assert "Export Session" in body


def test_manager_evaluations_support_pagination_sort_and_filters(client: TestClient, db_session: Session):
    manager = create_user(db_session, "Manager", "manager2@test.local", models.UserRole.manager)
    supervisor = create_user(db_session, "Supervisor", "supervisor2@test.local", models.UserRole.supervisor)
    instructor = create_user(db_session, "Instructor", "instructor2@test.local", models.UserRole.instructor)

    level = models.Level(name="Level A", active=True)
    db_session.add(level)
    db_session.flush()
    skill = models.Skill(level_id=level.id, name="Skill A", active=True)
    db_session.add(skill)
    db_session.flush()
    attr = models.Attribute(name="Attr A", description="desc", active=True)
    db_session.add(attr)
    db_session.flush()

    ev1 = models.Evaluation(
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        level_id=level.id,
        skill_id=skill.id,
        session_label="Eval 1",
        session_date=date(2026, 1, 10),
        notes="older",
        status=models.EvaluationStatus.submitted,
        submitted_at=datetime.now(timezone.utc),
    )
    ev1.ratings = [models.EvaluationRating(attribute_id=attr.id, rating_value=2)]
    ev2 = models.Evaluation(
        instructor_id=instructor.id,
        supervisor_id=supervisor.id,
        level_id=level.id,
        skill_id=skill.id,
        session_label="Eval 2",
        session_date=date(2026, 1, 20),
        notes="newer",
        status=models.EvaluationStatus.draft,
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
        "/exports/evaluations.csv?status=SUBMITTED&sort_by=session_date&sort_dir=asc",
        headers=manager_headers,
    )
    assert export.status_code == 200
    csv_data = export.text
    assert "Eval 1" in csv_data
    assert "Eval 2" not in csv_data
