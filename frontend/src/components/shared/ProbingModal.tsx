import { useState } from 'react';
import { AlertTriangle, CheckCircle2, Send } from 'lucide-react';
import type { ProbingQuestion } from '../../types/pipeline';

interface ProbingModalProps {
  questions: ProbingQuestion[];
  onAnswer: (questionId: string, answer: string) => Promise<void>;
  onSubmitAll: () => Promise<void>;
  onClose: () => void;
}

export default function ProbingModal({
  questions,
  onAnswer,
  onSubmitAll,
  onClose,
}: ProbingModalProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const allAnswered = questions.every((q) => answers[q.id]?.trim());
  const answeredCount = Object.keys(answers).filter((k) => answers[k]?.trim()).length;

  const handleConfirmAll = async () => {
    if (!allAnswered) return;
    setSubmitting(true);
    try {
      for (const q of questions) {
        const answer = answers[q.id];
        if (answer?.trim()) {
          await onAnswer(q.id, answer.trim());
        }
      }
      await onSubmitAll();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl border border-amber-800 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-amber-800/50 px-6 py-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-400" />
            <h2 className="text-lg font-semibold text-white">
              Esclarecimentos necessários
            </h2>
          </div>
          <span className="text-xs text-slate-500">
            {answeredCount}/{questions.length} respondidas
          </span>
        </div>

        <div className="space-y-4 p-6">
          {questions.length === 0 && (
            <p className="text-sm text-slate-400">
              Nenhuma pergunta de esclarecimento no momento.
            </p>
          )}

          {questions.map((q, idx) => (
            <div
              key={q.id}
              className="rounded-lg border border-slate-700 bg-slate-800/30 p-4"
            >
              <div className="mb-1 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-900/50 text-xs font-bold text-amber-400">
                  {idx + 1}
                </span>
                <span className="text-xs font-medium text-amber-400">
                  {q.context || 'Esclarecimento'}
                </span>
              </div>
              <p className="mb-3 text-sm text-slate-200">{q.question}</p>

              {q.answered ? (
                <div className="rounded bg-emerald-900/20 px-3 py-2 text-sm text-emerald-400">
                  Respondido: {q.answer}
                </div>
              ) : (
                <div>
                  {q.options && q.options.length > 0 && (
                    <div className="mb-3 grid grid-cols-1 gap-1.5">
                      {q.options.map((opt) => (
                        <button
                          key={opt.value}
                          onClick={() =>
                            setAnswers((prev) => ({ ...prev, [q.id]: opt.value }))
                          }
                          className={`text-left px-3 py-2 rounded-lg text-sm border transition-colors ${
                            answers[q.id] === opt.value
                              ? 'border-emasdep-500 bg-emasdep-600/20 text-emasdep-300'
                              : 'border-slate-700 bg-slate-800/50 text-slate-300 hover:border-slate-600 hover:bg-slate-800'
                          }`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  )}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={answers[q.id] ?? ''}
                      onChange={(e) =>
                        setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                      }
                      placeholder="Ou digite sua resposta personalizada..."
                      className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-emasdep-500 focus:outline-none"
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-slate-800 px-6 py-3">
          <button
            onClick={onClose}
            className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700"
          >
            Fechar
          </button>
          <button
            onClick={handleConfirmAll}
            disabled={!allAnswered || submitting}
            className="flex items-center gap-2 rounded-lg bg-emasdep-600 px-5 py-2 text-sm font-medium text-white hover:bg-emasdep-500 disabled:opacity-50"
          >
            {submitting ? (
              <>
                <Send className="h-4 w-4 animate-pulse" />
                Enviando...
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4" />
                Confirmar Todas as Respostas
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
