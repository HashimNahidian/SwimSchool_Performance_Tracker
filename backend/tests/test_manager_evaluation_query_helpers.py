from datetime import date, datetime, timezone
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(str(Path(__file__).resolve().parents[1]))

import models
from db import Base
from routers.manager import apply_evaluation_filters, apply_evaluation_sorting
from services import evaluation_query_with_joins
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


def seed_two_school_evals(db: Session) -> dict[str, int]:
    school_a = models.School(name="Query School A", active=True)
    school_b = models.School(name="Query School B", active=True)
    db.add_all([school_a, school_b])
    db.flush()

    supervisor_a = create_user(
        db,
        school_id=school_a.id,
        name="Supervisor A",
        email="query.supervisor.a@test.local",
        role=models.UserRole.SUPERVISOR,
    )
    supervisor_b = create_user(
        db,
        school_id=school_b.id,
        name="Supervisor B",
        email="query.supervisor.b@test.local",
        role=models.UserRole.SUPERVISOR,
    )
    instructor_a = create_user(
        db,
        school_id=school_a.id,
        name="Instructor A",
        email="query.instructor.a@test.local",
        role=models.UserRole.INSTRUCTOR,
    )
    instructor_b = create_user(
        db,
        school_id=school_b.id,
        name="Instructor B",
        email="query.instructor.b@test.local",
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
        submitted_at=datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc),
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
        submitted_at=datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc),
    )
    eval_b_early_draft = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        level_id=level_b.id,
        skill_id=skill_b.id,
        session_label="School B Early Draft",
        session_date=date(2026, 2, 20),
        notes="B draft notes",
        status=models.EvaluationStatus.DRAFT,
        submitted_at=datetime(2026, 2, 20, 9, 0, tzinfo=timezone.utc),
    )
    eval_b_late_submitted = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        level_id=level_b.id,
        skill_id=skill_b.id,
        session_label="School B Late Submitted",
        session_date=date(2026, 2, 25),
        notes="B late notes",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime(2026, 2, 25, 12, 0, tzinfo=timezone.utc),
    )
    eval_b_same_date_a = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        level_id=level_b.id,
        skill_id=skill_b.id,
        session_label="School B Same Date A",
        session_date=date(2026, 2, 23),
        notes="B same A",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc),
    )
    eval_b_same_date_b = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        level_id=level_b.id,
        skill_id=skill_b.id,
        session_label="School B Same Date B",
        session_date=date(2026, 2, 23),
        notes="B same B",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime(2026, 2, 23, 11, 0, tzinfo=timezone.utc),
    )
    eval_b_tie_submitted_at_a = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        level_id=level_b.id,
        skill_id=skill_b.id,
        session_label="School B Tie SubmittedAt A",
        session_date=date(2026, 2, 22),
        notes="B tie submitted_at A",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime(2026, 2, 23, 15, 0, tzinfo=timezone.utc),
    )
    eval_b_tie_submitted_at_b = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        level_id=level_b.id,
        skill_id=skill_b.id,
        session_label="School B Tie SubmittedAt B",
        session_date=date(2026, 2, 24),
        notes="B tie submitted_at B",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime(2026, 2, 23, 15, 0, tzinfo=timezone.utc),
    )
    db.add_all(
        [
            eval_a,
            eval_b,
            eval_b_early_draft,
            eval_b_late_submitted,
            eval_b_same_date_a,
            eval_b_same_date_b,
            eval_b_tie_submitted_at_a,
            eval_b_tie_submitted_at_b,
        ]
    )
    db.flush()

    attribute = models.Attribute(name="Rating Attribute", description="for rating filter tests", active=True)
    attribute_2 = models.Attribute(name="Rating Attribute 2", description="for multi-rating tests", active=True)
    db.add_all([attribute, attribute_2])
    db.flush()

    rating_a = models.EvaluationRating(evaluation_id=eval_a.id, attribute_id=attribute.id, rating_value=3)
    rating_a_2 = models.EvaluationRating(evaluation_id=eval_a.id, attribute_id=attribute_2.id, rating_value=2)
    rating_b = models.EvaluationRating(evaluation_id=eval_b.id, attribute_id=attribute.id, rating_value=1)
    rating_b_2 = models.EvaluationRating(evaluation_id=eval_b.id, attribute_id=attribute_2.id, rating_value=2)
    db.add_all([rating_a, rating_a_2, rating_b, rating_b_2])
    db.commit()

    return {
        "school_a_id": school_a.id,
        "school_b_id": school_b.id,
        "instructor_a_id": instructor_a.id,
        "instructor_b_id": instructor_b.id,
        "supervisor_b_id": supervisor_b.id,
        "level_b_id": level_b.id,
        "skill_b_id": skill_b.id,
        "eval_a_id": eval_a.id,
        "eval_b_id": eval_b.id,
        "eval_b_same_date_a_id": eval_b_same_date_a.id,
        "eval_b_same_date_b_id": eval_b_same_date_b.id,
        "eval_b_late_submitted_id": eval_b_late_submitted.id,
        "eval_b_tie_submitted_at_a_id": eval_b_tie_submitted_at_a.id,
        "eval_b_tie_submitted_at_b_id": eval_b_tie_submitted_at_b.id,
    }


def test_cross_tenant_filter_ids_return_no_rows_for_school_scoped_base_stmt(db_session: Session):
    seeded = seed_two_school_evals(db_session)

    stmt = evaluation_query_with_joins(seeded["school_b_id"])
    stmt = apply_evaluation_filters(stmt, instructor_id=seeded["instructor_a_id"])

    rows = db_session.scalars(stmt).all()
    assert rows == []
    assert all(row.session_label != "School A Session" for row in rows)


def test_apply_evaluation_sorting_rejects_invalid_sort_by(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    stmt = evaluation_query_with_joins(seeded["school_b_id"])

    with pytest.raises(HTTPException) as exc:
        apply_evaluation_sorting(stmt, sort_by="not_a_field", sort_dir="desc")
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid sort_by"


def test_apply_evaluation_sorting_rejects_invalid_sort_dir(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    stmt = evaluation_query_with_joins(seeded["school_b_id"])

    with pytest.raises(HTTPException) as exc:
        apply_evaluation_sorting(stmt, sort_by="submitted_at", sort_dir="down")
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid sort_dir"


def test_apply_evaluation_sorting_submitted_at_desc_with_id_tiebreaker(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    school_b_id = seeded["school_b_id"]

    supervisor_b = db_session.scalar(
        select(models.User).where(
            models.User.school_id == school_b_id,
            models.User.role == models.UserRole.SUPERVISOR,
        )
    )
    instructor_b = db_session.scalar(
        select(models.User).where(
            models.User.school_id == school_b_id,
            models.User.role == models.UserRole.INSTRUCTOR,
        )
    )
    level_b = db_session.scalar(select(models.Level).where(models.Level.school_id == school_b_id))
    skill_b = db_session.scalar(select(models.Skill).where(models.Skill.school_id == school_b_id))
    assert supervisor_b is not None and instructor_b is not None and level_b is not None and skill_b is not None

    # Create two additional school-B evaluations so we can assert deterministic ordering.
    eval_b2 = models.Evaluation(
        school_id=school_b_id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        level_id=level_b.id,
        skill_id=skill_b.id,
        session_label="School B Session 2",
        session_date=date(2026, 2, 23),
        notes="B2",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime(2026, 2, 23, 11, 0, tzinfo=timezone.utc),
    )
    eval_b3 = models.Evaluation(
        school_id=school_b_id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        level_id=level_b.id,
        skill_id=skill_b.id,
        session_label="School B Session 3",
        session_date=date(2026, 2, 23),
        notes="B3",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime(2026, 2, 23, 11, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([eval_b2, eval_b3])
    db_session.commit()

    stmt = evaluation_query_with_joins(school_b_id).order_by(None)
    stmt = apply_evaluation_sorting(stmt, sort_by="submitted_at", sort_dir="desc")
    rows = db_session.scalars(stmt).all()
    row_ids = [row.id for row in rows]

    # For tied submitted_at, higher id should come first.
    assert row_ids.index(eval_b3.id) < row_ids.index(eval_b2.id)


def test_cross_tenant_rating_filter_returns_no_rows_for_school_scoped_base_stmt(db_session: Session):
    seeded = seed_two_school_evals(db_session)

    stmt = evaluation_query_with_joins(seeded["school_b_id"])
    stmt = apply_evaluation_filters(stmt, rating_value=3)

    rows = db_session.scalars(stmt).all()
    assert len(rows) == 0
    assert all(row.session_label != "School A Session" for row in rows)


def test_rating_filter_returns_rows_for_own_tenant(db_session: Session):
    seeded = seed_two_school_evals(db_session)

    stmt = evaluation_query_with_joins(seeded["school_b_id"])
    stmt = apply_evaluation_filters(stmt, rating_value=1)

    rows = db_session.scalars(stmt).all()
    assert len(rows) == 1
    assert rows[0].session_label == "School B Session"
    assert rows[0].id == seeded["eval_b_id"]


def test_filters_and_sort_compose_deterministically_for_school_b(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    school_b_id = seeded["school_b_id"]

    eval_b_tie = models.Evaluation(
        school_id=school_b_id,
        instructor_id=seeded["instructor_b_id"],
        supervisor_id=seeded["supervisor_b_id"],
        level_id=seeded["level_b_id"],
        skill_id=seeded["skill_b_id"],
        session_label="School B Session Tie",
        session_date=date(2026, 2, 23),
        notes="B tie notes",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime(2026, 2, 23, 13, 0, tzinfo=timezone.utc),
    )
    db_session.add(eval_b_tie)
    db_session.commit()

    base_stmt = evaluation_query_with_joins(school_b_id).order_by(None)
    filtered_stmt = apply_evaluation_filters(
        base_stmt,
        status_filter=models.EvaluationStatus.SUBMITTED,
        date_from=date(2026, 2, 21),
        date_to=date(2026, 2, 26),
    )
    sorted_stmt = apply_evaluation_sorting(filtered_stmt, sort_by="session_date", sort_dir="asc")

    all_rows = db_session.scalars(sorted_stmt).all()
    assert all(row.school_id == school_b_id for row in all_rows)
    assert all(row.status == models.EvaluationStatus.SUBMITTED for row in all_rows)
    assert all(date(2026, 2, 21) <= row.session_date <= date(2026, 2, 26) for row in all_rows)

    expected_ids = [
        seeded["eval_b_tie_submitted_at_a_id"],
        eval_b_tie.id,
        seeded["eval_b_same_date_b_id"],
        seeded["eval_b_same_date_a_id"],
        seeded["eval_b_id"],
        seeded["eval_b_tie_submitted_at_b_id"],
        seeded["eval_b_late_submitted_id"],
    ]
    assert [row.id for row in all_rows] == expected_ids

    page1 = db_session.scalars(sorted_stmt.limit(1).offset(0)).all()
    page2 = db_session.scalars(sorted_stmt.limit(1).offset(1)).all()
    combined = [page1[0].id, page2[0].id]
    assert combined == expected_ids[:2]


def test_date_filter_inclusive_bounds(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    school_b_id = seeded["school_b_id"]
    boundary_day = date(2026, 2, 25)

    stmt = evaluation_query_with_joins(school_b_id)
    stmt = apply_evaluation_filters(
        stmt,
        status_filter=models.EvaluationStatus.SUBMITTED,
        date_from=boundary_day,
        date_to=boundary_day,
    )
    rows = db_session.scalars(stmt).all()

    assert len(rows) == 1
    assert rows[0].session_date == boundary_day
    assert rows[0].id == seeded["eval_b_late_submitted_id"]


def test_rating_filter_matches_any_rating_for_eval_with_multiple_ratings(db_session: Session):
    seeded = seed_two_school_evals(db_session)

    stmt = evaluation_query_with_joins(seeded["school_b_id"])
    stmt = apply_evaluation_filters(stmt, rating_value=2)
    rows = db_session.scalars(stmt).all()

    assert len(rows) == 1
    assert rows[0].id == seeded["eval_b_id"]
    assert rows[0].session_label == "School B Session"
    assert all(row.school_id == seeded["school_b_id"] for row in rows)
    assert all("School A Session" != row.session_label for row in rows)


def test_rating_filter_cross_tenant_still_returns_no_rows_with_multiple_ratings(db_session: Session):
    seeded = seed_two_school_evals(db_session)

    stmt = evaluation_query_with_joins(seeded["school_b_id"])
    stmt = apply_evaluation_filters(stmt, rating_value=3)
    rows = db_session.scalars(stmt).all()

    assert len(rows) == 0


def test_limit_offset_are_applied_after_filters_and_sorting(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    school_b_id = seeded["school_b_id"]

    eval_b_tie = models.Evaluation(
        school_id=school_b_id,
        instructor_id=seeded["instructor_b_id"],
        supervisor_id=seeded["supervisor_b_id"],
        level_id=seeded["level_b_id"],
        skill_id=seeded["skill_b_id"],
        session_label="School B Session Tie 2",
        session_date=date(2026, 2, 23),
        notes="B tie 2 notes",
        status=models.EvaluationStatus.SUBMITTED,
        submitted_at=datetime(2026, 2, 23, 14, 0, tzinfo=timezone.utc),
    )
    db_session.add(eval_b_tie)
    db_session.commit()

    stmt = evaluation_query_with_joins(school_b_id).order_by(None)
    stmt = apply_evaluation_filters(stmt, status_filter=models.EvaluationStatus.SUBMITTED)
    stmt = apply_evaluation_sorting(stmt, sort_by="session_date", sort_dir="asc")

    expected_ids = [
        seeded["eval_b_tie_submitted_at_a_id"],
        eval_b_tie.id,
        seeded["eval_b_same_date_b_id"],
        seeded["eval_b_same_date_a_id"],
        seeded["eval_b_id"],
        seeded["eval_b_tie_submitted_at_b_id"],
        seeded["eval_b_late_submitted_id"],
    ]
    all_rows = db_session.scalars(stmt).all()
    assert [row.id for row in all_rows] == expected_ids

    page_1 = db_session.scalars(stmt.limit(1).offset(0)).all()
    page_2 = db_session.scalars(stmt.limit(1).offset(1)).all()
    assert [page_1[0].id, page_2[0].id] == expected_ids[:2]


def test_sort_by_session_date_asc_then_id_desc_tiebreak_is_deterministic(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    school_b_id = seeded["school_b_id"]

    stmt = evaluation_query_with_joins(school_b_id).order_by(None)
    stmt = apply_evaluation_filters(stmt, status_filter=models.EvaluationStatus.SUBMITTED)
    stmt = apply_evaluation_sorting(stmt, sort_by="session_date", sort_dir="asc")
    rows = db_session.scalars(stmt).all()

    row_ids = [row.id for row in rows]
    rows_by_id = {row.id: row for row in rows}
    row_dates = [row.session_date for row in rows]
    assert row_dates == sorted(row_dates)
    assert (
        rows_by_id[seeded["eval_b_same_date_b_id"]].session_date
        == rows_by_id[seeded["eval_b_same_date_a_id"]].session_date
    )
    assert row_ids.index(seeded["eval_b_same_date_b_id"]) < row_ids.index(seeded["eval_b_same_date_a_id"])
    assert row_ids.index(seeded["eval_b_same_date_a_id"]) < row_ids.index(seeded["eval_b_id"])


def test_sort_by_submitted_at_asc_then_id_desc_tiebreak_is_deterministic(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    school_b_id = seeded["school_b_id"]

    stmt = evaluation_query_with_joins(school_b_id).order_by(None)
    stmt = apply_evaluation_filters(stmt, status_filter=models.EvaluationStatus.SUBMITTED)
    stmt = apply_evaluation_sorting(stmt, sort_by="submitted_at", sort_dir="asc")
    rows = db_session.scalars(stmt).all()

    row_ids = [row.id for row in rows]
    rows_by_id = {row.id: row for row in rows}
    submitted_times = [row.submitted_at for row in rows]
    assert submitted_times == sorted(submitted_times)
    tie_a_id = seeded["eval_b_tie_submitted_at_a_id"]
    tie_b_id = seeded["eval_b_tie_submitted_at_b_id"]
    assert rows_by_id[tie_a_id].submitted_at == rows_by_id[tie_b_id].submitted_at
    higher_id = tie_a_id if tie_a_id > tie_b_id else tie_b_id
    lower_id = tie_b_id if tie_a_id > tie_b_id else tie_a_id
    assert row_ids.index(higher_id) < row_ids.index(lower_id)


def test_sorting_invalid_inputs_still_raise_400(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    stmt = evaluation_query_with_joins(seeded["school_b_id"]).order_by(None)

    with pytest.raises(HTTPException) as invalid_sort_by:
        apply_evaluation_sorting(stmt, sort_by="nope", sort_dir="asc")
    assert invalid_sort_by.value.status_code == 400
    assert invalid_sort_by.value.detail == "Invalid sort_by"

    with pytest.raises(HTTPException) as invalid_sort_dir:
        apply_evaluation_sorting(stmt, sort_by="session_date", sort_dir="sideways")
    assert invalid_sort_dir.value.status_code == 400
    assert invalid_sort_dir.value.detail == "Invalid sort_dir"
