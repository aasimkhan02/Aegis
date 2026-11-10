import { ComparisonResponse, EvaluationRunSummary } from '../types/comparison';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export async function fetchCompletedRuns(): Promise<EvaluationRunSummary[]> {
  const response = await fetch(`${API_BASE_URL}/api/evaluations?status=completed&limit=50`);
  if (!response.ok) {
    throw new Error(`Failed to fetch evaluation runs: ${response.statusText}`);
  }
  const data = await response.json();
  return data.items || [];
}

export async function compareEvaluationRuns(
  baselineRunId: string,
  candidateRunId: string
): Promise<ComparisonResponse> {
  const response = await fetch(`${API_BASE_URL}/api/evaluations/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      baseline_run_id: baselineRunId,
      candidate_run_id: candidateRunId,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Comparison failed: ${response.statusText}`);
  }

  return response.json();
}

