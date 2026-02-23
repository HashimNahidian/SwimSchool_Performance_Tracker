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


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_user(
    db: Session,
    *,
    school_id: int,
    name: str,
    email: str,
    role: models.UserRole,
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
    db.flush()
    return user


def seed_two_school_evals(db: Session) -> dict[str, int | str]:
    school_a = models.School(name="School A", active=True)
    school_b = models.School(name="School B", active=True)
    db.add_all([school_a, school_b])
    db.flush()

    manager_a = create_user(
        db,
        school_id=school_a.id,
        name="Manager A",
        email="manager.a@test.local",
        role=models.UserRole.MANAGER,
    )
    manager_b = create_user(
        db,
        school_id=school_b.id,
        name="Manager B",
        email="manager.b@test.local",
        role=models.UserRole.MANAGER,
    )
    supervisor_a = create_user(
        db,
        school_id=school_a.id,
        name="Supervisor A",
        email="supervisor.a@test.local",
        role=models.UserRole.SUPERVISOR,
    )
    supervisor_b = create_user(
        db,
        school_id=school_b.id,
        name="Supervisor B",
        email="supervisor.b@test.local",
        role=models.UserRole.SUPERVISOR,
    )
    instructor_a = create_user(
        db,
        school_id=school_a.id,
        name="Instructor A",
        email="instructor.a@test.local",
        role=models.UserRole.INSTRUCTOR,
    )
    instructor_b = create_user(
        db,
        school_id=school_b.id,
        name="Instructor B",
        email="instructor.b@test.local",
        role=models.UserRole.INSTRUCTOR,
    )

    level_a = models.Level(school_id=school_a.id, name="Level A", active=True)
    level_b = models.Level(school_id=school_b.id, name="Level B", active=True)
    db.add_all([level_a, level_b])
    db.flush()

    skill_a = models.Skill(school_id=school_a.id, level_id=level_a.id, name="Skill A", active=True)
    skill_b = models.Skill(school_id=school_b.id, level_id=level_b.id, name="Skill B", active=True)
    db.add_all([skill_a, skill_b])
    db.flush()

    eval_a = models.Evaluation(
        school_id=school_a.id,
        instructor_id=instructor_a.id,
        supervisor_id=supervisor_a.id,
        level_id=level_a.id,
        skill_id=skill_a.id,
        session_label="School A Session",
        session_date=date(2026, 2, 23),
        notes="A notes",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime.now(timezone.utc),
    )
    eval_b = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        level_id=level_b.id,
        skill_id=skill_b.id,
        session_label="School B Session",
        session_date=date(2026, 2, 23),
        notes="B notes",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add_all([eval_a, eval_b])
    db.commit()

    return {
        "manager_a_email": manager_a.email,
        "manager_b_email": manager_b.email,
        "eval_a_id": eval_a.id,
        "eval_b_id": eval_b.id,
        "instructor_a_id": instructor_a.id,
    }


def test_manager_email_export_returns_501_when_smtp_not_configured(client: TestClient, db_session: Session):
    seeded = seed_two_school_evals(db_session)
    manager_headers = auth_headers(client, str(seeded["manager_a_email"]))
    response = client.post(
        "/manager/exports/evaluations/email",
        headers=manager_headers,
        json={"to": ["recipient@example.com"]},
    )
    assert response.status_code == 501
    assert response.json()["detail"] == "Email not configured"


def test_manager_email_export_filters_are_school_scoped(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    seeded = seed_two_school_evals(db_session)
    manager_b_headers = auth_headers(client, str(seeded["manager_b_email"]))

    captured: dict[str, str] = {}

    def fake_send_csv_email(
        recipients: list[str],
        subject: str,
        message: str,
        csv_text: str,
    ) -> None:
        captured["csv"] = csv_text

    monkeypatch.setattr("routers.manager.send_csv_email", fake_send_csv_email)

    response = client.post(
        "/manager/exports/evaluations/email",
        headers=manager_b_headers,
        json={
            "to": ["recipient@example.com"],
            "filters": {
                "instructor_id": seeded["instructor_a_id"],
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["detail"] == "Email sent"

    csv_text = captured["csv"]
    assert str(seeded["eval_a_id"]) not in csv_text
    assert "School A Session" not in csv_text
    assert csv_text.count("\n") == 1
