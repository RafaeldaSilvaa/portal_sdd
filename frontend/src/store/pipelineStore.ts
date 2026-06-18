import { create } from 'zustand';
import type {
  PipelineRun,
  PipelineStatus,
  ProbingQuestion,
  TelemetryStats,
  StartPipelineResponse,
} from '../types/pipeline';
import { api } from '../services/api';

interface PipelineStore {
  runs: PipelineRun[];
  currentRun: PipelineStatus | null;
  probingQuestions: ProbingQuestion[];
  telemetry: TelemetryStats | null;
  loading: boolean;
  error: string | null;

  fetchRuns: () => Promise<void>;
  fetchStatus: (correlationId: string) => Promise<void>;
  startPipeline: (intent: string) => Promise<string | null>;
  answerQuestion: (questionId: string, answer: string) => Promise<void>;
  fetchTelemetry: () => Promise<void>;
  clearError: () => void;
}

/** Converte o questionário da resposta de start em ProbingQuestion[] com opções preservadas */
function formatProbingQuestions(questionnaire: StartPipelineResponse['probing']['questionnaire']): ProbingQuestion[] {
  if (!questionnaire || !Array.isArray(questionnaire)) return [];
  return questionnaire.map((q) => ({
    id: q.id,
    context: q.context,
    question: q.question,
    options: q.options ?? undefined,
    answer: null,
    answered: false,
  }));
}

export const usePipelineStore = create<PipelineStore>((set, get) => ({
  runs: [],
  currentRun: null,
  probingQuestions: [],
  telemetry: null,
  loading: false,
  error: null,

  fetchRuns: async () => {
    set({ loading: true, error: null });
    try {
      const runs = await api.listRuns();
      set({ runs, loading: false });
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },

  fetchStatus: async (correlationId: string) => {
    set({ loading: true, error: null });
    try {
      const status = await api.getStatus(correlationId);
      // Preserva opções das perguntas existentes (vindas do startPipeline)
      const existingQuestions = get().probingQuestions;
      const existingOptions = new Map(existingQuestions.map((q) => [q.id, q.options]));
      const mergedQuestions = (status.probing_questions ?? []).map((q) => ({
        ...q,
        options: q.options ?? existingOptions.get(q.id) ?? undefined,
      }));
      set({
        currentRun: status,
        probingQuestions: mergedQuestions,
        loading: false,
      });
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },

  startPipeline: async (intent: string) => {
    set({ loading: true, error: null });
    try {
      const result = await api.startPipeline(intent);
      // Extrai perguntas de sondagem da resposta (com opções preservadas)
      const questions = formatProbingQuestions(result.probing?.questionnaire ?? []);
      set({
        probingQuestions: questions,
        currentRun: {
          correlation_id: result.correlation_id,
          current_state: result.status,
          current_gate: 0,
          spec: null,
          probing_questions: questions,
          sdd: null,
          task_count: null,
          mutation_score: null,
          coverage_percent: null,
          failure_reason: null,
          is_converged: false,
          is_cancelled: false,
          interaction_pending: null,
        },
        loading: false,
      });
      return result.correlation_id;
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
      return null;
    }
  },

  answerQuestion: async (questionId: string, answer: string) => {
    set({ loading: true, error: null });
    try {
      await api.answerQuestion(questionId, answer);
      const currentRun = get().currentRun;
      if (currentRun) {
        await get().fetchStatus(currentRun.correlation_id);
      }
      set({ loading: false });
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },

  fetchTelemetry: async () => {
    try {
      const stats = await api.getTelemetryStats();
      set({ telemetry: stats });
    } catch {
      // silent
    }
  },

  clearError: () => set({ error: null }),
}));
