import type {
  PipelineRun,
  PipelineStatus,
  PipelineLog,
  PipelineFileEntry,
  StartPipelineResponse,
  TelemetryStats,
} from '../types/pipeline';

const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '') || '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export interface LLMConfig {
  EMASDEP_LLM_PROVIDER: string;
  EMASDEP_LLM_MODEL: string;
  EMASDEP_LLM_BASE_URL: string;
  EMASDEP_LLM_API_KEY: string;
  EMASDEP_LLM_TEMPERATURE: string;
  EMASDEP_LLM_MAX_TOKENS: string;
  EMASDEP_ENV: string;
}

export interface OllamaModel {
  name: string;
  size: number;
  modified_at: string;
}

export const api = {
  health: () => request<{ status: string; version: string }>('/health'),

  getConfig: () => request<LLMConfig>('/config'),

  updateConfig: (cfg: Partial<LLMConfig>) =>
    request<LLMConfig>('/config', {
      method: 'PUT',
      body: JSON.stringify(cfg),
    }),

  listOllamaModels: () => request<{ models: OllamaModel[] }>('/config/ollama-models'),

  testConfig: (cfg: Partial<LLMConfig>) =>
    request<{ status: string; message: string }>('/config/test', {
      method: 'POST',
      body: JSON.stringify(cfg),
    }),

  getLogs: (correlationId: string, since?: string) =>
    request<PipelineLog[]>(`/pipeline/logs/${correlationId}${since ? `?since=${since}` : ''}`),

  cancelPipeline: (correlationId: string) =>
    request<{ status: string }>(`/pipeline/cancel/${correlationId}`, {
      method: 'POST',
    }),

  interactPipeline: (correlationId: string, response: string) =>
    request<{ status: string }>(`/pipeline/interact/${correlationId}`, {
      method: 'POST',
      body: JSON.stringify({ correlation_id: correlationId, response }),
    }),

  startPipeline: (rawIntent: string, projectName = 'default') =>
    request<StartPipelineResponse>('/pipeline/start', {
      method: 'POST',
      body: JSON.stringify({ raw_intent: rawIntent, project_name: projectName }),
    }),

  getStatus: (correlationId: string) =>
    request<PipelineStatus>(`/pipeline/status/${correlationId}`),

  listRuns: () => request<PipelineRun[]>('/pipeline/runs'),

  answerQuestion: (questionId: string, answer: string) =>
    request<{ status: string }>('/pipeline/answer', {
      method: 'POST',
      body: JSON.stringify({ question_id: questionId, answer }),
    }),

  getTelemetryStats: () => request<TelemetryStats>('/telemetry/stats'),

  listFiles: (correlationId: string) =>
    request<PipelineFileEntry[]>(`/pipeline/files/${correlationId}`),

  getFileContent: (correlationId: string, path: string) =>
    request<{ path: string; content: string }>(`/pipeline/files/${correlationId}/content?path=${encodeURIComponent(path)}`),

  getDownloadUrl: (correlationId: string) =>
    `${BASE}/pipeline/download/${correlationId}`,
};
