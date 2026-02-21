import type {
  Attribute,
  EvaluationSummary,
  Level,
  Skill,
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

export function listAttributes(token: string): Promise<Attribute[]> {
  return request("/manager/attributes", "GET", undefined, token);
}

export function createAttribute(
  token: string,
  payload: { name: string; description?: string; active: boolean }
): Promise<Attribute> {
  return request("/manager/attributes", "POST", payload, token);
}

export function listManagerEvaluations(token: string): Promise<EvaluationSummary[]> {
  return request("/manager/evaluations", "GET", undefined, token);
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

export function exportEvaluationsCsvUrl(): string {
  return `${API_BASE_URL}/manager/exports/evaluations.csv`;
}
