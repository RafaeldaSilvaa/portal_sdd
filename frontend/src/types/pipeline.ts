export interface PipelineRun {
  correlation_id: string;
  state: string;
  gate: number;
  converged: boolean;
  cancelled: boolean;
  created_at: string;
}

export interface PipelineLog {
  timestamp: string;
  message: string;
  level: string;
  gate: string;
}

export interface PipelineStatus {
  correlation_id: string;
  current_state: string;
  current_gate: number;
  spec: Record<string, unknown> | null;
  probing_questions: ProbingQuestion[] | null;
  sdd: string | null;
  task_count: number | null;
  mutation_score: number | null;
  coverage_percent: number | null;
  failure_reason: string | null;
  is_converged: boolean;
  is_cancelled: boolean;
  interaction_pending: string | null;
}

export interface ProbingOption {
  label: string;
  value: string;
}

export interface ProbingQuestion {
  id: string;
  context: string;
  question: string;
  options?: ProbingOption[];
  answer: string | null;
  answered: boolean;
}

export interface TelemetryStats {
  total_runs: number;
  converged_runs: number;
  failed_runs: number;
  avg_mutation_score: number;
  avg_coverage: number;
}

export interface StartPipelineResponse {
  correlation_id: string;
  status: string;
  probing: {
    action: string;
    ambiguity_score: number;
    questionnaire: ProbingQuestion[];
  };
}

export interface PipelineFileEntry {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: PipelineFileEntry[];
  size: number;
}

export type PipelineState =
  | 'INIT'
  | 'SPEC_V1'
  | 'BLOCKED_PROBE'
  | 'DESIGN'
  | 'RISK_ANALYSIS'
  | 'PLANNING'
  | 'TESTING'
  | 'CODING'
  | 'HEALING_LOOP'
  | 'VALIDATION'
  | 'CONVERGED'
  | 'FAILED';
