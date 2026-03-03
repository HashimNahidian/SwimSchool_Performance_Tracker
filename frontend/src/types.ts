export type UserRole = "MANAGER" | "SUPERVISOR" | "INSTRUCTOR";

export type User = {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  active: boolean;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type Level = {
  id: number;
  name: string;
  active: boolean;
};

export type Skill = {
  id: number;
  level_id: number;
  name: string;
  description: string | null;
  active: boolean;
};

export type Attribute = {
  id: number;
  name: string;
  description: string | null;
  active: boolean;
};

export type EvaluationSummary = {
  id: number;
  instructor_id: number;
  instructor_name: string;
  supervisor_id: number;
  supervisor_name: string;
  level_id: number;
  level_name: string;
  skill_id: number;
  skill_name: string;
  session_label: string;
  session_date: string;
  status: "DRAFT" | "SUBMITTED";
  submitted_at: string | null;
};

export type RatingOut = {
  attribute_id: number;
  attribute_name: string;
  rating_value: number;
};

export type EvaluationDetail = EvaluationSummary & {
  notes: string | null;
  ratings: RatingOut[];
};

export type TemplateCriterion = {
  attribute_id: number;
  attribute_name: string;
  sort_order: number;
};

export type TemplateResolved = {
  id: number;
  name: string;
  level_id: number | null;
  skill_id: number | null;
  active: boolean;
  attributes: TemplateCriterion[];
};

export type TemplateConfig = {
  id: number;
  name: string;
  level_id: number | null;
  skill_id: number | null;
  active: boolean;
  attributes: TemplateCriterion[];
};
