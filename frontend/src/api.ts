import type {
  Attribute,
  EvaluationDetail,
  EvaluationSummary,
  Level,
  ReevaluationRequest,
  ScheduledEvaluation,
  Skill,
  TokenResponse,
  User
} from "./types";

export const TOKEN_KEY = "propel_token";
export const REFRESH_KEY = "propel_refresh";
export const USER_KEY = "propel_user";
export const AUTH_STATE_EVENT = "propel-auth-state";

const API_BASE_URL = (
  import.meta.env.DEV ? "" : import.meta.env.VITE_API_BASE_URL ?? ""
).replace(/\/$/, "");

type AuthStateDetail =
  | { type: "refreshed"; accessToken: string; refreshToken: string }
  | { type: "cleared" };

function emitAuthState(detail: AuthStateDetail) {
  window.dispatchEvent(new CustomEvent<AuthStateDetail>(AUTH_STATE_EVENT, { detail }));
}

function clearStoredSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
  emitAuthState({ type: "cleared" });
}

async function fetchWithAuth(
  path: string,
  method: string,
  body?: unknown,
  token?: string
): Promise<Response> {
  return fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  });
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) {
    clearStoredSession();
    return null;
  }

  let response: Response;
  try {
    response = await fetchWithAuth("/auth/refresh", "POST", { refresh_token: refreshToken });
  } catch {
    clearStoredSession();
    return null;
  }

  if (!response.ok) {
    clearStoredSession();
    return null;
  }

  const payload = (await response.json()) as TokenResponse;
  localStorage.setItem(TOKEN_KEY, payload.access_token);
  localStorage.setItem(REFRESH_KEY, payload.refresh_token);
  emitAuthState({
    type: "refreshed",
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token
  });
  return payload.access_token;
}

async function request<T>(
  path: string,
  method: string,
  body?: unknown,
  token?: string
): Promise<T> {
  let response: Response;
  try {
    response = await fetchWithAuth(path, method, body, token);
  } catch {
    throw new Error(
      "Unable to reach the server. Check that the API is running and that the frontend API URL is configured correctly."
    );
  }

  if (response.status === 401 && token && !path.startsWith("/auth/")) {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) {
      response = await fetchWithAuth(path, method, body, refreshedToken);
    }
  }

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

// username-first identity activation
export function login(username: string, password: string): Promise<TokenResponse> {
  return request("/auth/login", "POST", { username, password });
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
    full_name: string;
    username: string;
    email?: string | null;
    phone?: string | null;
    password: string;
    role: "MANAGER" | "SUPERVISOR" | "INSTRUCTOR";
    is_active: boolean;
  }
): Promise<User> {
  return request("/manager/users", "POST", payload, token);
}

export function updateUser(
  token: string,
  userId: number,
  payload: {
    full_name?: string;
    username?: string;
    email?: string | null;
    phone?: string | null;
    role?: "MANAGER" | "SUPERVISOR" | "INSTRUCTOR";
    is_active?: boolean;
    password?: string;
  }
): Promise<User> {
  return request(`/manager/users/${userId}`, "PUT", payload, token);
}

export function deleteUser(token: string, userId: number): Promise<void> {
  return request(`/manager/users/${userId}`, "DELETE", undefined, token);
}

export function listLevels(token: string): Promise<Level[]> {
  return request("/manager/levels", "GET", undefined, token);
}

export function createLevel(
  token: string,
  payload: { name: string; sort_order?: number }
): Promise<Level> {
  return request("/manager/levels", "POST", payload, token);
}

export function updateLevel(
  token: string,
  levelId: number,
  payload: { name?: string; sort_order?: number }
): Promise<Level> {
  return request(`/manager/levels/${levelId}`, "PUT", payload, token);
}

export function deleteLevel(token: string, levelId: number): Promise<void> {
  return request(`/manager/levels/${levelId}`, "DELETE", undefined, token);
}

export function listSkills(token: string): Promise<Skill[]> {
  return request("/manager/skills", "GET", undefined, token);
}

export function createSkill(
  token: string,
  payload: { level_id: number; name: string; sort_order?: number }
): Promise<Skill> {
  return request("/manager/skills", "POST", payload, token);
}

export function updateSkill(
  token: string,
  skillId: number,
  payload: { level_id?: number; name?: string; sort_order?: number }
): Promise<Skill> {
  return request(`/manager/skills/${skillId}`, "PUT", payload, token);
}

export function deleteSkill(token: string, skillId: number): Promise<void> {
  return request(`/manager/skills/${skillId}`, "DELETE", undefined, token);
}

export function listAttributes(token: string): Promise<Attribute[]> {
  return request("/manager/attributes", "GET", undefined, token);
}

export function createAttribute(
  token: string,
  payload: { name: string; description?: string | null; sort_order?: number }
): Promise<Attribute> {
  return request("/manager/attributes", "POST", payload, token);
}

export function updateAttribute(
  token: string,
  attributeId: number,
  payload: { name?: string; description?: string | null; sort_order?: number }
): Promise<Attribute> {
  return request(`/manager/attributes/${attributeId}`, "PUT", payload, token);
}

export function deleteAttribute(token: string, attributeId: number): Promise<void> {
  return request(`/manager/attributes/${attributeId}`, "DELETE", undefined, token);
}

export function linkSkillAttribute(token: string, skillId: number, attributeId: number): Promise<void> {
  return request(`/manager/skills/${skillId}/attributes`, "POST", { attribute_id: attributeId }, token);
}

export function listManagerSkillAttributes(token: string, skillId: number): Promise<Attribute[]> {
  return request(`/manager/skills/${skillId}/attributes`, "GET", undefined, token);
}

export function unlinkSkillAttribute(token: string, skillId: number, attributeId: number): Promise<void> {
  return request(`/manager/skills/${skillId}/attributes/${attributeId}`, "DELETE", undefined, token);
}

export function listManagerEvaluations(token: string): Promise<EvaluationSummary[]> {
  return request("/manager/evaluations", "GET", undefined, token);
}

export type ManagerEvaluationQuery = {
  instructor_id?: number;
  supervisor_id?: number;
  skill_id?: number;
  final_grade?: number;
  needs_reevaluation?: boolean;
  date_from?: string;
  date_to?: string;
  sort_by?: "id" | "created_at" | "updated_at" | "instructor_id" | "supervisor_id" | "skill_id" | "final_grade";
  sort_dir?: "asc" | "desc";
  limit?: number;
  offset?: number;
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

export function listSupervisorLevels(token: string): Promise<Level[]> {
  return request("/supervisor/levels", "GET", undefined, token);
}

export function listSupervisorSkills(token: string): Promise<Skill[]> {
  return request("/supervisor/skills", "GET", undefined, token);
}

export function listSupervisorInstructors(token: string): Promise<User[]> {
  return request("/supervisor/instructors", "GET", undefined, token);
}

export function listSupervisorSkillAttributes(token: string, skillId: number): Promise<Attribute[]> {
  return request(`/supervisor/skills/${skillId}/attributes`, "GET", undefined, token);
}

export type SupervisorEvaluationQuery = {
  instructor_id?: number;
  skill_id?: number;
  needs_reevaluation?: boolean;
};

export function listSupervisorEvaluations(
  token: string,
  query?: SupervisorEvaluationQuery
): Promise<EvaluationSummary[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null) {
      params.set(key, String(value));
    }
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/supervisor/evaluations${suffix}`, "GET", undefined, token);
}

export function listInstructorEvaluations(token: string): Promise<EvaluationSummary[]> {
  return request("/instructor/evaluations", "GET", undefined, token);
}

export function createSupervisorEvaluation(
  token: string,
  payload: {
    instructor_id: number;
    skill_id: number;
    source_evaluation_id?: number | null;
    scheduled_evaluation_id?: number | null;
    notes?: string;
    duration_seconds?: number | null;
    ratings: Array<{ attribute_id: number; rating: number; comment?: string | null }>;
    needs_reevaluation?: boolean;
  }
): Promise<EvaluationDetail> {
  return request("/supervisor/evaluations", "POST", payload, token);
}

export function exportEvaluationsCsvUrl(): string {
  return `${API_BASE_URL}/manager/exports/evaluations.csv`;
}

export function emailEvaluationsCsv(
  token: string,
  payload: {
    to: string[];
    subject?: string;
    message?: string;
    filters?: ManagerEvaluationQuery;
  }
): Promise<{ detail: string }> {
  return request("/manager/exports/evaluations/email", "POST", payload, token);
}

export function getInstructorEvaluationDetail(token: string, id: number): Promise<EvaluationDetail> {
  return request(`/instructor/evaluations/${id}`, "GET", undefined, token);
}

export function acknowledgeInstructorEvaluation(token: string, id: number): Promise<EvaluationDetail> {
  return request(`/instructor/evaluations/${id}/acknowledge`, "POST", undefined, token);
}

export function getSupervisorEvaluationDetail(token: string, id: number): Promise<EvaluationDetail> {
  return request(`/supervisor/evaluations/${id}`, "GET", undefined, token);
}

export function updateSupervisorEvaluation(
  token: string,
  id: number,
  payload: {
    notes?: string | null;
    duration_seconds?: number | null;
    ratings?: Array<{ attribute_id: number; rating: number; comment?: string | null }>;
    needs_reevaluation?: boolean;
  }
): Promise<EvaluationDetail> {
  return request(`/supervisor/evaluations/${id}`, "PUT", payload, token);
}

export function deleteSupervisorEvaluation(token: string, id: number): Promise<void> {
  return request(`/supervisor/evaluations/${id}`, "DELETE", undefined, token);
}

export function getManagerEvaluationDetail(token: string, id: number): Promise<EvaluationDetail> {
  return request(`/manager/evaluations/${id}`, "GET", undefined, token);
}

export function updateManagerEvaluation(
  token: string,
  id: number,
  payload: {
    notes?: string | null;
    duration_seconds?: number | null;
    ratings?: Array<{ attribute_id: number; rating: number; comment?: string | null }>;
    needs_reevaluation?: boolean;
  }
): Promise<EvaluationDetail> {
  return request(`/manager/evaluations/${id}`, "PUT", payload, token);
}

export function deleteManagerEvaluation(token: string, id: number): Promise<void> {
  return request(`/manager/evaluations/${id}`, "DELETE", undefined, token);
}

export function listManagerReevaluationRequests(
  token: string,
  query?: {
    instructor_id?: number;
    skill_id?: number;
    status?: "OPEN" | "COMPLETED" | "CANCELED";
  }
): Promise<ReevaluationRequest[]> {
  const params = new URLSearchParams();
  if (query?.instructor_id !== undefined) params.set("instructor_id", String(query.instructor_id));
  if (query?.skill_id !== undefined) params.set("skill_id", String(query.skill_id));
  if (query?.status !== undefined) params.set("status", query.status);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/manager/reevaluations${suffix}`, "GET", undefined, token);
}

export function listSupervisorReevaluations(
  token: string,
  query?: { instructor_id?: number; skill_id?: number }
): Promise<ReevaluationRequest[]> {
  const params = new URLSearchParams();
  if (query?.instructor_id !== undefined) params.set("instructor_id", String(query.instructor_id));
  if (query?.skill_id !== undefined) params.set("skill_id", String(query.skill_id));
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/supervisor/reevaluations${suffix}`, "GET", undefined, token);
}

export function completeSupervisorReevaluation(
  token: string,
  id: number
): Promise<ReevaluationRequest> {
  return request(`/supervisor/reevaluations/${id}/complete`, "PUT", undefined, token);
}

export function listSupervisorScheduledEvaluations(
  token: string,
  query?: { instructor_id?: number; skill_id?: number; status?: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELED" }
): Promise<ScheduledEvaluation[]> {
  const params = new URLSearchParams();
  if (query?.instructor_id !== undefined) params.set("instructor_id", String(query.instructor_id));
  if (query?.skill_id !== undefined) params.set("skill_id", String(query.skill_id));
  if (query?.status !== undefined) params.set("status", query.status);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/supervisor/scheduled-evaluations${suffix}`, "GET", undefined, token);
}

export function createSupervisorScheduledEvaluation(
  token: string,
  payload: {
    instructor_id: number;
    skill_id: number;
    target_date: string;
    assigned_to_id?: number | null;
    status?: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELED";
    notes?: string | null;
  }
): Promise<ScheduledEvaluation> {
  return request("/supervisor/scheduled-evaluations", "POST", payload, token);
}

export function updateSupervisorScheduledEvaluation(
  token: string,
  id: number,
  payload: {
    instructor_id?: number;
    skill_id?: number;
    target_date?: string;
    assigned_to_id?: number | null;
    status?: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELED";
    notes?: string | null;
  }
): Promise<ScheduledEvaluation> {
  return request(`/supervisor/scheduled-evaluations/${id}`, "PUT", payload, token);
}

export function deleteSupervisorScheduledEvaluation(token: string, id: number): Promise<void> {
  return request(`/supervisor/scheduled-evaluations/${id}`, "DELETE", undefined, token);
}

export function listManagerScheduledEvaluations(
  token: string,
  query?: { instructor_id?: number; skill_id?: number; assigned_to_id?: number; status?: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELED" }
): Promise<ScheduledEvaluation[]> {
  const params = new URLSearchParams();
  if (query?.instructor_id !== undefined) params.set("instructor_id", String(query.instructor_id));
  if (query?.skill_id !== undefined) params.set("skill_id", String(query.skill_id));
  if (query?.assigned_to_id !== undefined) params.set("assigned_to_id", String(query.assigned_to_id));
  if (query?.status !== undefined) params.set("status", query.status);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/manager/scheduled-evaluations${suffix}`, "GET", undefined, token);
}

export function createManagerScheduledEvaluation(
  token: string,
  payload: {
    instructor_id: number;
    skill_id: number;
    target_date: string;
    assigned_to_id?: number | null;
    status?: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELED";
    notes?: string | null;
  }
): Promise<ScheduledEvaluation> {
  return request("/manager/scheduled-evaluations", "POST", payload, token);
}

export function updateManagerScheduledEvaluation(
  token: string,
  id: number,
  payload: {
    instructor_id?: number;
    skill_id?: number;
    target_date?: string;
    assigned_to_id?: number | null;
    status?: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELED";
    notes?: string | null;
  }
): Promise<ScheduledEvaluation> {
  return request(`/manager/scheduled-evaluations/${id}`, "PUT", payload, token);
}

export function deleteManagerScheduledEvaluation(token: string, id: number): Promise<void> {
  return request(`/manager/scheduled-evaluations/${id}`, "DELETE", undefined, token);
}
