import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class UserRole(str, enum.Enum):
    MANAGER = "MANAGER"
    SUPERVISOR = "SUPERVISOR"
    INSTRUCTOR = "INSTRUCTOR"


class EvaluationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Level(Base):
    __tablename__ = "levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("level_id", "name", name="uq_skills_level_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    level: Mapped["Level"] = relationship()


class Attribute(Base):
    __tablename__ = "attributes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    level_id: Mapped[int | None] = mapped_column(ForeignKey("levels.id"))
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    level: Mapped["Level | None"] = relationship()
    skill: Mapped["Skill | None"] = relationship()
    template_attributes: Mapped[list["TemplateAttribute"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class TemplateAttribute(Base):
    __tablename__ = "template_attributes"
    __table_args__ = (
        UniqueConstraint("template_id", "attribute_id", name="uq_template_attribute"),
        UniqueConstraint("template_id", "sort_order", name="uq_template_sort"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False, index=True)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("attributes.id"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    template: Mapped["Template"] = relationship(back_populates="template_attributes")
    attribute: Mapped["Attribute"] = relationship()


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    supervisor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"), nullable=False, index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("templates.id"), index=True)
    session_label: Mapped[str] = mapped_column(String(150), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus, name="evaluation_status"),
        default=EvaluationStatus.DRAFT,
        nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    instructor: Mapped["User"] = relationship(foreign_keys=[instructor_id])
    supervisor: Mapped["User"] = relationship(foreign_keys=[supervisor_id])
    level: Mapped["Level"] = relationship()
    skill: Mapped["Skill"] = relationship()
    ratings: Mapped[list["EvaluationRating"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )


class EvaluationRating(Base):
    __tablename__ = "evaluation_ratings"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "attribute_id", name="uq_evaluation_attribute"),
        CheckConstraint("rating_value BETWEEN 1 AND 3", name="ck_rating_value_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id"), nullable=False, index=True)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("attributes.id"), nullable=False, index=True)
    rating_value: Mapped[int] = mapped_column(Integer, nullable=False)

    evaluation: Mapped["Evaluation"] = relationship(back_populates="ratings")
    attribute: Mapped["Attribute"] = relationship()


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    client_ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User | None"] = relationship()
