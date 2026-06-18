import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, FileText, Beaker, Code2, Shield,
  StopCircle, Terminal, Send, ChevronDown, ChevronRight,
} from 'lucide-react';
import { usePipelineStore } from '../store/pipelineStore';
import { api } from '../services/api';
import type { PipelineLog } from '../types/pipeline';
import PipelineDAG from '../components/pipeline/PipelineDAG';
import CodeExplorer from '../components/code/CodeExplorer';

const STATE_COLORS: Record<string, string> = {
  CONVERGED: 'text-emerald-400 bg-emerald-950/30 border-emerald-800',
  FAILED: 'text-red-400 bg-red-950/30 border-red-800',
  CANCELLED: 'text-slate-400 bg-slate-950/30 border-slate-600',
  BLOCKED_PROBE: 'text-amber-400 bg-amber-950/30 border-amber-800',
  CODING: 'text-cyan-400 bg-cyan-950/30 border-cyan-800',
  TESTING: 'text-rose-400 bg-rose-950/30 border-rose-800',
};

const LOG_LEVEL_COLORS: Record<string, string> = {
  info: 'text-slate-400',
  warning: 'text-amber-400',
  error: 'text-red-400',
  success: 'text-emerald-400',
};

export default function PipelineView() {
  const { correlationId } = useParams<{ correlationId: string }>();
  const navigate = useNavigate();
  const { currentRun, fetchStatus } = usePipelineStore();
  const [logs, setLogs] = useState<PipelineLog[]>([]);
  const [cancelMsg, setCancelMsg] = useState('');
  const [interactInput, setInteractInput] = useState('');
  const [sddOpen, setSddOpen] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const logContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    if (!autoScroll) return;
    const el = logContainerRef.current;
    if (el) {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
      if (atBottom) scrollToBottom();
    }
  }, [logs, autoScroll, scrollToBottom]);

  useEffect(() => {
    if (!correlationId) return;
    fetchStatus(correlationId);
    const interval = setInterval(() => fetchStatus(correlationId), 3000);
    return () => clearInterval(interval);
  }, [correlationId, fetchStatus]);

  useEffect(() => {
    if (!correlationId) return;
    const lastTimestampRef = { current: '' };
    const lastMessagesRef = new Set<string>();
    const poll = setInterval(async () => {
      try {
        const newLogs = await api.getLogs(correlationId, lastTimestampRef.current || undefined);
        if (newLogs.length > 0) {
          const deduped = newLogs.filter((log) => {
            const key = `${log.gate}|${log.level}|${log.message}`;
            if (lastMessagesRef.has(key)) return false;
            lastMessagesRef.add(key);
            return true;
          });
          if (deduped.length > 0) {
            setLogs((prev) => [...prev, ...deduped]);
            lastTimestampRef.current = deduped[deduped.length - 1].timestamp;
          }
        }
      } catch { }
    }, 1500);
    return () => clearInterval(poll);
  }, [correlationId]);

  const handleCancel = async () => {
    if (!correlationId) return;
    try {
      await api.cancelPipeline(correlationId);
      setCancelMsg('Cancelling pipeline...');
    } catch { }
  };

  const handleInteract = async () => {
    if (!correlationId || !interactInput.trim()) return;
    try {
      await api.interactPipeline(correlationId, interactInput.trim());
      setInteractInput('');
    } catch { }
  };

  const [probeAnswers, setProbeAnswers] = useState<Record<string, string>>({});

  const handleAnswerProbe = async (questionId: string) => {
    const answer = probeAnswers[questionId];
    if (!answer?.trim()) return;
    await api.answerQuestion(questionId, answer.trim());
    fetchStatus(correlationId!);
    setProbeAnswers((p) => ({ ...p, [questionId]: '' }));
  };

  if (!currentRun) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emasdep-500 border-t-transparent" />
      </div>
    );
  }

  const stateColor =
    STATE_COLORS[currentRun.current_state] ??
    'text-slate-400 bg-slate-950/30 border-slate-800';

  const metrics = [
    { label: 'Mutation Score', value: currentRun.mutation_score ? `${(currentRun.mutation_score * 100).toFixed(1)}%` : '-', icon: Beaker, color: 'text-violet-400' },
    { label: 'Coverage', value: currentRun.coverage_percent ? `${(currentRun.coverage_percent * 100).toFixed(1)}%` : '-', icon: Shield, color: 'text-emerald-400' },
    { label: 'Code Artifacts', value: currentRun.sdd ? 'Generated' : '-', icon: Code2, color: 'text-cyan-400' },
    { label: 'Spec Contract', value: currentRun.spec ? 'Bound' : 'Pending', icon: FileText, color: 'text-amber-400' },
  ];

  const canCancel = !['CONVERGED', 'FAILED', 'CANCELLED'].includes(currentRun.current_state);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/')} className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">Pipeline Run</h1>
          <p className="font-mono text-sm text-slate-500">{currentRun.correlation_id}</p>
        </div>
        <span className={`ml-auto rounded-lg border px-3 py-1 text-sm font-medium ${stateColor}`}>
          {currentRun.current_state}
        </span>
        {canCancel && (
          <button onClick={handleCancel} className="flex items-center gap-1.5 rounded-lg border border-red-800 bg-red-950/20 px-3 py-1.5 text-sm text-red-400 hover:bg-red-950/40">
            <StopCircle className="h-4 w-4" /> Cancel
          </button>
        )}
      </div>
      {cancelMsg && <div className="rounded-lg bg-amber-950/20 border border-amber-800 px-4 py-2 text-sm text-amber-400">{cancelMsg}</div>}

      <div className="grid grid-cols-4 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <div className="flex items-center gap-2">
              <m.icon className={`h-4 w-4 ${m.color}`} />
              <span className="text-xs font-medium text-slate-400">{m.label}</span>
            </div>
            <div className="mt-1 text-lg font-bold text-white">{m.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <PipelineDAG
          currentGate={currentRun.current_gate}
          isConverged={currentRun.is_converged}
          isFailed={currentRun.current_state === 'FAILED'}
        />

        <div className="space-y-4">
          {currentRun.interaction_pending && (
            <div className="rounded-xl border border-emasdep-700 bg-emasdep-950/20 p-4">
              <h3 className="mb-2 text-sm font-semibold text-emasdep-400">Input Required</h3>
              <p className="mb-3 text-sm text-slate-300">{currentRun.interaction_pending}</p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={interactInput}
                  onChange={(e) => setInteractInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleInteract()}
                  placeholder="Type your response..."
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:ring-2 focus:ring-emasdep-500 focus:outline-none"
                />
                <button onClick={handleInteract} disabled={!interactInput.trim()} className="flex items-center gap-1.5 px-3 py-2 bg-emasdep-600 hover:bg-emasdep-500 disabled:opacity-50 rounded-lg text-white text-sm">
                  <Send className="h-4 w-4" /> Send
                </button>
              </div>
            </div>
          )}

          {currentRun.failure_reason && (
            <div className="rounded-xl border border-red-800 bg-red-950/20 p-4">
              <h3 className="mb-1 text-sm font-semibold text-red-400">Failure Reason</h3>
              <p className="text-sm text-red-300">{currentRun.failure_reason}</p>
            </div>
          )}

          {currentRun.probing_questions && currentRun.probing_questions.length > 0 && (
            <div className="rounded-xl border border-amber-800 bg-amber-950/20 p-4">
              <h3 className="mb-2 text-sm font-semibold text-amber-400">Perguntas de esclarecimento</h3>
              <div className="space-y-3">
                {currentRun.probing_questions.map((q) => (
                  <div key={q.id} className="text-sm">
                    <p className="mb-1 text-xs text-amber-500">{q.context}</p>
                    <p className="text-slate-200">{q.question}</p>
                    {q.answered ? (
                      <p className="mt-1 text-xs text-emerald-400">Respondido: {q.answer}</p>
                    ) : (
                      <div className="mt-2">
                        {q.options && q.options.length > 0 && (
                          <div className="mb-2 grid grid-cols-1 gap-1">
                            {q.options.map((opt) => (
                              <button
                                key={opt.value}
                                onClick={() =>
                                  setProbeAnswers((p) => ({ ...p, [q.id]: opt.value }))
                                }
                                className={`text-left px-2 py-1.5 rounded text-xs border transition-colors ${
                                  probeAnswers[q.id] === opt.value
                                    ? 'border-emasdep-500 bg-emasdep-600/20 text-emasdep-300'
                                    : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600'
                                }`}
                              >
                                {opt.label}
                              </button>
                            ))}
                          </div>
                        )}
                        <div className="flex gap-1.5">
                          <input
                            type="text"
                            value={probeAnswers[q.id] ?? ''}
                            onChange={(e) =>
                              setProbeAnswers((p) => ({ ...p, [q.id]: e.target.value }))
                            }
                            placeholder="Digite sua resposta..."
                            className="flex-1 bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:ring-1 focus:ring-emasdep-500 focus:outline-none"
                            onKeyDown={(e) => e.key === 'Enter' && handleAnswerProbe(q.id)}
                          />
                          <button
                            onClick={() => handleAnswerProbe(q.id)}
                            disabled={!probeAnswers[q.id]?.trim()}
                            className="flex items-center gap-1 px-2 py-1.5 bg-emasdep-600 hover:bg-emasdep-500 disabled:opacity-50 rounded text-xs text-white"
                          >
                            <Send className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {currentRun.sdd && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50">
              <button
                onClick={() => setSddOpen(!sddOpen)}
                className="flex w-full items-center justify-between px-4 py-3 text-left"
              >
                <h3 className="text-sm font-semibold text-slate-300">SDD Preview</h3>
                {sddOpen ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
              </button>
              {sddOpen && (
                <div className="max-h-96 overflow-y-auto border-t border-slate-800 p-4">
                  <pre className="whitespace-pre-wrap text-xs text-slate-400 leading-relaxed">
                    {currentRun.sdd}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {correlationId && <CodeExplorer correlationId={correlationId} />}

      <div className="rounded-xl border border-slate-800 bg-slate-900/50">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <div className="flex items-center gap-2">
            <Terminal className="h-4 w-4 text-emasdep-400" />
            <h3 className="text-sm font-semibold text-slate-300">Live Pipeline Logs</h3>
            {logs.length > 0 && <span className="text-xs text-slate-500">{logs.length} entries</span>}
          </div>
          <button
            onClick={() => { setAutoScroll(!autoScroll); if (!autoScroll) scrollToBottom(); }}
            className={`flex items-center gap-1 rounded px-2 py-1 text-xs transition-colors ${
              autoScroll ? 'bg-emasdep-600/20 text-emasdep-400' : 'bg-slate-800 text-slate-500 hover:text-slate-300'
            }`}
            title={autoScroll ? 'Auto-scroll ON — click to disable' : 'Auto-scroll OFF — click to enable'}
          >
            <ChevronDown className="h-3 w-3" />
            {autoScroll ? 'Auto' : 'Manual'}
          </button>
        </div>
        <div
          ref={logContainerRef}
          className="max-h-80 overflow-y-auto p-4 font-mono text-xs space-y-1"
          onScroll={() => {
            if (!logContainerRef.current) return;
            const el = logContainerRef.current;
            const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
            if (!atBottom) setAutoScroll(false);
          }}
        >
          {logs.length === 0 ? (
            <p className="text-slate-600 italic">Waiting for pipeline events...</p>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-slate-600 shrink-0 w-20">
                  {log.timestamp.split('T')[1]?.split('.')[0] || log.timestamp.slice(11, 19)}
                </span>
                {log.gate && <span className="text-emasdep-600 shrink-0 w-16">[{log.gate}]</span>}
                <span className={LOG_LEVEL_COLORS[log.level] || 'text-slate-400'}>
                  {log.message}
                </span>
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
