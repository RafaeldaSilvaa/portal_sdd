import { Zap } from 'lucide-react';

export default function Header() {
  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-800 bg-slate-900/50 px-6 backdrop-blur">
      <div className="flex items-center gap-3">
        <Zap className="h-5 w-5 text-emasdep-400" />
        <span className="text-sm font-medium text-slate-400">
          Enterprise Multi-Agent Spec-Driven Engineering Platform
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="rounded bg-emasdep-900/50 px-2 py-0.5 text-xs font-medium text-emasdep-300">
          v3.0.0
        </span>
        <span className="h-2 w-2 rounded-full bg-emerald-500" />
        <span className="text-xs text-slate-500">Online</span>
      </div>
    </header>
  );
}
