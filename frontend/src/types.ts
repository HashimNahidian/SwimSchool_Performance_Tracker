export type UserRole = "MANAGER" | "SUPERVISOR" | "INSTRUCTOR";
<<<<<<< HEAD

export type User = {
=======
export type EvaluationStatus = "DRAFT" | "SUBMITTED";

export interface User {
>>>>>>> origin/main
  id: number;
  name: string;
  email: string;
  role: UserRole;
  active: boolean;
<<<<<<< HEAD
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
=======
}

export interface Level {
  id: number;
  name: string;
  active: boolean;
}

export interface Skill {
>>>>>>> origin/main
  id: number;
  level_id: number;
  name: string;
  active: boolean;
<<<<<<< HEAD
};

export type Attribute = {
=======
}

export interface Attribute {
>>>>>>> origin/main
  id: number;
  name: string;
  description: string | null;
  active: boolean;
<<<<<<< HEAD
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
=======
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
>>>>>>> origin/main
