export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  assistant_count?: number;
  dataset_count?: number;
  evaluation_count?: number;
}

export interface ProjectCreatePayload {
  name: string;
  description?: string;
}

export interface AssistantVersion {
  id: string;
  project_id: string;
  name: string;
  version: string;
  system_prompt: string | null;
  tools_schema: any[] | null;
  model: string | null;
  provider: string | null;
  metadata: Record<string, any>;
  created_at: string;
  project_name?: string;
}

export interface AssistantVersionCreatePayload {
  project_id: string;
  name: string;
  version: string;
  system_prompt?: string;
  tools_schema?: any[];
  model?: string;
  provider?: string;
  metadata?: Record<string, any>;
}

export interface MetricResult {
  id: string;
  case_result_id: string;
  metric_name: string;
  score: number;
  passed: boolean;
  threshold: number;
  details: Record<string, any>;
  created_at: string;
}

export interface CaseResult {
  id: string;
  evaluation_run_id: string;
  test_case_id: string;
  status: 'passed' | 'failed' | 'error';
  latency_ms: number;
  input_snapshot: any;
  output: any;
  error_message: string | null;
  created_at: string;
  metric_results: MetricResult[];
}

export interface EvaluationRun {
  id: string;
  project_id: string;
  assistant_version_id: string;
  dataset_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  config: Record<string, any>;
  project_name?: string | null;
  assistant_name?: string | null;
  assistant_version_tag?: string | null;
  dataset_name?: string | null;
  pass_rate?: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface EvaluationCreatePayload {
  assistant_version_id: string;
  dataset_id: string;
  config?: {
    max_concurrency?: number;
    fail_fast?: boolean;
    enable_deepeval?: boolean;
    enable_ragas?: boolean;
    enable_security?: boolean;
    security_validators?: string[];
    evaluators?: string[];
    extra?: Record<string, any>;
  };
}

export interface DashboardStats {
  total_projects: number;
  total_assistants: number;
  total_datasets: number;
  total_evaluation_runs: number;
  total_cases_evaluated: number;
  overall_passed_cases: number;
  overall_failed_cases: number;
  overall_pass_rate: number;
  total_security_failures: number;
  average_latency_ms: number | null;
}

export interface SecurityFinding {
  case_result_id: string;
  run_id: string;
  test_case_id: string;
  test_case_name: string;
  assistant_name: string | null;
  assistant_version: string | null;
  validator_name: string;
  status: string;
  score: number;
  error_message: string | null;
  latency_ms: number | null;
  evaluated_at: string;
}

export interface SecuritySummary {
  total_security_cases: number;
  total_security_failures: number;
  security_pass_rate: number;
  validator_breakdown: Record<string, { passed: number; failed: number }>;
  findings: SecurityFinding[];
}

