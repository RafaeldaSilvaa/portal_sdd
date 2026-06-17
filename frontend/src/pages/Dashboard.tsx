import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  GitBranch,
  Target,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import SpecEditor from '../components/spec/SpecEditor';
import ProbingModal from '../components/shared/ProbingModal';
import { usePipelineStore } from '../store/pipelineStore';

export default function Dashboard() {
  const navigate = useNavigate();
  const {
    runs,
    currentRun,
    probingQuestions,
    telemetry,
    loading,
    fetchRuns,
    startPipeline,
    answerQuestion,
    fetchTelemetry,
  } = usePipelineStore();

  const [showProbing, setShowProbing] = useState(false);

  useEffect(() => {
    fetchRuns();
    fetchTelemetry();
  }, [fetchRuns, fetchTelemetry]);

  const handleStartPipeline = async (intent: string) => {
    const correlationId = await startPipeline(intent);
    if (correlationId) {
      const probing = usePipelineStore.getState().probingQuestions;
      if (probing.length > 0) {
        setShowProbing(true);
      } else {
        navigate(`/pipeline/${correlationId}`);
      }
    }
  };

  const handleAnswer = async (questionId: string, answer: string) => {
    await answerQuestion(questionId, answer);
    const updatedProbing = usePipelineStore.getState().probingQuestions;
    if (updatedProbing.every((q) => q.answered)) {
      setShowProbing(false);
      if (currentRun) {
        navigate(`/pipeline/${currentRun.correlation_id}`);
      }
    }
  };

  const statsCards = [
    {
      label: 'Total Runs',
      value: telemetry?.total_runs ?? 0,
      icon: GitBranch,
      color: 'text-blue-400 bg-blue-950/30',
    },
    {
      label: 'Converged',
      value: telemetry?.converged_runs ?? 0,
      icon: CheckCircle2,
      color: 'text-emerald-400 bg-emerald-950/30',
    },
    {
      label: 'Failed',
      value: telemetry?.failed_runs ?? 0,
      icon: XCircle,
      color: 'text-red-400 bg-red-950/30',
    },
    {
      label: 'Avg Mutation Score',
      value: telemetry ? `${(telemetry.avg_mutation_score * 100).toFixed(1)}%` : '-',
      icon: Target,
      color: 'text-violet-400 bg-violet-950/30',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-400">
          EMASDEP Pipeline Control Center
        </p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {statsCards.map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-slate-800 bg-slate-900/50 p-4"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">
                {card.label}
              </span>
              <div className={`rounded-lg p-2 ${card.color}`}>
                <card.icon className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-2 text-2xl font-bold text-white">
              {card.value}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <SpecEditor
          onSubmit={handleStartPipeline}
          loading={loading}
        />

        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          <h2 className="mb-4 text-lg font-semibold text-white">
            Recent Runs
          </h2>
          <div className="space-y-2">
            {runs.length === 0 && (
              <p className="text-sm text-slate-500">
                No pipeline runs yet. Start one above.
              </p>
            )}
            {runs.slice(0, 10).map((run) => (
              <div
                key={run.correlation_id}
                onClick={() => navigate(`/pipeline/${run.correlation_id}`)}
                className="flex cursor-pointer items-center justify-between rounded-lg border border-slate-800 bg-slate-800/30 px-4 py-3 transition-colors hover:border-slate-700 hover:bg-slate-800/50"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`h-2 w-2 rounded-full ${
                      run.converged
                        ? 'bg-emerald-500'
                        : run.state === 'FAILED'
                          ? 'bg-red-500'
                          : 'bg-amber-500'
                    }`}
                  />
                  <span className="text-sm font-mono text-slate-300">
                    {run.correlation_id.slice(0, 16)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">
                    {run.state}
                  </span>
                  <span className="text-xs text-slate-600">
                    Gate {run.gate}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {showProbing && probingQuestions.length > 0 && (
        <ProbingModal
          questions={probingQuestions}
          onAnswer={handleAnswer}
          onClose={() => setShowProbing(false)}
        />
      )}
    </div>
  );
}
