from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from models import ReevaluationStatus, ScheduledEvaluationStatus, UserRole


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    password: str = Field(min_length=8)

    @model_validator(mode="after")
    def ensure_identifier(self) -> "LoginRequest":
        if not (self.username or self.email):
            raise ValueError("username is required")
        return self


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=50)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=25)
    password: str = Field(min_length=8)
    role: UserRole
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    username: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=25)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    full_name: str
    username: str
    email: str | None
    phone: str | None
    role: UserRole
    is_active: bool


# ── Levels ───────────────────────────────────────────────────────────────────

class LevelBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = 0


class LevelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    sort_order: int | None = None


class LevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sort_order: int
    is_active: bool


# ── Skills ───────────────────────────────────────────────────────────────────

class SkillBase(BaseModel):
    level_id: int
    name: str = Field(min_length=1, max_length=255)
    sort_order: int = 0


class SkillUpdate(BaseModel):
    level_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sort_order: int | None = None


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level_id: int
    name: str
    sort_order: int
    is_active: bool


# ── Attributes ───────────────────────────────────────────────────────────────

class AttributeBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    sort_order: int = 0


class AttributeCreate(AttributeBase):
    pass


class AttributeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    sort_order: int | None = None


class AttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    name: str
    description: str | None
    sort_order: int
    is_active: bool


# ── Skill ↔ Attribute links ───────────────────────────────────────────────────

class SkillAttributeIn(BaseModel):
    attribute_id: int


# ── Evaluations ───────────────────────────────────────────────────────────────

class RatingIn(BaseModel):
    attribute_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class EvaluationCreate(BaseModel):
    instructor_id: int
    skill_id: int
    source_evaluation_id: int | None = None
    scheduled_evaluation_id: int | None = None
    notes: str | None = None
    duration_seconds: int | None = None
    ratings: list[RatingIn] = Field(default_factory=list)
    needs_reevaluation: bool = False


class EvaluationUpdate(BaseModel):
    notes: str | None = None
    scheduled_evaluation_id: int | None = None
    duration_seconds: int | None = None
    ratings: list[RatingIn] | None = None
    needs_reevaluation: bool | None = None


class EvaluationSummaryOut(BaseModel):
    id: int
    instructor_id: int
    instructor_name: str
    supervisor_id: int
    supervisor_name: str
    level_id: int
    level_name: str
    skill_id: int
    skill_name: str
    scheduled_evaluation_id: int | None = None
    duration_seconds: int | None
    final_grade: int | None
    needs_reevaluation: bool
    instructor_acknowledged_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RatingOut(BaseModel):
    attribute_id: int
    attribute_name: str
    rating: int
    comment: str | None


class EvaluationDetailOut(EvaluationSummaryOut):
    notes: str | None
    ratings: list[RatingOut]


class ReevaluationRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    instructor_id: int
    instructor_name: str
    supervisor_id: int | None
    supervisor_name: str | None
    skill_id: int
    skill_name: str
    source_evaluation_id: int | None
    needs_reevaluation: bool
    status: ReevaluationStatus
    requested_at: datetime
    completed_at: datetime | None
    notes: str | None


class EvaluationFilterIn(BaseModel):
    instructor_id: int | None = None
    supervisor_id: int | None = None
    skill_id: int | None = None
    final_grade: int | None = Field(default=None, ge=1, le=5)
    needs_reevaluation: bool | None = None
    date_from: date | None = None
    date_to: date | None = None
    sort_by: str | None = None
    sort_dir: str | None = None
    limit: int | None = Field(default=None, ge=1, le=200)
    offset: int | None = Field(default=None, ge=0)


class ExportEmailRequest(BaseModel):
    to: list[EmailStr] = Field(min_length=1)
    subject: str | None = Field(default=None, max_length=200)
    message: str | None = Field(default=None, max_length=4000)
    filters: EvaluationFilterIn | None = None


class ScheduledEvaluationBase(BaseModel):
    instructor_id: int
    skill_id: int
    target_date: date
    assigned_to_id: int | None = None
    status: ScheduledEvaluationStatus = ScheduledEvaluationStatus.PENDING
    notes: str | None = None


class ScheduledEvaluationCreate(ScheduledEvaluationBase):
    pass


class ScheduledEvaluationUpdate(BaseModel):
    instructor_id: int | None = None
    skill_id: int | None = None
    target_date: date | None = None
    assigned_to_id: int | None = None
    status: ScheduledEvaluationStatus | None = None
    notes: str | None = None


class ScheduledEvaluationOut(BaseModel):
    id: int
    school_id: int
    instructor_id: int
    instructor_name: str
    skill_id: int
    skill_name: str
    level_id: int
    level_name: str
    target_date: date
    requested_by_id: int
    requested_by_name: str
    assigned_to_id: int | None
    assigned_to_name: str | None
    status: ScheduledEvaluationStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
