import { create } from 'zustand';
import type {
  PipelineRun,
  PipelineStatus,
  ProbingQuestion,
  TelemetryStats,
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
      set({
        currentRun: status,
        probingQuestions: status.probing_questions ?? [],
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
      await get().fetchStatus(result.correlation_id);
      set({ loading: false });
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
