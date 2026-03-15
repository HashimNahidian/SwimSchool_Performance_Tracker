export type UserRole = "MANAGER" | "SUPERVISOR" | "INSTRUCTOR";

export type User = {
  id: number;
  school_id: number;
  full_name: string;
  email: string;
  phone?: string | null;
  role: UserRole;
  is_active: boolean;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type Level = {
  id: number;
  name: string;
  sort_order: number;
  is_active: boolean;
};

export type Skill = {
  id: number;
  level_id: number;
  name: string;
  sort_order: number;
  is_active: boolean;
};

export type Attribute = {
  id: number;
  school_id: number;
  name: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
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
  final_grade: number | null;
  needs_reevaluation: boolean;
  created_at: string;
  updated_at: string;
};

export type RatingOut = {
  attribute_id: number;
  attribute_name: string;
  rating: number;
  comment: string | null;
};

export type EvaluationDetail = EvaluationSummary & {
  notes: string | null;
  ratings: RatingOut[];
};

export type ReevaluationStatus = "OPEN" | "COMPLETED" | "CANCELED";

export type ReevaluationRequest = {
  id: number;
  school_id: number;
  instructor_id: number;
  instructor_name: string;
  supervisor_id: number | null;
  supervisor_name: string | null;
  skill_id: number;
  skill_name: string;
  source_evaluation_id: number | null;
  needs_reevaluation: boolean;
  status: ReevaluationStatus;
  requested_at: string;
  completed_at: string | null;
  notes: string | null;
};
