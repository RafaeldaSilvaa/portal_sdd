import { useState } from 'react';
import { AlertTriangle, Send, X } from 'lucide-react';
import type { ProbingQuestion } from '../../types/pipeline';

interface ProbingModalProps {
  questions: ProbingQuestion[];
  onAnswer: (questionId: string, answer: string) => Promise<void>;
  onClose: () => void;
}

export default function ProbingModal({
  questions,
  onAnswer,
  onClose,
}: ProbingModalProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});

  const handleSubmit = async (questionId: string) => {
    const answer = answers[questionId];
    if (!answer?.trim()) return;
    await onAnswer(questionId, answer.trim());
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-2xl rounded-xl border border-amber-800 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-amber-800/50 px-6 py-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-400" />
            <h2 className="text-lg font-semibold text-white">
              Clarification Required
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4 p-6">
          {questions.map((q) => (
            <div
              key={q.id}
              className="rounded-lg border border-slate-700 bg-slate-800/30 p-4"
            >
              <p className="mb-1 text-xs font-medium text-amber-400">
                {q.context}
              </p>
              <p className="mb-3 text-sm text-slate-200">{q.question}</p>

              {q.answered ? (
                <div className="rounded bg-emerald-900/20 px-3 py-2 text-sm text-emerald-400">
                  Answered: {q.answer}
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={answers[q.id] ?? ''}
                    onChange={(e) =>
                      setAnswers((prev) => ({
                        ...prev,
                        [q.id]: e.target.value,
                      }))
                    }
                    placeholder="Type your answer..."
                    className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-emasdep-500 focus:outline-none"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSubmit(q.id);
                    }}
                  />
                  <button
                    onClick={() => handleSubmit(q.id)}
                    disabled={!answers[q.id]?.trim()}
                    className="flex items-center gap-1 rounded-lg bg-emasdep-600 px-3 py-2 text-sm font-medium text-white hover:bg-emasdep-500 disabled:opacity-50"
                  >
                    <Send className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="flex justify-end border-t border-slate-800 px-6 py-3">
          <button
            onClick={onClose}
            className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
