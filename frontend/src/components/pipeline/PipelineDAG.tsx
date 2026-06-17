import 'reactflow/dist/style.css';

const GATE_LABELS: Record<number, string> = {
  1: 'Spec Contract',
  2: 'Probing',
  3: 'Architecture',
  4: 'Planner',
  5: 'QA / Tests',
  6: 'Engineer',
  7: 'Convergence',
};


interface PipelineDAGProps {
  currentGate: number;
  isConverged: boolean;
  isFailed: boolean;
}

export default function PipelineDAG({
  currentGate,
  isConverged,
  isFailed,
}: PipelineDAGProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-300">Pipeline DAG</h3>
        {isConverged && (
          <span className="rounded bg-emerald-900/30 px-2 py-0.5 text-xs font-medium text-emerald-400">
            Converged
          </span>
        )}
        {isFailed && (
          <span className="rounded bg-red-900/30 px-2 py-0.5 text-xs font-medium text-red-400">
            Failed
          </span>
        )}
      </div>

      <div className="space-y-2">
        {Object.entries(GATE_LABELS).map(([id, label]) => {
          const numId = parseInt(id);
          const isActive = numId === currentGate;
          const isDone = numId < currentGate || isConverged;

          return (
            <div
              key={id}
              className={`flex items-center gap-3 rounded-lg border px-4 py-3 transition-all ${
                isActive
                  ? 'border-emasdep-500 bg-emasdep-950/30 shadow-sm'
                  : isDone
                    ? 'border-emerald-800 bg-emerald-950/10'
                    : 'border-slate-800 bg-slate-900/30'
              }`}
            >
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                  isActive
                    ? 'bg-emasdep-500 text-white'
                    : isDone
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-800 text-slate-500'
                }`}
              >
                {isDone ? '\u2713' : id}
              </div>
              <div className="flex-1">
                <div className="text-xs text-slate-500">Gate {id}</div>
                <div className="text-sm font-medium text-slate-200">
                  {label}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
