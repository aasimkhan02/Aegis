export interface QualityGateThresholds {
  minimum_pass_rate: number;
  maximum_regression_percentage_points: number;
  maximum_security_failures: number;
  required_metrics: string[];
}

export interface QualityGateRequest {
  baseline_run_id: string;
  candidate_run_id: string;
  thresholds?: QualityGateThresholds;
}

export interface RuleEvaluationDetail {
  rule_name: string;
  passed: boolean;
  configured_threshold: any;
  actual_value: any;
  message: string;
}

export interface QualityGateResponse {
  decision: 'PASS' | 'FAIL';
  passed: boolean;
  baseline_run_id: string;
  candidate_run_id: string;
  project_id: string;
  dataset_id: string;
  thresholds: QualityGateThresholds;
  rules_evaluated: string[];
  passed_rules: string[];
  failed_rules: string[];
  rule_details: RuleEvaluationDetail[];
  failed_requirements: string[];
  explanation: string;
  evaluated_at: string;
}
