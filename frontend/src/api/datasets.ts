import {
  Dataset,
  DatasetCreatePayload,
  DatasetExport,
  ImportResult,
  TestCase,
  TestCaseCreatePayload,
} from '../types/dataset';

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

export async function fetchDatasets(search?: string): Promise<Dataset[]> {
  const url = new URL(`${BASE_URL}/api/datasets`);
  if (search) url.searchParams.set('search', search);
  const res = await fetch(url.toString());
  return handleResponse<Dataset[]>(res);
}

export async function fetchDataset(id: string): Promise<Dataset> {
  const res = await fetch(`${BASE_URL}/api/datasets/${id}`);
  return handleResponse<Dataset>(res);
}

export async function createDataset(payload: DatasetCreatePayload): Promise<Dataset> {
  const res = await fetch(`${BASE_URL}/api/datasets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<Dataset>(res);
}

export async function updateDataset(id: string, payload: Partial<DatasetCreatePayload>): Promise<Dataset> {
  const res = await fetch(`${BASE_URL}/api/datasets/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<Dataset>(res);
}

export async function deleteDataset(id: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`${BASE_URL}/api/datasets/${id}`, {
    method: 'DELETE',
  });
  return handleResponse<{ status: string; message: string }>(res);
}

export async function fetchTestCases(
  datasetId: string,
  params?: { tag?: string; is_enabled?: boolean; search?: string }
): Promise<TestCase[]> {
  const url = new URL(`${BASE_URL}/api/datasets/${datasetId}/test-cases`);
  if (params?.tag) url.searchParams.set('tag', params.tag);
  if (params?.is_enabled !== undefined) url.searchParams.set('is_enabled', String(params.is_enabled));
  if (params?.search) url.searchParams.set('search', params.search);

  const res = await fetch(url.toString());
  return handleResponse<TestCase[]>(res);
}

export async function createTestCase(
  datasetId: string,
  payload: TestCaseCreatePayload
): Promise<TestCase> {
  const res = await fetch(`${BASE_URL}/api/datasets/${datasetId}/test-cases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<TestCase>(res);
}

export async function updateTestCase(
  id: string,
  payload: Partial<TestCaseCreatePayload>
): Promise<TestCase> {
  const res = await fetch(`${BASE_URL}/api/test-cases/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<TestCase>(res);
}

export async function toggleTestCase(id: string): Promise<TestCase> {
  const res = await fetch(`${BASE_URL}/api/test-cases/${id}/toggle`, {
    method: 'PATCH',
  });
  return handleResponse<TestCase>(res);
}

export async function deleteTestCase(
  id: string
): Promise<{ status: string; action: string; message: string }> {
  const res = await fetch(`${BASE_URL}/api/test-cases/${id}`, {
    method: 'DELETE',
  });
  return handleResponse<{ status: string; action: string; message: string }>(res);
}

export async function exportDataset(datasetId: string): Promise<DatasetExport> {
  const res = await fetch(`${BASE_URL}/api/datasets/${datasetId}/export`);
  return handleResponse<DatasetExport>(res);
}

export async function importTestCases(
  datasetId: string,
  payload: { test_cases: any[]; overwrite_existing?: boolean }
): Promise<ImportResult> {
  const res = await fetch(`${BASE_URL}/api/datasets/${datasetId}/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<ImportResult>(res);
}

export async function importFullDataset(payload: {
  name: string;
  description?: string;
  test_cases: any[];
  overwrite_existing?: boolean;
}): Promise<ImportResult> {
  const res = await fetch(`${BASE_URL}/api/datasets/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<ImportResult>(res);
}

