export interface RunPerformanceSummary {
  run_id: string;
  assistant_version_id: string;
  assistant_name?: string | null;
  assistant_version?: string | null;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number;
  average_latency_ms?: number | null;
}

export interface OverallPerformance {
  total_cases: number;
  baseline: RunPerformanceSummary;
  candidate: RunPerformanceSummary;
  pass_rate_delta: number;
}

export interface MetricScoreComparison {
  metric_name: string;
  baseline_score?: number | null;
  candidate_score?: number | null;
  score_delta?: number | null;
  status: 'improved' | 'degraded' | 'unchanged' | 'only_in_candidate' | 'only_in_baseline' | string;
}

export interface MetricComparisonSummary {
  metrics: MetricScoreComparison[];
  improved_metrics: string[];
  degraded_metrics: string[];
  unchanged_metrics: string[];
}

export interface TestCaseRegressionDetail {
  test_case_id: string;
  name: string;
  baseline_status: string;
  candidate_status: string;
  is_security: boolean;
  error_message?: string | null;
  failed_metrics: string[];
}

export interface RegressionAnalysis {
  regressed_cases: TestCaseRegressionDetail[];
  improved_cases: TestCaseRegressionDetail[];
  both_failed_cases: TestCaseRegressionDetail[];
  both_passed_count: number;
  security_regressions: TestCaseRegressionDetail[];
}

export interface LatencyComparison {
  baseline_average_ms?: number | null;
  candidate_average_ms?: number | null;
  delta_ms?: number | null;
  percent_change?: number | null;
}

export interface ComparisonResponse {
  baseline_run_id: string;
  candidate_run_id: string;
  project_id: string;
  dataset_id: string;
  verdict: 'improved' | 'regressed' | 'unchanged';
  verdict_explanation: string;
  overall: OverallPerformance;
  metrics: MetricComparisonSummary;
  regressions: RegressionAnalysis;
  latency: LatencyComparison;
  compared_at: string;
}

export interface EvaluationRunSummary {
  id: string;
  project_id: string;
  assistant_version_id: string;
  dataset_id: string;
  status: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  created_at: string;
  completed_at?: string | null;
}

