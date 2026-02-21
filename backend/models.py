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
<<<<<<< HEAD
    MANAGER = "MANAGER"
    SUPERVISOR = "SUPERVISOR"
    INSTRUCTOR = "INSTRUCTOR"


class EvaluationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
=======
    manager = "MANAGER"
    supervisor = "SUPERVISOR"
    instructor = "INSTRUCTOR"


class EvaluationStatus(str, enum.Enum):
    draft = "DRAFT"
    submitted = "SUBMITTED"
>>>>>>> origin/main


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Level(Base):
    __tablename__ = "levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("level_id", "name", name="uq_skills_level_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
<<<<<<< HEAD
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
=======
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
>>>>>>> origin/main

    level: Mapped["Level"] = relationship()


class Attribute(Base):
    __tablename__ = "attributes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
<<<<<<< HEAD
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
=======
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
>>>>>>> origin/main


class Template(Base):
    __tablename__ = "templates"
<<<<<<< HEAD

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    level_id: Mapped[int | None] = mapped_column(ForeignKey("levels.id"))
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    level: Mapped["Level | None"] = relationship()
    skill: Mapped["Skill | None"] = relationship()
    template_attributes: Mapped[list["TemplateAttribute"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
=======
    __table_args__ = (
        UniqueConstraint("name", "level_id", "skill_id", name="uq_templates_name_scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    level_id: Mapped[int | None] = mapped_column(ForeignKey("levels.id", ondelete="SET NULL"), nullable=True, index=True)
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    template_attributes: Mapped[list["TemplateAttribute"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateAttribute.sort_order",
>>>>>>> origin/main
    )


class TemplateAttribute(Base):
    __tablename__ = "template_attributes"
<<<<<<< HEAD
    __table_args__ = (
        UniqueConstraint("template_id", "attribute_id", name="uq_template_attribute"),
        UniqueConstraint("template_id", "sort_order", name="uq_template_sort"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False, index=True)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("attributes.id"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
=======
    __table_args__ = (UniqueConstraint("template_id", "attribute_id", name="uq_template_attribute"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("attributes.id", ondelete="RESTRICT"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
>>>>>>> origin/main

    template: Mapped["Template"] = relationship(back_populates="template_attributes")
    attribute: Mapped["Attribute"] = relationship()


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
<<<<<<< HEAD
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
=======
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    supervisor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    level_id: Mapped[int | None] = mapped_column(ForeignKey("levels.id", ondelete="SET NULL"), nullable=True, index=True)
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"), nullable=True, index=True)
    session_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus, name="evaluation_status"),
        nullable=False,
        default=EvaluationStatus.draft,
        server_default=EvaluationStatus.draft.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ratings: Mapped[list["EvaluationRating"]] = relationship(back_populates="evaluation", cascade="all, delete-orphan")
>>>>>>> origin/main


class EvaluationRating(Base):
    __tablename__ = "evaluation_ratings"
    __table_args__ = (
<<<<<<< HEAD
        UniqueConstraint("evaluation_id", "attribute_id", name="uq_evaluation_attribute"),
        CheckConstraint("rating_value BETWEEN 1 AND 3", name="ck_rating_value_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id"), nullable=False, index=True)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("attributes.id"), nullable=False, index=True)
=======
        UniqueConstraint("evaluation_id", "attribute_id", name="uq_eval_rating"),
        CheckConstraint("rating_value IN (1, 2, 3)", name="ck_rating_value_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("attributes.id", ondelete="RESTRICT"), nullable=False, index=True)
>>>>>>> origin/main
    rating_value: Mapped[int] = mapped_column(Integer, nullable=False)

    evaluation: Mapped["Evaluation"] = relationship(back_populates="ratings")
    attribute: Mapped["Attribute"] = relationship()


<<<<<<< HEAD
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
=======
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(160), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
>>>>>>> origin/main
