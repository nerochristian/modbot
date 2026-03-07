import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Shield, Zap, Lock, ScrollText,
  Users, Command, BarChart3, Settings, Bot, Package,
  Gavel, History, ChevronDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/store/useAppStore';

const navSections = [
  {
    label: 'Overview',
    items: [
      { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
      { icon: BarChart3, label: 'Analytics', path: '/dashboard/analytics' },
    ],
  },
  {
    label: 'Configuration',
    items: [
      { icon: Command, label: 'Commands', path: '/dashboard/commands' },
      { icon: Settings, label: 'Setup', path: '/dashboard/setup' },
      { icon: Package, label: 'Modules', path: '/dashboard/modules' },
      { icon: Zap, label: 'Automod', path: '/dashboard/automod' },
      { icon: Lock, label: 'Anti-Raid', path: '/dashboard/anti-raid' },
      { icon: ScrollText, label: 'Logging', path: '/dashboard/logging' },
    ],
  },
  {
    label: 'Management',
    items: [
      { icon: Gavel, label: 'Cases', path: '/dashboard/cases' },
      { icon: Users, label: 'Permissions', path: '/dashboard/permissions' },
      { icon: History, label: 'Audit Log', path: '/dashboard/audit' },
    ],
  },
  {
    label: 'System',
    items: [
      { icon: Settings, label: 'Settings', path: '/dashboard/settings' },
    ],
  },
];

export function Sidebar() {
  const { capabilities } = useAppStore();

  return (
    <aside className="w-64 bg-sidebar-bg border-r border-cream-300 flex flex-col h-full shrink-0">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-cream-300">
        <div className="flex items-center gap-3 text-indigo-600">
          <div className="p-1.5 bg-indigo-50 rounded-xl">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <span className="font-display font-bold text-lg text-slate-800 tracking-tight">modbot</span>
            {capabilities && (
              <span className="text-[10px] text-slate-400 font-medium ml-1.5">v{capabilities.version}</span>
            )}
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-5">
        {navSections.map((section) => (
          <div key={section.label}>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.15em] mb-2 px-3">
              {section.label}
            </div>
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  className={({ isActive }) => cn(
                    'flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-white text-indigo-600 shadow-[0_2px_8px_rgba(0,0,0,0.04)]'
                      : 'text-slate-600 hover:bg-white/50 hover:text-slate-900'
                  )}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Footer: Bot status */}
      <div className="p-4 border-t border-cream-300">
        <div className="flex items-center gap-2 px-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-medium text-slate-500">Bot Online</span>
        </div>
      </div>
    </aside>
  );
}
