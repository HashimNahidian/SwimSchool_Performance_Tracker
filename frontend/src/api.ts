import type {
  EvaluationSummary,
  Level,
  Skill,
  TemplateResolved,
  TokenResponse,
  User
} from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(
  path: string,
  method: string,
  body?: unknown,
  token?: string
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const payload = await response.json();
      message = payload.detail ?? message;
    } catch {
      // no-op
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return request("/auth/login", "POST", { email, password });
}

export function refresh(refreshToken: string): Promise<TokenResponse> {
  return request("/auth/refresh", "POST", { refresh_token: refreshToken });
}

export function logout(refreshToken: string): Promise<void> {
  return request("/auth/logout", "POST", { refresh_token: refreshToken });
}

export function me(token: string): Promise<User> {
  return request("/auth/me", "GET", undefined, token);
}

export function listUsers(token: string): Promise<User[]> {
  return request("/manager/users", "GET", undefined, token);
}

export function createUser(
  token: string,
  payload: {
    name: string;
    email: string;
    password: string;
    role: "MANAGER" | "SUPERVISOR" | "INSTRUCTOR";
    active: boolean;
  }
): Promise<User> {
  return request("/manager/users", "POST", payload, token);
}

export function listLevels(token: string): Promise<Level[]> {
  return request("/manager/levels", "GET", undefined, token);
}

export function createLevel(
  token: string,
  payload: { name: string; active: boolean }
): Promise<Level> {
  return request("/manager/levels", "POST", payload, token);
}

export function listSkills(token: string): Promise<Skill[]> {
  return request("/manager/skills", "GET", undefined, token);
}

export function createSkill(
  token: string,
  payload: { level_id: number; name: string; active: boolean }
): Promise<Skill> {
  return request("/manager/skills", "POST", payload, token);
}

export function listManagerEvaluations(token: string): Promise<EvaluationSummary[]> {
  return request("/manager/evaluations", "GET", undefined, token);
}

export type ManagerEvaluationQuery = {
  instructor_id?: number | string;
  supervisor_id?: number | string;
  level_id?: number | string;
  skill_id?: number | string;
  rating_value?: number | string;
  status?: "DRAFT" | "SUBMITTED" | string;
  date_from?: string;
  date_to?: string;
  sort_by?:
    | "id"
    | "session_date"
    | "submitted_at"
    | "instructor_id"
    | "supervisor_id"
    | "level_id"
    | "skill_id"
    | string;
  sort_dir?: "asc" | "desc" | string;
  limit?: number | string;
  offset?: number | string;
};

export function listManagerEvaluationsWithQuery(
  token: string,
  query: ManagerEvaluationQuery
): Promise<EvaluationSummary[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/manager/evaluations${suffix}`, "GET", undefined, token);
}

export function listSupervisorEvaluations(token: string): Promise<EvaluationSummary[]> {
  return request("/supervisor/evaluations", "GET", undefined, token);
}

export function listInstructorEvaluations(token: string): Promise<EvaluationSummary[]> {
  return request("/instructor/evaluations", "GET", undefined, token);
}

export function createSupervisorEvaluation(
  token: string,
  payload: {
    instructor_id: number;
    level_id: number;
    skill_id: number;
    session_label: string;
    session_date: string;
    notes?: string;
    ratings: Array<{ attribute_id: number; rating_value: number }>;
  }
): Promise<unknown> {
  return request("/supervisor/evaluations", "POST", payload, token);
}

export function resolveSupervisorTemplate(
  token: string,
  levelId: number,
  skillId: number
): Promise<TemplateResolved> {
  return request(
    `/supervisor/templates/resolve?level_id=${levelId}&skill_id=${skillId}`,
    "GET",
    undefined,
    token
  );
}

export function exportEvaluationsCsvUrl(): string {
  return `${API_BASE_URL}/manager/exports/evaluations.csv`;
}
