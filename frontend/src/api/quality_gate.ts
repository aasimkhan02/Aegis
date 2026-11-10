import { QualityGateRequest, QualityGateResponse } from '../types/quality_gate';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export async function evaluateQualityGate(payload: QualityGateRequest): Promise<QualityGateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/evaluations/release-gate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Quality gate evaluation failed: ${response.statusText}`);
  }

  return response.json();
}

