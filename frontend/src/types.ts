export type UserRole = "MANAGER" | "SUPERVISOR" | "INSTRUCTOR";
export type EvaluationStatus = "DRAFT" | "SUBMITTED";

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  active: boolean;
}

export interface Level {
  id: number;
  name: string;
  active: boolean;
}

export interface Skill {
  id: number;
  level_id: number;
  name: string;
  active: boolean;
}

export interface Attribute {
  id: number;
  name: string;
  description: string | null;
  active: boolean;
}

export interface TemplateAttribute {
  attribute_id: number;
  sort_order: number;
}

export interface Template {
  id: number;
  name: string;
  level_id: number | null;
  skill_id: number | null;
  active: boolean;
  template_attributes: TemplateAttribute[];
}

export interface EvaluationRating {
  attribute_id: number;
  rating_value: number;
}

export interface Evaluation {
  id: number;
  instructor_id: number;
  supervisor_id: number;
  level_id: number | null;
  skill_id: number | null;
  session_label: string | null;
  session_date: string;
  notes: string | null;
  status: EvaluationStatus;
  created_at: string;
  submitted_at: string | null;
  ratings: EvaluationRating[];
}

export interface TrendPoint {
  period: string;
  evaluation_count: number;
  average_rating: number;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}
