from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from models import EvaluationStatus, UserRole


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8)


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8)
    role: UserRole
    active: bool = True


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    name: str
    email: str
    role: UserRole
    active: bool


class LevelBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    active: bool = True


class LevelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    active: bool | None = None


class LevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    active: bool


class SkillBase(BaseModel):
    level_id: int
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    active: bool = True


class SkillUpdate(BaseModel):
    level_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    active: bool | None = None


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level_id: int
    name: str
    description: str | None
    active: bool


class AttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    active: bool


class TemplateAttributeIn(BaseModel):
    attribute_id: int
    sort_order: int = Field(ge=1)


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    level_id: int | None = None
    skill_id: int | None = None
    active: bool = True
    attributes: list[TemplateAttributeIn]


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    level_id: int | None = None
    skill_id: int | None = None
    active: bool | None = None
    attributes: list[TemplateAttributeIn] | None = None


class TemplateAttributeOut(BaseModel):
    attribute_id: int
    attribute_name: str
    sort_order: int


class TemplateOut(BaseModel):
    id: int
    name: str
    level_id: int | None
    skill_id: int | None
    active: bool
    attributes: list[TemplateAttributeOut]


class RatingIn(BaseModel):
    attribute_id: int
    rating_value: int = Field(ge=1, le=3)


class EvaluationCreate(BaseModel):
    instructor_id: int
    level_id: int
    skill_id: int
    session_label: str = Field(min_length=1, max_length=150)
    session_date: date
    notes: str | None = None
    template_id: int | None = None
    ratings: list[RatingIn] = Field(default_factory=list)


class EvaluationUpdate(BaseModel):
    notes: str | None = None
    ratings: list[RatingIn] | None = None


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
    session_label: str
    session_date: date
    status: EvaluationStatus
    submitted_at: datetime | None


class RatingOut(BaseModel):
    attribute_id: int
    attribute_name: str
    rating_value: int


class EvaluationDetailOut(EvaluationSummaryOut):
    notes: str | None
    ratings: list[RatingOut]


class EvaluationFilterIn(BaseModel):
    instructor_id: int | None = None
    supervisor_id: int | None = None
    level_id: int | None = None
    skill_id: int | None = None
    rating_value: int | None = Field(default=None, ge=1, le=3)
    status: EvaluationStatus | None = None
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
