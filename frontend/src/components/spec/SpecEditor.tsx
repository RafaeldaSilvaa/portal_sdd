import { useState } from 'react';
import { FileText, Play } from 'lucide-react';

interface SpecEditorProps {
  onSubmit: (intent: string) => Promise<void>;
  loading: boolean;
}

export default function SpecEditor({ onSubmit, loading }: SpecEditorProps) {
  const [intent, setIntent] = useState('');

  const handleSubmit = async () => {
    if (!intent.trim()) return;
    await onSubmit(intent.trim());
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
      <div className="mb-4 flex items-center gap-2">
        <FileText className="h-5 w-5 text-emasdep-400" />
        <h2 className="text-lg font-semibold text-white">
          Raw Intent Input
        </h2>
      </div>

      <textarea
        value={intent}
        onChange={(e) => setIntent(e.target.value)}
        placeholder="Describe your business requirement in natural language...&#10;&#10;Example: 'Create a billing engine that processes invoices with idempotency guarantees and optimistic locking'"
        className="mb-4 min-h-[160px] w-full rounded-lg border border-slate-700 bg-slate-800/50 p-4 text-sm text-slate-200 placeholder-slate-500 focus:border-emasdep-500 focus:outline-none focus:ring-1 focus:ring-emasdep-500"
      />

      <button
        onClick={handleSubmit}
        disabled={loading || !intent.trim()}
        className="flex items-center gap-2 rounded-lg bg-emasdep-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emasdep-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        {loading ? 'Processing...' : 'Start Pipeline'}
      </button>
    </div>
  );
}
