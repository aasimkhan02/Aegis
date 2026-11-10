import {
  Project,
  ProjectCreatePayload,
  AssistantVersion,
  AssistantVersionCreatePayload,
  EvaluationRun,
  EvaluationCreatePayload,
  CaseResult,
  DashboardStats,
  SecuritySummary,
} from '../types/dashboard';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) {
        errorDetail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // fallback to status text
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

// ---------------- Dashboard & Stats ----------------

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const res = await fetch(`${BASE_URL}/api/dashboard/stats`);
  return handleResponse<DashboardStats>(res);
}

export async function fetchSecuritySummary(): Promise<SecuritySummary> {
  const res = await fetch(`${BASE_URL}/api/dashboard/security`);
  return handleResponse<SecuritySummary>(res);
}

// ---------------- Projects ----------------

export async function fetchProjects(limit = 100, offset = 0): Promise<{ items: Project[]; total: number }> {
  const url = new URL(`${BASE_URL}/api/projects`);
  url.searchParams.set('limit', limit.toString());
  url.searchParams.set('offset', offset.toString());
  const res = await fetch(url.toString());
  return handleResponse<{ items: Project[]; total: number }>(res);
}

export async function createProject(payload: ProjectCreatePayload): Promise<Project> {
  const res = await fetch(`${BASE_URL}/api/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<Project>(res);
}

export async function updateProject(id: string, payload: Partial<ProjectCreatePayload>): Promise<Project> {
  const res = await fetch(`${BASE_URL}/api/projects/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<Project>(res);
}

// ---------------- Assistants ----------------

export async function fetchAssistants(projectId?: string, limit = 100, offset = 0): Promise<{ items: AssistantVersion[]; total: number }> {
  const url = new URL(`${BASE_URL}/api/assistants`);
  if (projectId) url.searchParams.set('project_id', projectId);
  url.searchParams.set('limit', limit.toString());
  url.searchParams.set('offset', offset.toString());
  const res = await fetch(url.toString());
  return handleResponse<{ items: AssistantVersion[]; total: number }>(res);
}

export async function createAssistant(payload: AssistantVersionCreatePayload): Promise<AssistantVersion> {
  const res = await fetch(`${BASE_URL}/api/assistants`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<AssistantVersion>(res);
}

// ---------------- Evaluations ----------------

export async function fetchEvaluationRuns(params?: {
  projectId?: string;
  datasetId?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ items: EvaluationRun[]; total: number }> {
  const url = new URL(`${BASE_URL}/api/evaluations`);
  if (params?.projectId) url.searchParams.set('project_id', params.projectId);
  if (params?.datasetId) url.searchParams.set('dataset_id', params.datasetId);
  if (params?.status) url.searchParams.set('status', params.status);
  url.searchParams.set('limit', (params?.limit ?? 50).toString());
  url.searchParams.set('offset', (params?.offset ?? 0).toString());
  const res = await fetch(url.toString());
  return handleResponse<{ items: EvaluationRun[]; total: number }>(res);
}

export async function fetchEvaluationRun(runId: string): Promise<EvaluationRun> {
  const res = await fetch(`${BASE_URL}/api/evaluations/${runId}`);
  return handleResponse<EvaluationRun>(res);
}

export async function startEvaluationRun(payload: EvaluationCreatePayload): Promise<EvaluationRun> {
  const res = await fetch(`${BASE_URL}/api/evaluations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<EvaluationRun>(res);
}

export async function fetchCaseResults(
  runId: string,
  status?: string,
  limit = 100,
  offset = 0
): Promise<{ items: CaseResult[]; total: number }> {
  const url = new URL(`${BASE_URL}/api/evaluations/${runId}/results`);
  if (status) url.searchParams.set('status', status);
  url.searchParams.set('limit', limit.toString());
  url.searchParams.set('offset', offset.toString());
  const res = await fetch(url.toString());
  return handleResponse<{ items: CaseResult[]; total: number }>(res);
}

