import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  GitBranch,
  BarChart3,
  Settings,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import clsx from 'clsx';

interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Pipeline', path: '/pipeline', icon: GitBranch },
  { label: 'Telemetry', path: '/telemetry', icon: BarChart3 },
  { label: 'Settings', path: '/settings', icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="flex w-56 flex-col border-r border-slate-800 bg-slate-900">
      <div className="flex h-14 items-center gap-2 border-b border-slate-800 px-4">
        <Zap className="h-6 w-6 text-emasdep-400" />
        <span className="text-lg font-bold tracking-tight text-white">
          EMASDEP
        </span>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-emasdep-900/50 text-emasdep-300'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200',
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-800 p-3">
        <div className="rounded-lg bg-slate-800/50 p-3">
          <div className="text-xs font-medium text-slate-400">System Status</div>
          <div className="mt-1 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="text-xs text-emerald-400">All Gates Nominal</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
