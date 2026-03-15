from datetime import datetime, timezone
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
        full_name=name,
        email=email,
        password_hash=hash_password("TestPass123!"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def seed_two_school_evals(db: Session) -> dict[str, int]:
    school_a = models.School(name="Query School A")
    school_b = models.School(name="Query School B")
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

    level_a = models.Level(school_id=school_a.id, name="Level A")
    level_b = models.Level(school_id=school_b.id, name="Level B")
    db.add_all([level_a, level_b])
    db.flush()

    skill_a = models.Skill(level_id=level_a.id, name="Skill A")
    skill_b = models.Skill(level_id=level_b.id, name="Skill B")
    db.add_all([skill_a, skill_b])
    db.flush()

    # School A: one evaluation with final_grade=5 (unique value for cross-tenant tests)
    eval_a = models.Evaluation(
        school_id=school_a.id,
        instructor_id=instructor_a.id,
        supervisor_id=supervisor_a.id,
        skill_id=skill_a.id,
        notes="A notes",
        final_grade=5,
        created_at=datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc),
    )

    # School B: multiple evaluations with different final_grade and created_at
    eval_b = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        skill_id=skill_b.id,
        notes="B notes",
        final_grade=1,
        needs_reevaluation=True,
        created_at=datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc),
    )
    eval_b_early = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        skill_id=skill_b.id,
        notes="B early notes",
        final_grade=2,
        created_at=datetime(2026, 2, 20, 9, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 20, 9, 0, tzinfo=timezone.utc),
    )
    eval_b_late = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        skill_id=skill_b.id,
        notes="B late notes",
        final_grade=3,
        created_at=datetime(2026, 2, 25, 12, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 25, 12, 0, tzinfo=timezone.utc),
    )
    eval_b_same_grade_a = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        skill_id=skill_b.id,
        notes="B same grade A",
        final_grade=2,
        created_at=datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc),
    )
    eval_b_same_grade_b = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        skill_id=skill_b.id,
        notes="B same grade B",
        final_grade=2,
        created_at=datetime(2026, 2, 23, 11, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 23, 11, 0, tzinfo=timezone.utc),
    )
    eval_b_tie_created_a = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        skill_id=skill_b.id,
        notes="B tie created A",
        final_grade=4,
        created_at=datetime(2026, 2, 23, 15, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 23, 15, 0, tzinfo=timezone.utc),
    )
    eval_b_tie_created_b = models.Evaluation(
        school_id=school_b.id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        skill_id=skill_b.id,
        notes="B tie created B",
        final_grade=4,
        created_at=datetime(2026, 2, 23, 15, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 23, 15, 0, tzinfo=timezone.utc),
    )
    db.add_all(
        [
            eval_a,
            eval_b,
            eval_b_early,
            eval_b_late,
            eval_b_same_grade_a,
            eval_b_same_grade_b,
            eval_b_tie_created_a,
            eval_b_tie_created_b,
        ]
    )
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
        "eval_b_early_id": eval_b_early.id,
        "eval_b_late_id": eval_b_late.id,
        "eval_b_same_grade_a_id": eval_b_same_grade_a.id,
        "eval_b_same_grade_b_id": eval_b_same_grade_b.id,
        "eval_b_tie_created_a_id": eval_b_tie_created_a.id,
        "eval_b_tie_created_b_id": eval_b_tie_created_b.id,
    }


def test_cross_tenant_filter_ids_return_no_rows_for_school_scoped_base_stmt(db_session: Session):
    seeded = seed_two_school_evals(db_session)

    stmt = evaluation_query_with_joins(seeded["school_b_id"])
    stmt = apply_evaluation_filters(stmt, instructor_id=seeded["instructor_a_id"])

    rows = db_session.scalars(stmt).all()
    assert rows == []
    assert all(row.notes != "A notes" for row in rows)


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
        apply_evaluation_sorting(stmt, sort_by="final_grade", sort_dir="down")
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid sort_dir"


def test_apply_evaluation_sorting_created_at_desc_with_id_tiebreaker(db_session: Session):
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
    skill_b = db_session.scalar(select(models.Skill).where(models.Skill.level_id == level_b.id))
    assert supervisor_b is not None and instructor_b is not None and level_b is not None and skill_b is not None

    # Create two additional school-B evaluations with the same created_at.
    same_ts = datetime(2026, 2, 28, 10, 0, tzinfo=timezone.utc)
    eval_b_new1 = models.Evaluation(
        school_id=school_b_id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        skill_id=skill_b.id,
        notes="new1",
        final_grade=3,
        created_at=same_ts,
        updated_at=same_ts,
    )
    eval_b_new2 = models.Evaluation(
        school_id=school_b_id,
        instructor_id=instructor_b.id,
        supervisor_id=supervisor_b.id,
        skill_id=skill_b.id,
        notes="new2",
        final_grade=3,
        created_at=same_ts,
        updated_at=same_ts,
    )
    db_session.add_all([eval_b_new1, eval_b_new2])
    db_session.commit()

    stmt = evaluation_query_with_joins(school_b_id).order_by(None)
    stmt = apply_evaluation_sorting(stmt, sort_by="created_at", sort_dir="desc")
    rows = db_session.scalars(stmt).all()
    row_ids = [row.id for row in rows]

    # For tied created_at, higher id should come first (tiebreaker is desc(Evaluation.id))
    assert row_ids.index(eval_b_new2.id) < row_ids.index(eval_b_new1.id)


def test_cross_tenant_final_grade_filter_returns_no_rows_for_school_scoped_base_stmt(db_session: Session):
    seeded = seed_two_school_evals(db_session)

    # School A's eval has final_grade=5; school B has no eval with final_grade=5
    stmt = evaluation_query_with_joins(seeded["school_b_id"])
    stmt = apply_evaluation_filters(stmt, final_grade=5)

    rows = db_session.scalars(stmt).all()
    assert len(rows) == 0
    assert all(row.notes != "A notes" for row in rows)


def test_final_grade_filter_returns_rows_for_own_tenant(db_session: Session):
    seeded = seed_two_school_evals(db_session)

    stmt = evaluation_query_with_joins(seeded["school_b_id"])
    stmt = apply_evaluation_filters(stmt, final_grade=1)

    rows = db_session.scalars(stmt).all()
    assert len(rows) == 1
    assert rows[0].notes == "B notes"
    assert rows[0].id == seeded["eval_b_id"]


def test_filters_and_sort_compose_deterministically_for_school_b(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    school_b_id = seeded["school_b_id"]

    # Add one more eval with final_grade=2 for the sort test
    eval_b_tie = models.Evaluation(
        school_id=school_b_id,
        instructor_id=seeded["instructor_b_id"],
        supervisor_id=seeded["supervisor_b_id"],
        skill_id=seeded["skill_b_id"],
        notes="B tie notes",
        final_grade=2,
        created_at=datetime(2026, 2, 23, 13, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 23, 13, 0, tzinfo=timezone.utc),
    )
    db_session.add(eval_b_tie)
    db_session.commit()

    base_stmt = evaluation_query_with_joins(school_b_id).order_by(None)
    # Filter by final_grade=2 to get only grade-2 evals
    filtered_stmt = apply_evaluation_filters(base_stmt, final_grade=2)
    sorted_stmt = apply_evaluation_sorting(filtered_stmt, sort_by="final_grade", sort_dir="asc")

    all_rows = db_session.scalars(sorted_stmt).all()
    assert all(row.school_id == school_b_id for row in all_rows)
    assert all(row.final_grade == 2 for row in all_rows)

    # All rows have final_grade=2, tiebreaker is id desc
    row_ids = [row.id for row in all_rows]
    assert row_ids == sorted(row_ids, reverse=True)

    # Pagination should be stable
    page1 = db_session.scalars(sorted_stmt.limit(1).offset(0)).all()
    page2 = db_session.scalars(sorted_stmt.limit(1).offset(1)).all()
    combined = [page1[0].id, page2[0].id]
    assert combined == row_ids[:2]


def test_date_filter_selects_evaluations_within_range(db_session: Session):
    from datetime import date

    seeded = seed_two_school_evals(db_session)
    school_b_id = seeded["school_b_id"]

    # date_from=2026-02-24 should include eval_b_late (created 2026-02-25)
    # and exclude eval_b (created 2026-02-23) and eval_b_early (created 2026-02-20)
    stmt = evaluation_query_with_joins(school_b_id)
    stmt = apply_evaluation_filters(stmt, date_from=date(2026, 2, 24))
    rows = db_session.scalars(stmt).all()

    row_ids = [row.id for row in rows]
    assert seeded["eval_b_late_id"] in row_ids
    assert seeded["eval_b_id"] not in row_ids
    assert seeded["eval_b_early_id"] not in row_ids


def test_final_grade_filter_returns_multiple_rows_for_same_grade(db_session: Session):
    seeded = seed_two_school_evals(db_session)

    stmt = evaluation_query_with_joins(seeded["school_b_id"])
    stmt = apply_evaluation_filters(stmt, final_grade=2)
    rows = db_session.scalars(stmt).all()

    # eval_b_early, eval_b_same_grade_a, eval_b_same_grade_b all have final_grade=2
    assert len(rows) == 3
    assert all(row.school_id == seeded["school_b_id"] for row in rows)
    assert all(row.final_grade == 2 for row in rows)


def test_final_grade_cross_tenant_filter_returns_no_rows(db_session: Session):
    seeded = seed_two_school_evals(db_session)

    # final_grade=5 only exists in school A
    stmt = evaluation_query_with_joins(seeded["school_b_id"])
    stmt = apply_evaluation_filters(stmt, final_grade=5)
    rows = db_session.scalars(stmt).all()

    assert len(rows) == 0


def test_limit_offset_are_applied_after_filters_and_sorting(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    school_b_id = seeded["school_b_id"]

    stmt = evaluation_query_with_joins(school_b_id).order_by(None)
    stmt = apply_evaluation_filters(stmt, final_grade=2)
    stmt = apply_evaluation_sorting(stmt, sort_by="final_grade", sort_dir="asc")

    # All grade=2 rows sorted by id desc (tiebreaker)
    all_rows = db_session.scalars(stmt).all()
    expected_ids = [row.id for row in all_rows]
    assert len(expected_ids) == 3  # eval_b_early, eval_b_same_grade_a, eval_b_same_grade_b

    page_1 = db_session.scalars(stmt.limit(1).offset(0)).all()
    page_2 = db_session.scalars(stmt.limit(1).offset(1)).all()
    assert [page_1[0].id, page_2[0].id] == expected_ids[:2]


def test_sort_by_final_grade_asc_then_id_desc_tiebreak_is_deterministic(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    school_b_id = seeded["school_b_id"]

    stmt = evaluation_query_with_joins(school_b_id).order_by(None)
    stmt = apply_evaluation_filters(stmt, final_grade=2)
    stmt = apply_evaluation_sorting(stmt, sort_by="final_grade", sort_dir="asc")
    rows = db_session.scalars(stmt).all()

    row_ids = [row.id for row in rows]
    # All have the same grade=2, so tiebreaker (id desc) must hold
    tie_a_id = seeded["eval_b_same_grade_a_id"]
    tie_b_id = seeded["eval_b_same_grade_b_id"]
    higher_id = tie_a_id if tie_a_id > tie_b_id else tie_b_id
    lower_id = tie_b_id if tie_a_id > tie_b_id else tie_a_id
    assert row_ids.index(higher_id) < row_ids.index(lower_id)


def test_sort_by_created_at_asc_then_id_desc_tiebreak_is_deterministic(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    school_b_id = seeded["school_b_id"]

    stmt = evaluation_query_with_joins(school_b_id).order_by(None)
    stmt = apply_evaluation_sorting(stmt, sort_by="created_at", sort_dir="asc")
    rows = db_session.scalars(stmt).all()

    row_ids = [row.id for row in rows]
    rows_by_id = {row.id: row for row in rows}

    tie_a_id = seeded["eval_b_tie_created_a_id"]
    tie_b_id = seeded["eval_b_tie_created_b_id"]
    assert rows_by_id[tie_a_id].created_at == rows_by_id[tie_b_id].created_at

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
        apply_evaluation_sorting(stmt, sort_by="final_grade", sort_dir="sideways")
    assert invalid_sort_dir.value.status_code == 400
    assert invalid_sort_dir.value.detail == "Invalid sort_dir"


def test_apply_evaluation_filters_supports_needs_reevaluation(db_session: Session):
    seeded = seed_two_school_evals(db_session)
    stmt = evaluation_query_with_joins(seeded["school_b_id"])
    stmt = apply_evaluation_filters(stmt, needs_reevaluation=True)

    rows = db_session.scalars(stmt).all()
    assert len(rows) == 1
    assert rows[0].id == seeded["eval_b_id"]
