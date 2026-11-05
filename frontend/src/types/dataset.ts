export interface Dataset {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  test_case_count: number;
  tags: string[];
}

export interface TestCase {
  id: string;
  dataset_id: string;
  name: string;
  input_data: any;
  expected_output: any | null;
  expected_behavior: string | null;
  retrieval_context: any[] | null;
  tags: string[];
  metadata: Record<string, any>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
  has_evaluations?: boolean;
}

export interface DatasetCreatePayload {
  name: string;
  description?: string;
  metadata?: Record<string, any>;
}

export interface TestCaseCreatePayload {
  name: string;
  input_data: any;
  expected_output?: any;
  expected_behavior?: string;
  retrieval_context?: any[];
  tags?: string[];
  metadata?: Record<string, any>;
  is_enabled?: boolean;
}

export interface ImportResult {
  dataset_id: string;
  dataset_name: string;
  imported_count: number;
  skipped_count: number;
  errors: Array<{
    index?: number;
    name?: string;
    error: string;
  }>;
  created_test_case_ids: string[];
}

export interface DatasetExport {
  dataset: Dataset;
  test_cases: TestCase[];
  exported_at: string;
}

